FROM aflplusplus/aflplusplus:stable

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdb make gcc clang python3 python3-pip ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir sysv_ipc

WORKDIR /work

CMD ["bash"]
