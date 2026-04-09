all: progress_rate progress_rate_test

progress_rate: progress_rate.c
	gcc -lm -o progress_rate progress_rate.c

progress_rate_test: progress_rate_test.c
	gcc -lm -o progress_rate_test progress_rate_test.c

clean:
	rm progress_rate progress_rate_test
