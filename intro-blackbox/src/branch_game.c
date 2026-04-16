#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *read_input(const char *path) {
  FILE *fp = fopen(path, "rb");
  if (!fp) return NULL;
  fseek(fp, 0, SEEK_END);
  long size = ftell(fp);
  rewind(fp);
  if (size < 0) {
    fclose(fp);
    return NULL;
  }
  char *buf = calloc((size_t)size + 1, 1);
  if (!buf) {
    fclose(fp);
    return NULL;
  }
  fread(buf, 1, (size_t)size, fp);
  fclose(fp);
  return buf;
}

int main(int argc, char **argv) {
  if (argc != 2) {
    fprintf(stderr, "usage: %s <file>\n", argv[0]);
    return 2;
  }

  char *buf = read_input(argv[1]); if (!buf) {
    fprintf(stderr, "failed to read file\n");
    return 2;
  }

  size_t len = strlen(buf);

  // We exclude 0 byte, so we have 255^6 at most (sum up all of length at most 5)
  if (len > 0 && buf[0] == 'A') {
    puts("branch 1");
    if (len > 1 && buf[1] == 'B') {
      puts("branch 2");
      if (len > 2 && buf[2] == 'C') {
        puts("branch 3");
        if (len > 3 && buf[3] == 'D') {
          puts("branch 4");
          if (len > 4 && buf[4] == '7') {
            puts("branch 5: jackpot");
            abort();
          }
        }
      }
    }
  }

  free(buf);
  return 0;
}
