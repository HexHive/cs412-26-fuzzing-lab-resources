/* null-pointer-dereference: loading through a null pointer is undefined. */
#include <stdio.h>

int main(int argc, char **argv)
{
    (void)argv;
    int *p = (int *)0;
    if (argc > 0) p = (int *)0;    /* defeat constant-folding */
    int v = *p;                    /* null deref */
    printf("%d\n", v);
    return 0;
}
