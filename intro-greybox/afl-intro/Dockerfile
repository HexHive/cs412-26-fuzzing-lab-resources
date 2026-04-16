FROM aflplusplus/aflplusplus

RUN mkdir -p /home/softsec
WORKDIR /home/softsec

RUN wget -q https://dl.xpdfreader.com/old/xpdf-3.02.tar.gz && \
    tar xf xpdf-3.02.tar.gz && \
    rm xpdf-3.02.tar.gz

RUN cd xpdf-3.02 && \
    CC=afl-clang-fast CXX=afl-clang-fast++ \
    CFLAGS="-fsanitize=address -g -O1" \
    CXXFLAGS="-fsanitize=address -g -O1 -fpermissive" \
    LDFLAGS="-fsanitize=address" \
    ./configure --prefix=/home/softsec/install && \
    make -j$(nproc) && \
    make install

# for seed corpus, use AFL++ PDF test cases
RUN cp -r /AFLplusplus/testcases/others/pdf /home/softsec/seeds

CMD ["/bin/bash"]
