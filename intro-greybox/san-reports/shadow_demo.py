#!/usr/bin/env python3
"""
shadow_demo.py --- Heap red-zone & shadow-memory visualizer.

Compiles a small heap-overflow program twice (plain and with ASan),
runs both under libdebug, and contrasts the memory layout around the
heap allocation.

We see:
  1. Plain build --- no protection, overflow writes silently
  2. ASan build --- red zones in heap memory, shadow bytes guard every access

Usage:
    python3 shadow_demo.py
"""
import struct
import subprocess
import sys

from libdebug import debugger

#
#   shadow_addr = (app_addr >> 3) + 0x7FFF8000
#
#   0x00       all 8 app bytes accessible
#   0x01..0x07 first N accessible, rest poisoned
#   0xfa       heap left red zone
#   0xfb       heap right red zone
#   0xfd       freed heap
#
SHADOW_BASE = 0x7fff8000

POISON_NAMES = {
    0x00: "accessible",
    0x01: "partial (1/8)",
    0x02: "partial (2/8)",
    0x03: "partial (3/8)",
    0x04: "partial (4/8)",
    0x05: "partial (5/8)",
    0x06: "partial (6/8)",
    0x07: "partial (7/8)",
    0xf1: "stack LEFT red zone",
    0xf2: "stack MID red zone",
    0xf3: "stack RIGHT red zone",
    0xf5: "stack use-after-return",
    0xfa: "heap LEFT red zone",
    0xfb: "heap RIGHT red zone",
    0xfd: "freed heap",
}

# term colors :)
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"
BG_RED = "\033[97;41m"   # bright-white on red background

# a minimal heap overflow with a checkpoint() function that the debugger
# uses as a breakpoint.  rdi = buf when the debugger stops there.

N_INTS = 10
BUF_BYTES = N_INTS * 4
OOB_IDX = 10

TARGET_C = r"""
#include <stdlib.h>

__attribute__((noinline, used))
void checkpoint(void *p) { asm volatile("" : : "r"(p)); }

int main(void) {
    int *buf = malloc(10 * sizeof(int));        /* 40 bytes            */
    for (int i = 0; i < 10; i++) buf[i] = i;    /* fill: 0,1,2,...,9   */
    checkpoint(buf);                            /* PAUSE 1: before OOB */
    buf[10] = 0x42;                             /* heap overflow       */
    checkpoint(buf);                            /* PAUSE 2: after OOB  */
    free(buf);
    return 0;
}
"""

PLAIN_BIN = "/tmp/_shadow_plain"
ASAN_BIN  = "/tmp/_shadow_asan"

# some helpers

def shadow_of(addr):
    return (addr >> 3) + SHADOW_BASE

def sdesc(v):
    return POISON_NAMES.get(v, "poison (%#04x)" % v)

def scol(v):
    """Colour-code a shadow byte value."""
    s = "%02x" % v
    if v == 0:        return GREEN + s + RESET
    if 1 <= v <= 7:  return YELLOW + s + RESET
    return RED + s + RESET

def section(title):
    """Print a section divider."""
    w = 66
    print("\n  " + BOLD + "-" * w)
    print("   " + title)
    print("  " + "-" * w + RESET)


# the build function
def build():
    """Compile the target program (plain + ASan) into /tmp."""
    src = "/tmp/_shadow_target.c"
    with open(src, "w") as f:
        f.write(TARGET_C)
    base = ["clang", "-O0", "-g", "-fno-omit-frame-pointer", src]
    null = subprocess.DEVNULL
    subprocess.check_call(base + ["-o", PLAIN_BIN],
                          stdout=null, stderr=null)
    subprocess.check_call(base + ["-fsanitize=address", "-o", ASAN_BIN],
                          stdout=null, stderr=null)

