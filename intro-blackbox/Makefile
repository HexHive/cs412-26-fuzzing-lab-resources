CC ?= clang
CFLAGS ?= -O0 -g -fno-omit-frame-pointer -Wall -Wextra -I./src
LDFLAGS ?=


all: libtoy.so harness branch_game manual_target_plain manual_target_instrumented

manual_target_plain: src/manual_target.c
	$(CC) $(CFLAGS) -o $@ src/manual_target.c

manual_target_instrumented: src/manual_target.c
	$(CC) $(CFLAGS) -DMANUAL_INSTRUMENT -o $@ src/manual_target.c

afl: CFLAGS += -fsanitize=address

afl: libtoy.so harness branch_game

libtoy.so: src/toy_library.c src/toy_library.h
	$(CC) $(CFLAGS) -shared -fPIC -o $@ src/toy_library.c

harness: src/harness.c libtoy.so src/toy_library.h
	$(CC) $(CFLAGS) -L. -Wl,-rpath,'$$ORIGIN' -o $@ src/harness.c -ltoy

branch_game: src/branch_game.c
	$(CC) $(CFLAGS) -o $@ src/branch_game.c

clean:
	rm -f harness branch_game libtoy.so manual_target_plain manual_target_instrumented
	find . -maxdepth 1 -name 'core*' -delete

.PHONY: all afl clean
