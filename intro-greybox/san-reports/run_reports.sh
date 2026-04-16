#!/usr/bin/env bash

set -uo pipefail

CFLAGS_COMMON="-O0 -g -fno-omit-frame-pointer"
ASAN_FLAGS="-fsanitize=address"
UBSAN_FLAGS="-fsanitize=undefined -fno-sanitize-recover=undefined"

export ASAN_OPTIONS="color=never:abort_on_error=0:symbolize=1"
export UBSAN_OPTIONS="color=never:print_stacktrace=1:halt_on_error=1"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

run_case() {
  local kind="$1"   # asan | ubsan
  local src="$2"
  local name
  name="$(basename "$src" .c)"
  local bin="$WORKDIR/${kind}_${name}"
  local flags

  case "$kind" in
    asan)  flags="$ASAN_FLAGS"  ;;
    ubsan) flags="$UBSAN_FLAGS" ;;
  esac

  printf '\n'
  printf '============================================================\n'
  printf '  %s :: %s\n' "${kind^^}" "$name"
  printf '  source: %s\n' "$src"
  printf '============================================================\n'

  if ! gcc $CFLAGS_COMMON $flags "$src" -o "$bin" 2> "$WORKDIR/cc.err"; then
    echo "[compile failed]"
    cat "$WORKDIR/cc.err"
    return
  fi

  # Run it. Capture combined stdout+stderr and the real exit code.
  local out ec
  out=$("$bin" 2>&1) && ec=0 || ec=$?
  echo "$out"
  printf -- '-- exited with code %d --\n' "$ec"
}

echo '#############################################################'
echo '#   ASan reports                                            #'
echo '#############################################################'
for f in bugs/asan/*.c; do run_case asan "$f"; done

echo
echo '#############################################################'
echo '#   UBSan reports                                           #'
echo '#############################################################'
for f in bugs/ubsan/*.c; do run_case ubsan "$f"; done
