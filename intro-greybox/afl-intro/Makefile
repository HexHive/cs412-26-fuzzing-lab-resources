IMAGE_NAME  := softsec-xpdf-fuzz
CONTAINER   := softsec-xpdf
WORKDIR     := /home/softsec

.PHONY: build run fuzz shell clean

build:
	docker build -t $(IMAGE_NAME) .

## Drop into the container interactively
run:
	docker run -ti --rm --name $(CONTAINER) $(IMAGE_NAME)

## Grey-box fuzzing: coverage-guided (instrumented binary)
fuzz:
	docker run -ti --rm --name $(CONTAINER) $(IMAGE_NAME) \
	  afl-fuzz -i $(WORKDIR)/seeds -o $(WORKDIR)/out -s 123 \
	    -- $(WORKDIR)/install/bin/pdftotext @@ /tmp/output

## Open a shell in a running container
shell:
	docker exec -ti $(CONTAINER) /bin/bash

## Remove containers and image
clean:
	-docker rm -f $(CONTAINER) $(CONTAINER)-blind
	-docker rmi -f $(IMAGE_NAME)
