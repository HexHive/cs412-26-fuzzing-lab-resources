# CS412 Fuzzing intro lab resources

[Slides](https://docs.google.com/presentation/d/1_xIYxHXqJmD1CH7IkFL5paujnAie4avRhbla4EJxQHs/edit?usp=sharing) to this weeks lab.

Files we consider:

- `Dockerfile` - environment with AFL++, clang, gcc and gdb
- `src/toy_library.c` + `src/toy_library.h` - small shared library with multiple branches and a crash
- `src/harness.c` - AFL++ style harness - reads input from a file or stdin and calls the shared library
- `src/branch_game.c` - tiny target with branch levels to show why guided fuzzing rocks
- `src/fake_afl.py` - Our poor man's fuzzer that helps in understanding afl++ (c.f. below)
- `seeds/` - starter corpus (empty)

## Setup: Build Stuff inside Docker

```bash
docker build -t afl-lab-demo .
docker run --rm -it -v "$PWD":/work afl-lab-demo
cd /work
make
```

## Run the targets normally

```bash
./branch_game seeds/A
./harness seeds/hello.txt
cat seeds/hello.txt | ./harness
```

## AFL++ quick start

Fuzz the harnessed library:

```bash
mkdir -p findings
AFL_SKIP_CPUFREQ=1 afl-fuzz -i seeds -o findings -- ./harness @@
```

Fuzz the branch demo:

```bash
AFL_SKIP_CPUFREQ=1 afl-fuzz -i seeds -o findings-branch -- ./branch_game @@
```

## Debug a crash

After AFL++ finds a crashing input, reproduce it:

```bash
# Only to see whether it really crashes
./harness findings/default/crashes/<crash-file>
```

Then open it in gdb:

```bash
# Assuming file is used as input
gdb --args ./harness findings/default/crashes/<crash-file>
run
bt

# Assuming stdin is used as input
gdb --args ./harness
run < findings/default/crashes/<crash-file>
bt
```

## Understanding AFL++ under the Hood

This repo also contains a tiny target that mimics AFL-style shared-memory coverage without using AFL++ instrumentation:

- `src/manual_target.c` - crashes on `abba` (because the winner takes it all)
- `manual_target_plain` - same target without coverage writes
- `manual_target_instrumented` - built with `-DMANUAL_INSTRUMENT` and writes branch IDs into shared memory
    - c.f. next week where we discuss coverage instrumentation
- `src/poor_afl.py` - runs in either `--mode blind` or `--mode coverage`

Build it:

```bash
python -m venv .venv
# then source it...
make manual_target_plain manual_target_instrumented
```

Run the poor man's fuzzer with coverage guidance:

```bash
python src/poor_afl.py --mode coverage --iterations 100
```

Run it without coverage:

```bash
python src/poor_afl.py --mode blind --iterations 1000
```
