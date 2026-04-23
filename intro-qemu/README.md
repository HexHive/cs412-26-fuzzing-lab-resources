# AFL++ QEMU Persistent Fuzzing Lab for Xpdf pdfinfo

This lab discusses how to fuzz with AFL++ / QEMU and QASAN.
To make this interactive, we will focus on one piece of software: `pdfinfo` from `Xpdf 3.02`.

## 1. Build Xpdf 3.02

Build it **without** `afl-clang-fast` or `afl-clang-lto`. 
For didactic purposes, we use an open-source target to do our closed-source testing.

```
wget https://dl.xpdfreader.com/old/xpdf-3.02.tar.gz
tar -xvzf xpdf-3.02.tar.gz
cd xpdf-3.02
sudo apt update && sudo apt install -y build-essential gcc
./configure --prefix="$HOME/fuzzing_xpdf/install/"
make
make install
```

## 2. Create a seed corpus

As we learned in the first lab, it is important to have seeds to work from.
We download them off of the internet, of course.

```
cd ..
mkdir pdf_examples
cd pdf_examples

wget https://github.com/mozilla/pdf.js-sample-files/raw/master/helloworld.pdf
wget https://sample-files.com/downloads/documents/pdf/basic-text.pdf
```

## 3. Verify the target works
Before fuzzing, we do some small sanity checks:

```
$HOME/fuzzing_xpdf/install/bin/pdfinfo -box -meta helloworld.pdf
$HOME/fuzzing_xpdf/install/bin/pdfinfo -box -meta basic-text.pdf
```

Which should hopefully yield:

```
[AFL++ 674faf9b66fb] /work # $HOME/fuzzing_xpdf/install/bin/pdfinfo -box -meta helloworld.pdf
$HOME/fuzzing_xpdf/install/bin/pdfinfo -box -meta basic-text.pdf
Tagged:         no
Pages:          1
Encrypted:      no
Page size:      200 x 200 pts
MediaBox:           0.00     0.00   200.00   200.00
CropBox:            0.00     0.00   200.00   200.00
BleedBox:           0.00     0.00   200.00   200.00
TrimBox:            0.00     0.00   200.00   200.00
ArtBox:             0.00     0.00   200.00   200.00
File size:      678 bytes
Optimized:      no
PDF version:    1.7
Title:          Sample Document for PDF Testing
Creator:        Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36
Producer:       Skia/PDF m126
CreationDate:   Tue Jul  9 13:31:41 2024
ModDate:        Tue Jul  9 13:31:41 2024
Tagged:         yes
Pages:          1
Encrypted:      no
Page size:      594.96 x 841.92 pts (A4)
MediaBox:           0.00     0.00   594.96   841.92
CropBox:            0.00     0.00   594.96   841.92
BleedBox:           0.00     0.00   594.96   841.92
TrimBox:            0.00     0.00   594.96   841.92
ArtBox:             0.00     0.00   594.96   841.92
File size:      74656 bytes
Optimized:      no
PDF version:    1.4
```

## 4. Baseline AFL++ QEMU fuzzing

We Start with a normal QEMU-mode run before enabling persistence:

- QEMU mode with -Q
- Timeout with 2000ms

```
afl-fuzz -Q -m none -i ./pdf_examples/ -o ./afl_out/ -t 2000 -- \
  $HOME/fuzzing_xpdf/install/bin/pdfinfo @@
```

However, we are slow! How do we speed it up? With persistent mode!

- Persistent mode with AFL_QEMU_PERSISTENT_ADDR  --> use an address to start from!
- Register restore with AFL_QEMU_PERSISTENT_GPR=1 --> Save general purpose registers (GPRs)
- Optional QASAN with AFL_USE_QASAN=1 --> Later: use QASAN for heap sanitization.

## 5. Inspect the memory map

To see where QEMU maps the PIE binary at runtime:
`AFL_QEMU_DEBUG_MAPS=1 afl-qemu-trace $HOME/fuzzing_xpdf/install/bin/pdfinfo`

Example mapping that was observed during debugging:

```
4000000000-4000037000 r--p 00000000 00:36 12760882 /root/fuzzing_xpdf/install/bin/pdfinfo
4000037000-40000ae000 r-xp 00037000 00:36 12760882 /root/fuzzing_xpdf/install/bin/pdfinfo
40000ae000-40000d3000 r--p 000ae000 00:36 12760882 /root/fuzzing_xpdf/install/bin/pdfinfo
40000d3000-40000db000 r--p 000d3000 00:36 12760882 /root/fuzzing_xpdf/install/bin/pdfinfo
40000db000-4000102000 rw-p 000db000 00:36 12760882 /root/fuzzing_xpdf/install/bin/pdfinfo
```

