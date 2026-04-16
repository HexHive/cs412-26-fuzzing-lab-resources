#!/usr/bin/env bash
set -euo pipefail

BUILD_DIR="/work/build"
BUGS_DIR="/work/bugs"

BOLD=$'\033[1m'
DIM=$'\033[2m'
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
CYAN=$'\033[0;36m'
YELLOW=$'\033[1;33m'
RESET=$'\033[0m'

banner() { printf '\n%s%s%s\n\n' "$BOLD$CYAN" "$1" "$RESET"; }
die()    { printf '%sError:%s %s\n' "$RED" "$RESET" "$1" >&2; exit 1; }

find_san_for() {
    local name="$1"
    for d in asan ubsan; do
        [[ -f "$BUGS_DIR/$d/${name}.c" ]] && { echo "$d"; return 0; }
    done
    return 1
}

find_source() {
    local name="$1" san
    san=$(find_san_for "$name") || die "no source found for '$name'"
    echo "$BUGS_DIR/$san/${name}.c"
}

san_cflags() {
    case "$1" in
        asan)  echo "-fsanitize=address" ;;
        ubsan) echo "-fsanitize=undefined -fno-sanitize-recover=undefined" ;;
    esac
}

extract_main() {
    awk '/<main>:/{found=1} found{print} found && /^[[:space:]]*$/{exit}'
}

# Strip hex addresses so diff only shows real instruction differences.
#   "0000000000001149 <main>:"       -> "<main>:"
#   "    1149:  push   %rbp"         -> "  push   %rbp"
#   "call   1040 <malloc@plt>"       -> "call   <malloc@plt>"
#   "je     11ce <main+0x85>"        -> "je     <main+0x85>"
#   "lea  0xe5e(%rip)  # 2004 <...>" -> "lea  0xe5e(%rip)"
strip_addrs() {
    sed -E \
        -e 's/^[0-9a-f]+ (<)/\1/' \
        -e 's/^[[:space:]]+[0-9a-f]+:\t/\t/' \
        -e 's/(call|j[a-z]+)[[:space:]]+[0-9a-f]+ </\1 </g' \
        -e 's/[[:space:]]+#[[:space:]]*[0-9a-f]+ <[^>]+>//' \
        -e 's/[[:space:]]+$//'
}

cmd_list() {
    banner "Fuzzing 101 -- Sanitizer Instrumentation Inspector"
    printf '%sAvailable bug programs:%s\n\n' "$BOLD" "$RESET"
    for san_dir in asan ubsan; do
        [[ -d "$BUGS_DIR/$san_dir" ]] || continue
        for f in "$BUGS_DIR/$san_dir"/*.c; do
            local name
            name=$(basename "$f" .c)
            local desc
            desc=$(grep -m1 '^/\*' "$f" 2>/dev/null | sed 's|^/\* *||;s| *\*/.*||') || true
            [[ -z "$desc" ]] && desc="$name"
            printf '  %s%-20s%s %s(%s)%s  %s\n' \
                "$YELLOW" "$name" "$RESET" "$DIM" "$san_dir" "$RESET" "$desc"
        done
    done
    cat <<'EOF'

Commands:
  inspect <name>                   Show source code
  inspect <name> plain             Disassemble main() -- no sanitizer
  inspect <name> asan|ubsan        Disassemble main() -- with sanitizer
  inspect <name> diff              Diff of main(): plain vs sanitized
  inspect <name> diff full         Diff of full binary
  inspect <name> decompile         Pseudo-C of main() -- no sanitizer
  inspect <name> decompile-san     Pseudo-C of main() -- with sanitizer
  inspect <name> decompile-diff    Diff pseudo-C: plain vs sanitized
  inspect <name> run               Run the plain (unsanitized) binary
  inspect <name> run-san           Run the sanitized binary (shows report)

Tip: pipe long output through less, e.g.  inspect heap_overflow asan | less
EOF
}

cmd_source() {
    local src
    src=$(find_source "$1")
    banner "Source: $src"
    cat -n "$src"
}

cmd_disasm() {
    local name="$1" variant="$2"
    local bin="$BUILD_DIR/$variant/$name"
    [[ -f "$bin" ]] || die "no $variant build for '$name' (expected $bin)"

    local label flags=""
    case "$variant" in
        plain) label="NO sanitizer" ;;
        *)     label="${variant^^}"; flags=$(san_cflags "$variant") ;;
    esac

    banner "Disassembly of '$name' -- $label  (main function)"
    printf '%sCompiled with:%s gcc -O0 -g %s %s.c\n\n' "$BOLD" "$RESET" "$flags" "$name"
    objdump -d -M intel --no-show-raw-insn "$bin" | extract_main
    printf '\n%s(%d instructions)%s\n' "$DIM" \
        "$(objdump -d -M intel --no-show-raw-insn "$bin" | extract_main | grep -cE '^\s+[0-9a-f]+:')" \
        "$RESET"
}

