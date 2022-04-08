
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/time.h>

#define DATA_FILENAME "numbers.dat"

#define NUMEROS 1573888
#define MAX        1023

int main(int argc, char* argv[]) {
    int numbers[NUMEROS];
    int prime_count = 0;

    if (argc != 2)
        return -1;

    int rounds = atoi(argv[1]);
    if (rounds <= 0)
        return -1;

    FILE *f = fopen(DATA_FILENAME, "rb");
    if (!f) return -1;

    for (int i = 0; i < NUMEROS; ++i) {
        fread(&numbers[i], 4, 1, f);
    }

    fclose(f);

    struct timeval begin;
    gettimeofday(&begin, NULL);

    while (rounds > 0) {
        for (int divisor = 2; divisor < MAX; ++divisor) {
            for (int i = 0; i < NUMEROS; ++i) {
                if (divisor < numbers[i]) {
                    if (numbers[i] % divisor == 0) {
                        prime_count++;
                    }
                }

                rounds--;

                if (rounds <= 0) {
                    goto mainloop_exit;
                }
            }
        }
    }

    struct timeval end;
mainloop_exit:

    gettimeofday(&end, NULL);
    unsigned long long elapsed = 1000000 * (end.tv_sec - begin.tv_sec) + (end.tv_usec - begin.tv_usec);


    printf("Found %i primes.\n", prime_count);
    printf("Took %llu microseconds.\n", elapsed);

    return 0;
}
