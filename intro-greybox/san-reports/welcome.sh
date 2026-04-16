#!/usr/bin/env bash
cat <<'BANNER'
+--------------------------------------------------------------+
|    Fuzzing 101 --- Nice sanitizers and where to find them    |
+--------------------------------------------------------------+

  Pre-built binaries in /work/build/{plain,asan,ubsan}/
  Bug sources        in /work/bugs/{asan,ubsan}/

BANNER

printf '  \033[1mQuick start:\033[0m\n'
cat <<'USAGE'
    inspect                                 # list programs & commands
    inspect heap_overflow                   # view source
    inspect heap_overflow plain             # disasm main() -- no sanitizer
    inspect heap_overflow asan              # disasm main() -- with ASan
    inspect heap_overflow diff              # unified diff of both
    inspect stack_overflow diff             # <-- best for showing red-zones
    inspect double_free decompile           # pseudo-C (radare2) -- no sanitizer
    inspect double_free decompile-san       # pseudo-C with ASan
    inspect double_free decompile-diff      # diff the pseudo-C
    inspect heap_overflow run-san           # run and see the ASan report

  * Heap red-zone & shadow memory demo (libdebug) *
    python3 shadow_demo.py          # plain vs ASan heap layout side-by-side

  * Objdump or pwndbg directly :) *
    objdump -d /work/build/plain/heap_overflow | less
    pwndbg ./build/asan/heap_overflow

USAGE