def hexdump(data, start_addr, buf_addr, buf_size, hi_addr=None):
    """Pretty-print memory.  16 bytes/row, grouped by 4 (one int).
    
    Annotations on the right show decoded int values for buffer rows.
    """
    hi_end = (hi_addr + 4) if hi_addr is not None else None

    for off in range(0, len(data), 16):
        addr = start_addr + off
        row  = data[off:off + 16]

        # Label relative to buf
        rel = addr - buf_addr
        if rel < 0:
            lbl = "buf - %#04x" % (-rel)
        else:
            lbl = "buf + %#04x" % rel

        # Hex bytes in groups of 4
        groups = []
        for g in range(0, 16, 4):
            if g >= len(row):
                break
            cells = []
            for i in range(g, min(g + 4, len(row))):
                ba = addr + i
                b  = row[i]
                if hi_addr is not None and hi_addr <= ba < hi_end:
                    cells.append(BG_RED + BOLD + "%02x" % b + RESET)
                elif buf_addr <= ba < buf_addr + buf_size:
                    cells.append(GREEN + "%02x" % b + RESET)
                else:
                    cells.append(RED + "%02x" % b + RESET)
            groups.append(" ".join(cells))
        hex_part = "  ".join(groups)

        # Right-side annotation: decode ints that fall inside the buffer
        notes = []
        for g in range(0, min(len(row), 16), 4):
            ba = addr + g
            if g + 4 <= len(row):
                val = struct.unpack_from("<i", row, g)[0]
                idx = (ba - buf_addr) // 4
                if buf_addr <= ba < buf_addr + buf_size:
                    notes.append("[%d]=%d" % (idx, val))
                elif hi_addr is not None and ba == hi_addr:
                    notes.append("[%d]=%d !!" % (idx, val))
        ann = ("  " + DIM + " ".join(notes) + RESET) if notes else ""

        print("  %-12s  %s%s" % (lbl, hex_part, ann))


# phase 1: plain

def phase_plain():
    d = debugger(PLAIN_BIN, aslr=False)
    d.run()
    d.breakpoint("checkpoint", file="binary")

    # buffer initialised, overflow not yet done
    d.cont()
    d.wait()
    buf = d.regs.rdi
    pad_before, pad_after = 32, 48
    total = pad_before + BUF_BYTES + pad_after
    mem_before = bytes(d.memory[buf - pad_before, total])

    # overflow done
    d.cont()
    d.wait()
    mem_after = bytes(d.memory[buf - pad_before, total])

    d.terminate()

    print("\n  buf @ %s%#x%s  (%d bytes = int[%d])" %
          (CYAN, buf, RESET, BUF_BYTES, N_INTS))

    print("\n  %s1) Before the overflow:%s\n" % (BOLD, RESET))
    hexdump(mem_before, buf - pad_before, buf, BUF_BYTES)

    print("\n  %s2) After  buf[10] = 0x42:%s\n" % (BOLD, RESET))
    hexdump(mem_after, buf - pad_before, buf, BUF_BYTES,
            hi_addr=buf + OOB_IDX * 4)

    print("\n  %s-->%s The overflow wrote 0x42 past the allocation." %
          (YELLOW, RESET))
    print("      No detection. No crash. %sSilent memory corruption.%s" %
          (YELLOW, RESET))


# --- Phase 2: ASan ----------------------------------------------------------

