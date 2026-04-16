#include "toy_library.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void crash_now(void) {
  volatile uint32_t *p = NULL;
  *p = 0x41414141;
}

int process_input(const unsigned char *data, size_t len) {
  if (len == 0) {
    return 0;
  }

  if (data[0] == 'H') {
    if (len > 1 && data[1] == 'I') {
      if (len > 2 && data[2] == '!') {
        puts("greeting path");
      }
    }
  }

  if (len >= 4 && memcmp(data, "PING", 4) == 0) {
    puts("command path");
  }

  if (len >= 6 && memcmp(data, "MAGI", 4) == 0) {
    if (data[4] == 'C' && data[5] == '!') {
      puts("deeper magic path");
    }
  }

  if (len >= 8 && memcmp(data, "CRSH", 4) == 0) {
    if (data[4] == '-') {
      if (data[5] == 'N' && data[6] == 'O' && data[7] == 'W') {
        fprintf(stderr, "boom: deliberate crash reached\n");
        crash_now();
      }
    }
  }

  if (len >= 5 && data[0] >= '0' && data[0] <= '9') {
    int sum = 0;
    for (size_t i = 0; i < len && i < 5; i++) {
      if (data[i] < '0' || data[i] > '9') {
        return 0;
      }
      sum += data[i] - '0';
    }
    if (sum == 23) {
      puts("numeric path");
    }
  }

  return 0;
}