Another stable mapping that was observed with a different setup (using QASAN) was:

```
7ffff6119000-7ffff6150000 r--p 00000000 00:36 12760882 /root/fuzzing_xpdf/install/bin/pdfinfo
7ffff6150000-7ffff61c7000 r-xp 00037000 00:36 12760882 /root/fuzzing_xpdf/install/bin/pdfinfo
7ffff61c7000-7ffff61ec000 r--p 000ae000 00:36 12760882 /root/fuzzing_xpdf/install/bin/pdfinfo
7ffff61ec000-7ffff61f4000 r--p 000d3000 00:36 12760882 /root/fuzzing_xpdf/install/bin/pdfinfo
7ffff61f4000-7ffff621b000 rw-p 000db000 00:36 12760882 /root/fuzzing_xpdf/install/bin/pdfinfo
```

## 6. Find the persistent address

[!IMPORTANT] Open the binary in Ghidra to find the function entry you want to use for the persistent loop.
The persistent start should be a clean function entry whenever possible.

The function offset identified during "reversing" was:
`0x39bc0 (main)`

For the `0x4000000000` PIE base, that becomes: `0x4000039bc0`
For the `0x7ffff6119000` / `0x7ffff6150000` mapping that was observed during debugging, that becomes: `0x7ffff6152bc0`

Address calculation
Using the 0x4000000000-based map:
- text mapping starts at `0x4000037000`
- file offset of text mapping is `0x37000`
- target function offset is `0x39bc0`

```
0x39bc0 - 0x37000 = 0x2bc0
0x4000037000 + 0x2bc0 = 0x4000039bc0
Using the 0x7ffff6150000 text mapping:
0x39bc0 - 0x37000 = 0x2bc0
0x7ffff6150000 + 0x2bc0 = 0x7ffff6152bc0
```

## 7. Final command without and with QASAN

```
This is the final command used for the persistent run without QASAN:
AFL_QEMU_PERSISTENT_GPR=1 AFL_QEMU_PERSISTENT_ADDR=0x4000039bc0 \
afl-fuzz -Q -m none -i ./pdf_examples/ -o ./afl_out_qasan -t 2000 -- \
$HOME/fuzzing_xpdf/install/bin/pdfinfo @@
```

This is the final command used for the persistent run with QASAN:

```
AFL_USE_QASAN=1 AFL_QEMU_PERSISTENT_GPR=1 AFL_QEMU_PERSISTENT_ADDR=0x7ffff6152bc0 \
afl-fuzz -Q -m none -i ./pdf_examples/ -o ./afl_out_qasan -t 2000 -- \
$HOME/fuzzing_xpdf/install/bin/pdfinfo @@
```

## 8. Why the addresses differ

The function offset is the same in both cases: `0x39bc0`

The difference comes from the runtime PIE base used by QEMU for the target binary.
- Without ASAN: QEMU mapped the binary at a base consistent with 0x4000000000, giving: `AFL_QEMU_PERSISTENT_ADDR=0x4000039bc0`
- In another setup, the observed mapping produced: `AFL_QEMU_PERSISTENT_ADDR=0x7ffff6152bc0`

## 10. Docker note for deterministic mapping
Inside Docker, setarch -R may fail under the default seccomp policy because the personality syscall is restricted :)

A working way to allow `setarch` is to start the container with:
docker run --rm -it --privileged <image> bash
Then inside the container:
setarch "$(uname -m)" -R bash

12. Known-good commands

- Check the map: `AFL_QEMU_DEBUG_MAPS=1 afl-qemu-trace $HOME/fuzzing_xpdf/install/bin/pdfinfo`
- Fuzz without QASAN: 
```
AFL_QEMU_PERSISTENT_GPR=1 AFL_QEMU_PERSISTENT_ADDR=0x4000039bc0 \
afl-fuzz -Q -m none -i ./pdf_examples/ -o ./afl_out_qasan -t 2000 -- \
$HOME/fuzzing_xpdf/install/bin/pdfinfo @@
```
- Fuzz with QASAN:
```
AFL_USE_QASAN=1 AFL_QEMU_PERSISTENT_GPR=1 AFL_QEMU_PERSISTENT_ADDR=0x7ffff6152bc0 \
afl-fuzz -Q -m none -i ./pdf_examples/ -o ./afl_out_qasan -t 2000 -- \
$HOME/fuzzing_xpdf/install/bin/pdfinfo @@
```

The offset found in Ghidra stays the same, but the final persistent address must match the runtime base shown by QEMU!

