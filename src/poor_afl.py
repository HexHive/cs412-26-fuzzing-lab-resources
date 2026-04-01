#!/usr/bin/env python3
import argparse
import os
import random
import subprocess
import time
from pathlib import Path

# SYS-V API for creating shared memory regions
import sysv_ipc

# how many edges, bbs, ... 
# we support at most
# --> usually depends on target size, 
# and this has to be configured the same
# way here to match the target
#
# find it out wiht AFL_DEBUG=1 ./target
MAP_SIZE = 256

# a "grammar" based fuzzer, but
# the principle is the same for
# all other types of fuzzers
ALPHABET = b"abczx"

# Path mumble jumble
ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "seeds_manual"
QUEUE_DIR = ROOT / "findings_manual" / "queue"
CRASH_DIR = ROOT / "findings_manual" / "crashes"

# Very nice afl++ generalization: target is fixed
# for our purposes
TARGET_INSTR = ROOT / "manual_target_instrumented"
TARGET_PLAIN = ROOT / "manual_target_plain"

for d in (CORPUS_DIR, QUEUE_DIR, CRASH_DIR):
    d.mkdir(parents=True, exist_ok=True)

if not any(CORPUS_DIR.iterdir()):
    (CORPUS_DIR / "seed0.txt").write_bytes(b"a\n")
    (CORPUS_DIR / "seed1.txt").write_bytes(b"z\n")


# Coverage map that is given to the child
def create_shared_memory():
    shm = sysv_ipc.SharedMemory(None, sysv_ipc.IPC_CREX, size=MAP_SIZE, mode=0o600)
    shm.write(b"\x00" * MAP_SIZE, 0)
    return shm

# Reset after child exits
def reset_map(shm):
    shm.write(b"\x00" * MAP_SIZE, 0)

# Dump map
def read_map(shm):
    return bytearray(shm.read(MAP_SIZE))


# We count hits (no counters)
def coverage_count(bitmap):
    return sum(1 for b in bitmap if b)

def mutate_input(data: bytes) -> bytes:
    buf = bytearray(data.rstrip(b"\n"))

    # Base case: have at least something
    if not buf:
        buf = bytearray(b"a")

    # ========================
    # ADVANCED FUZZING MUTATOR
    # ========================
    for _ in range(random.randint(1, 3)):
        action = random.choice(["flip", "insert", "delete"])
        # flip entry in input (e.g. a -> b)
        if action == "flip" and buf:
            i = random.randrange(len(buf))
            buf[i] = ALPHABET[random.randrange(len(ALPHABET))]
        # Insert at pos i
        elif action == "insert" and len(buf) < 8:
            i = random.randrange(len(buf) + 1)
            buf[i:i] = bytes([ALPHABET[random.randrange(len(ALPHABET))]])
        # get rid
        elif action == "delete" and len(buf) > 1:
            i = random.randrange(len(buf))
            del buf[i]

    # Dumb mutator: we terminate input with newline
    return bytes(buf) + b"\n"


def execute_target(target: Path, input_data: bytes, use_coverage: bool, shm=None):
    env = os.environ.copy()

    # Pass this to the child
    # (env var passed on below)
    if use_coverage and shm is not None:
        env["__AFL_SHM_ID"] = str(shm.id)

    try:
        result = subprocess.run(
            [str(target)], # <-- harness that we start
            input=input_data, # <-- pipe the fuzz input into stdin
            stdout=subprocess.PIPE, # <-- get the stdout from restul
            stderr=subprocess.PIPE, # <-- get the stderr from result
            timeout=0.2, # <-- process might hang, so we timeout
            env=env, # <-- __AFL_SHM_ID: thats the shared memory we use
        )

        # resultcode: 0 OK, otherwise crash/unnormal exit
        return result.returncode, result.stdout.decode(errors="ignore"), result.stderr.decode(errors="ignore")
    except subprocess.TimeoutExpired:
        return 0, "", "timeout"


# We provide this dir (very fancy seeds of course)
def load_initial_corpus():
    return [p.read_bytes() for p in sorted(CORPUS_DIR.iterdir()) if p.is_file()]


def save_input(base: Path, prefix: str, data: bytes):
    name = f"{prefix}_{int(time.time() * 1000)}_{random.randint(1000,9999)}.txt"
    (base / name).write_bytes(data)


def fuzz(iterations: int, mode: str, seed: int):
    random.seed(seed)
    queue = load_initial_corpus()

    if not queue:
        raise SystemExit("No seeds, bro")

    use_coverage = (mode == "coverage")

    # Pick target (its hardcoded for this example)
    target = TARGET_INSTR if use_coverage else TARGET_PLAIN
    if not target.exists():
        raise SystemExit(f"Target not found, bro: {target}")

    shm = create_shared_memory() if use_coverage else None
    global_cov = bytearray(MAP_SIZE)

    print(f"[CS-412] mode={mode} target={target.name} corpus={len(queue)}")

    try:
        for i in range(iterations):
            # ------------------
            # Advanced scheduler
            # ------------------
            parent = random.choice(queue)

            # Call into advanced mutator
            child = mutate_input(parent)

            # If we dont collect coverage, just ignore
            # what the target does witht the shmem
            if use_coverage:
                reset_map(shm)

            # Fuzzer go brr here
            status, out, err = execute_target(target, child, use_coverage, shm)
            print(f"iter={i:03d} input={child.rstrip()!r} rc={status}")

            # too verbose
            # if out.strip():
            #     print("  stdout:", out.strip())
            # if err.strip():
            #     print("  stderr:", err.strip())

            interesting = False
            if use_coverage:
                bitmap = read_map(shm)
                # AFL collects coverage in map: hitcounts per edge/basic block/...
                # we convert the hitcounts into bits -> collecting new hits here
                new_bits = [idx for idx, (old, new) in enumerate(zip(global_cov, bitmap)) if old == 0 and new > 0]
                print(f"  coverage={coverage_count(bitmap)} new_bits={new_bits}")

                # New bit -> add this seed to "interesting" set
                # literally, this is coverage guided fuzzing
                if new_bits:
                    interesting = True
                    for idx in new_bits:
                        global_cov[idx] = 1
            else:
                # Blind mode: keep a few random mutations so there is still a queue.
                # but this is truly random
                interesting = random.random() < 0.1
                print("  blind mode: no coverage feedback")

            if interesting:
                queue.append(child)
                save_input(QUEUE_DIR, "id", child)
                print(f"  [+] kept, queue={len(queue)}")

            if status < 0:
                save_input(CRASH_DIR, "crash", child)
                print("  [!] crash found")
                break

    # Get rid of shmem
    finally:
        if shm is not None:
            try:
                shm.detach()
            except Exception:
                pass
            try:
                shm.remove()
            except Exception:
                pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="CS-412: I'll do it myself AFL++ demo")
    # Black-box / grey-box
    ap.add_argument("--mode", choices=["coverage", "blind"], default="coverage")
    # Forkserver type of deal
    ap.add_argument("--iterations", type=int, default=100)
    # So its reproducible -> PRNG seeding
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    fuzz(args.iterations, args.mode, args.seed)