def phase_asan():
    d = debugger(ASAN_BIN, aslr=False)
    d.run()
    d.breakpoint("checkpoint")
    d.breakpoint("__asan_report_store4")

    # buffer initialised, before overflow
    d.cont()
    d.wait()
    buf = d.regs.rdi
    pad_before, pad_after = 48, 64
    total = pad_before + BUF_BYTES + pad_after
    heap_mem = bytes(d.memory[buf - pad_before, total])

    # ASan catches the overflow (before the store happens)
    d.cont()
    d.wait()
    bad_addr   = d.regs.rdi
    shad_addr  = shadow_of(bad_addr)
    shad_val   = d.memory[shad_addr, 1][0]

    # read shadow memory around the buffer
    sr = 8                                      # extra shadow bytes each side
    shad_start = shadow_of(buf) - sr
    shad_len   = (BUF_BYTES // 8) + sr * 2
    shad_data  = bytes(d.memory[shad_start, shad_len])

    d.terminate()

    print("\n  buf @ %s%#x%s  (%d bytes = int[%d])" %
          (CYAN, buf, RESET, BUF_BYTES, N_INTS))

    print("\n  %s1) Heap memory around the buffer:%s" % (BOLD, RESET))
    print("     (%s%sgreen%s = buffer   %s%sred%s = outside / red zone)" %
          (DIM, GREEN, RESET, DIM, RED, RESET))
    print()
    hexdump(heap_mem, buf - pad_before, buf, BUF_BYTES)

    # pretty layout diagram
    print()
    rz = RED + "RED ZONE" + RESET
    bf = GREEN + " buf[0] ........ buf[9] " + RESET
    print("  Layout:  | %s | %s | %s |" % (rz, bf, rz))
    print("  %s         ASan guard     user data (40 B)     ASan guard%s" %
          (DIM, RESET))

    # violation report
    oob_off = bad_addr - buf
    print("\n  %s%s!! ASan caught the overflow BEFORE the store !!%s" %
          (BOLD, RED, RESET))
    print("    Target address : %#x  (buf + %#x -> buf[%d])" %
          (bad_addr, oob_off, oob_off // 4))
    print("    Shadow byte    : %s -> %s" % (scol(shad_val), sdesc(shad_val)))

    # shadow memory
    print("\n  %s2) Shadow memory:%s  (1 shadow byte = 8 app bytes)" %
          (BOLD, RESET))
    print("     shadow = (addr >> 3) + %#x\n" % SHADOW_BASE)

    for off in range(0, len(shad_data), 16):
        sa   = shad_start + off
        aa   = (sa - SHADOW_BASE) << 3
        row  = shad_data[off:off + 16]
        cells = []
        for i, b in enumerate(row):
            if sa + i == shad_addr:
                cells.append(BOLD + "[" + scol(b) + BOLD + "]" + RESET)
            else:
                cells.append(" " + scol(b) + " ")
        print("  %#014x  app %#014x  %s" % (sa, aa, "".join(cells)))

    vals = sorted(set(shad_data))
    print("\n  %sLegend:%s" % (BOLD, RESET))
    for v in vals:
        print("    %s = %s" % (scol(v), sdesc(v)))


def main():
    w = 66
    print()
    print("  " + BOLD + "=" * w)
    print("   Heap Red Zone & Shadow Memory Demo")
    print("  " + "=" * w + RESET)

    print("\n  %sTarget program:%s" % (BOLD, RESET))
    print("  %s  int *buf = malloc(10 * sizeof(int));  // 40 bytes%s"   % (DIM, RESET))
    print("  %s  for (int i = 0; i < 10; i++) buf[i] = i;%s"           % (DIM, RESET))
    print("  %s  buf[10] = 0x42;                       // overflow%s"   % (DIM, RESET))
    print()
    print("  %sShadow mapping: shadow = (addr >> 3) + %#x%s" %
          (DIM, SHADOW_BASE, RESET))

    build()

    section("PLAIN  (no sanitizer)")
    phase_plain()

    section("ASAN  (-fsanitize=address)")
    phase_asan()

    # summary
    section("Summary")
    print()
    print("  PLAIN:")
    print("    | %sheap meta%s | %s buf[0]...buf[9] %s | %s no guard %s |" %
          (DIM, RESET, GREEN, RESET, DIM, RESET))
    print("    %s                                       ^ overflow lands here "
          "undetected%s" % (DIM, RESET))
    print()
    print("  ASAN:")
    print("    | %sRED ZONE%s | %s buf[0]...buf[9] %s | %sRED ZONE%s |" %
          (RED, RESET, GREEN, RESET, RED, RESET))
    print("    %s                                       ^ shadow check blocks "
          "the write%s" % (DIM, RESET))
    print()


if __name__ == "__main__":
    main()
