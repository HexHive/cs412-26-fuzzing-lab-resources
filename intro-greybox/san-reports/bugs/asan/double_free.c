#include <stdlib.h>

int main(void)
{
    int *a = malloc(sizeof(int));
    *a = 42;
    free(a); /* free(a); free(a) doesn't work :) glibc checks for those
	      * trivial DFs */
    free(a);
    return 0;
}