cmd_diff() {
    local name="$1" mode="${2:-main}"
    local san
    san=$(find_san_for "$name") || die "no source for '$name'"

    local plain_bin="$BUILD_DIR/plain/$name"
    local san_bin="$BUILD_DIR/$san/$name"
    [[ -f "$plain_bin" ]] || die "missing plain build: $plain_bin"
    [[ -f "$san_bin" ]]   || die "missing $san build: $san_bin"

    local flags
    flags=$(san_cflags "$san")

    banner "Diff: plain vs ${san^^} -- $name"
    printf '  %s--- plain%s   (gcc -O0 -g)\n' "$RED" "$RESET"
    printf '  %s+++ %s%s     (gcc -O0 -g %s)\n\n' "$GREEN" "$san" "$RESET" "$flags"

    local filter="cat"
    [[ "$mode" == "main" ]] && filter="extract_main"

    local plain_count san_count
    plain_count=$(objdump -d -M intel --no-show-raw-insn "$plain_bin" | extract_main | grep -cE '^\s+[0-9a-f]+:')
    san_count=$(objdump -d -M intel --no-show-raw-insn "$san_bin"   | extract_main | grep -cE '^\s+[0-9a-f]+:')

    diff --color=always -u \
        --label "plain ($plain_count insns)" \
        --label "$san   ($san_count insns)" \
        <(objdump -d -M intel --no-show-raw-insn "$plain_bin" | $filter | strip_addrs) \
        <(objdump -d -M intel --no-show-raw-insn "$san_bin"   | $filter | strip_addrs) \
    || true   # diff exits 1 when files differ -- that's expected

    printf '\n%sPlain: %d instructions  |  %s: %d instructions  |  Overhead: +%d insns%s\n' \
        "$DIM" "$plain_count" "${san^^}" "$san_count" "$((san_count - plain_count))" "$RESET"
}

# Strip hex addresses from r2 pseudo-C so diff is clean.
strip_r2_addrs() {
    sed -E \
        -e 's/loc_0x[0-9a-f]+/loc_/g' \
        -e 's/@ 0x[0-9a-f]+/@ /g' \
        -e 's/[[:space:]]+$//'
}

cmd_decompile() {
    local name="$1" variant="$2"
    local bin="$BUILD_DIR/$variant/$name"
    [[ -f "$bin" ]] || die "no $variant build for '$name' (expected $bin)"

    local label flags=""
    case "$variant" in
        plain) label="NO sanitizer" ;;
        *)     label="${variant^^}"; flags=$(san_cflags "$variant") ;;
    esac

    banner "Pseudo-C of '$name' -- $label  (main function)"
    printf '%sCompiled with:%s gcc -O0 -g %s %s.c\n\n' "$BOLD" "$RESET" "$flags" "$name"
    r2 -q -e scr.color=0 -e asm.syntax=intel -c 'aaa; s main; pdc' "$bin" 2>/dev/null
}

cmd_decompile_diff() {
    local name="$1"
    local san
    san=$(find_san_for "$name") || die "no source for '$name'"

    local plain_bin="$BUILD_DIR/plain/$name"
    local san_bin="$BUILD_DIR/$san/$name"
    [[ -f "$plain_bin" ]] || die "missing plain build: $plain_bin"
    [[ -f "$san_bin" ]]   || die "missing $san build: $san_bin"

    local flags
    flags=$(san_cflags "$san")

    banner "Pseudo-C diff: plain vs ${san^^} -- $name"
    printf '  %s--- plain%s   (gcc -O0 -g)\n' "$RED" "$RESET"
    printf '  %s+++ %s%s     (gcc -O0 -g %s)\n\n' "$GREEN" "$san" "$RESET" "$flags"

    diff --color=always -u \
        --label "plain" \
        --label "$san" \
        <(r2 -q -e scr.color=0 -e asm.syntax=intel -c 'aaa; s main; pdc' "$plain_bin" 2>/dev/null | strip_r2_addrs) \
        <(r2 -q -e scr.color=0 -e asm.syntax=intel -c 'aaa; s main; pdc' "$san_bin"   2>/dev/null | strip_r2_addrs) \
    || true
}

cmd_run() {
    local name="$1" variant="$2"
    local bin="$BUILD_DIR/$variant/$name"
    [[ -f "$bin" ]] || die "no $variant build for '$name'"

    local label
    case "$variant" in
        plain) label="NO sanitizer" ;;
        *)     label="${variant^^}" ;;
    esac

    banner "Running '$name' -- $label"
    export ASAN_OPTIONS="color=always:abort_on_error=0:symbolize=1"
    export UBSAN_OPTIONS="color=always:print_stacktrace=1:halt_on_error=1"
    "$bin" && ec=0 || ec=$?
    printf '\n%s-- exited with code %d --%s\n' "$DIM" "$ec" "$RESET"
}

if [[ $# -eq 0 ]]; then
    cmd_list
    exit 0
fi

NAME="$1"
ACTION="${2:-source}"
EXTRA="${3:-}"

case "$ACTION" in
    source)   cmd_source "$NAME" ;;
    plain)    cmd_disasm  "$NAME" plain ;;
    asan)     cmd_disasm  "$NAME" asan  ;;
    ubsan)    cmd_disasm  "$NAME" ubsan ;;
    diff)     cmd_diff    "$NAME" "${EXTRA:-main}" ;;
    decompile)
        cmd_decompile "$NAME" plain
        ;;
    decompile-san)
        san=$(find_san_for "$NAME") || die "no source for '$NAME'"
        cmd_decompile "$NAME" "$san"
        ;;
    decompile-diff)
        cmd_decompile_diff "$NAME"
        ;;
    run)      cmd_run     "$NAME" plain ;;
    run-san)
        san=$(find_san_for "$NAME") || die "no source for '$NAME'"
        cmd_run "$NAME" "$san"
        ;;
    *)  die "unknown action '$ACTION'. Try: inspect $NAME [source|plain|asan|ubsan|diff|run|run-san]" ;;
esac
