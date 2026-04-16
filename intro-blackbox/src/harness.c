#include "toy_library.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char *read_all(FILE *fp, size_t *out_len) {
  size_t cap = 4096;
  size_t len = 0;
  unsigned char *buf = malloc(cap);
  if (!buf) {
    return NULL;
  }

  while (!feof(fp)) {
    if (len == cap) {
      cap *= 2;
      unsigned char *tmp = realloc(buf, cap);
      if (!tmp) {
        free(buf);
        return NULL;
      }
      buf = tmp;
    }
    size_t n = fread(buf + len, 1, cap - len, fp);
    len += n;
    if (ferror(fp)) {
      free(buf);
      return NULL;
    }
  }

  *out_len = len;
  return buf;
}

int main(int argc, char **argv) {
  FILE *fp = stdin;

  if (argc > 2) {
    fprintf(stderr, "usage: %s [file]\n", argv[0]);
    return 2;
  }

  if (argc == 2) {
    fp = fopen(argv[1], "rb");
    if (!fp) {
      fprintf(stderr, "failed to open '%s': %s\n", argv[1], strerror(errno));
      return 2;
    }
  }

  size_t len = 0;
  unsigned char *data = read_all(fp, &len);
  if (argc == 2) {
    fclose(fp);
  }
  if (!data) {
    fprintf(stderr, "failed to read input\n");
    return 2;
  }

  int rc = process_input(data, len);
  free(data);
  return rc;
}
