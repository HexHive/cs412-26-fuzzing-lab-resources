#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    int *a = malloc(10 * sizeof(int));
    for (int i = 0; i < 10; i++) a[i] = i;
    a[9 + argc] = 42;
    printf("%d\n", a[9 + argc]);
    free(a);
    return 0;
}
