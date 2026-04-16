IMAGE  := sanitizer-reports:latest
DOCKER ?= docker

.PHONY: image reports run shell clean

shell: run

image:
	$(DOCKER) build -t $(IMAGE) .

reports: image
	$(DOCKER) run --rm $(IMAGE)

run: image
	$(DOCKER) run --rm -it --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --entrypoint /bin/bash $(IMAGE)

shell: run

clean:
	-$(DOCKER) rmi $(IMAGE)
