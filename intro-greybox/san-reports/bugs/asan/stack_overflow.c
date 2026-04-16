#include <stdio.h>

int main(int argc, char **argv)
{
    (void)argv;
    int buf[4] = {0, 1, 2, 3};
    buf[4 + argc] = 0xdeadbeef;
    printf("%d\n", buf[4 + argc]);
    return 0;
}
