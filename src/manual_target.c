// Next week; we will actually look at the "real instrumentation"
// This is already quite close but not as flexible
// And we dont yet handle sanitization :)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// Needd ipc and shm if we do it ourselves
#ifdef MANUAL_INSTRUMENT
#include <sys/ipc.h>
#include <sys/shm.h>
#endif

// Mapsize has to correspond to afl++'s
// mapsize otherwise we write in a too small
// region or the mapsize is too large (slows down)
#define MAP_SIZE 256

#ifdef MANUAL_INSTRUMENT
static unsigned char *cov_map;

static void setup_shm(void) {
    // Read the envvar and get void* to map
    const char *id_str = getenv("__AFL_SHM_ID");
    if (!id_str) return;

    int shm_id = atoi(id_str);
    if (shm_id <= 0) return;

    cov_map = (unsigned char *)shmat(shm_id, NULL, 0);
    if (cov_map == (void *)-1) cov_map = NULL;
}

// Tracing: usually this is a bit smarter
// for those who wonder: do {..} is used for multiline macros and for branches.
// 
// For those who doubt that this is how coverage is really implemented:
// -> You are correct to doubt me!
// -> I invite you to read it up in the compiler pass :)
// -------------------------------------------------------------------------------------------
// https://github.com/AFLplusplus/AFLplusplus/blob/stable/instrumentation/afl-llvm-pass.so.cc
// -------------------------------------------------------------------------------------------
#define TRACE(ID) do { if (cov_map) cov_map[(ID) % MAP_SIZE]++; } while (0)

#else
// Disable the instrumentation otherwise...
#define setup_shm() ((void)0)
#define TRACE(ID) ((void)0)
#endif

static void bug(void) {
    volatile int *p = NULL;
    *p = 0x41414141;
}

// Prints input and crashes on abba
// because 'the winner takes it all'
int main(void) {
    char buf[128] = {0};
    setup_shm();
    TRACE(1); // entry

    if (!fgets(buf, sizeof(buf), stdin)) {
        return 0;
    }

    size_t n = strcspn(buf, "\n");
    buf[n] = '\0';

    if (n > 0 && buf[0] == 'a') {
        TRACE(10);
        puts("hit: a");

        if (n > 1 && buf[1] == 'b') {
            TRACE(20);
            puts("hit: ab");

            if (n > 2 && buf[2] == 'b') {
                TRACE(30);
                puts("hit: abb");

                if (n > 3 && buf[3] == 'a') {
                    TRACE(42); // WE found the answer
                    puts("hit: abba");
                    bug();
                } else if (n > 3 && buf[3] == 'x') {
                    TRACE(41);
                    puts("side path: abbx");
                }
            } else if (n > 2 && buf[2] == 'c') {
                TRACE(31);
                puts("side path: abc");
            }
        } else if (n > 1 && buf[1] == 'a') {
            TRACE(21);
            puts("side path: aa");
        }
    } else if (n > 0 && buf[0] == 'z') {
        TRACE(50);
        puts("side path: z");
    }

    TRACE(99); // exit-ish
    return 0;
}
