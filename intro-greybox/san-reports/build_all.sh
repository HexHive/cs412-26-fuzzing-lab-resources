#!/usr/bin/env bash
set -euo pipefail

CFLAGS_COMMON="-O0 -g -fno-omit-frame-pointer"
ASAN_FLAGS="-fsanitize=address"
UBSAN_FLAGS="-fsanitize=undefined"
CC=clang

BUILD_DIR="/work/build"
BUGS_DIR="/work/bugs"

mkdir -p "$BUILD_DIR"/{plain,asan,ubsan}

for san_dir in asan ubsan; do
    [[ -d "$BUGS_DIR/$san_dir" ]] || continue
    for src in "$BUGS_DIR/$san_dir"/*.c; do
        name=$(basename "$src" .c)
        # plain build (no sanitizer)
        $CC $CFLAGS_COMMON "$src" -o "$BUILD_DIR/plain/${name}"
        # sanitizer build
        case "$san_dir" in
            asan)  $CC $CFLAGS_COMMON $ASAN_FLAGS  "$src" -o "$BUILD_DIR/asan/${name}"  ;;
            ubsan) $CC $CFLAGS_COMMON $UBSAN_FLAGS "$src" -o "$BUILD_DIR/ubsan/${name}" ;;
        esac
        echo "  built: $name  (plain + $san_dir)"
    done
done

echo "All binaries ready in $BUILD_DIR/"
