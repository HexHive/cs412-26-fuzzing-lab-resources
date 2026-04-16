Table of Contents
_________________

1. CS-412 Fuzzing Lab 2 --- Introduction to Greybox Fuzzing and Sanitizers
.. 1. Contents
.. 2. Prerequisites
.. 3. Getting Started


1 CS-412 Fuzzing Lab 2 --- Introduction to Greybox Fuzzing and Sanitizers
=========================================================================

  Slides: [Greybox Fuzzing and Sanitizers].

  This directory contains the material presented during Fuzzing Lab 2 of
  /CS-412: Software Security/ at EPFL, 2026. The lab covers two core
  topics: *coverage-guided (greybox) fuzzing* with AFL++ and *compiler
  sanitizers* (AddressSanitizer and UndefinedBehaviorSanitizer). Both
  topics are demonstrated through self-contained, Docker-based
  exercises.


[Greybox Fuzzing and Sanitizers]
<https://docs.google.com/presentation/d/1vdEUggIJTtoe0_DfAxIiZy4ARoJwdAig4scQzXf7CEg/edit?slide=id.g3d5cefbae9d_2_0#slide=id.g3d5cefbae9d_2_0>

1.1 Contents
~~~~~~~~~~~~

  - [`afl-intro/'] --- Greybox fuzzing with AFL++. Walks through fuzzing
    *Xpdf 3.02* (`pdftotext') to rediscover [CVE-2019-13288], an
    uncontrolled recursion bug. Covers compiling a target with
    `afl-clang-fast', running `afl-fuzz', and triaging crashes with GDB.
  - [`san-reports/'] --- Sanitizers under the hood. Provides an
    interactive environment for inspecting how ASan and UBSan instrument
    compiled code. Includes pre-built binaries, an `inspect' tool for
    comparing plain vs. sanitized assembly, and a `shadow_demo.py'
    script that visualises heap red zones and shadow memory.


[`afl-intro/'] <file:afl-intro/>

[CVE-2019-13288]
<https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-13288>

[`san-reports/'] <file:san-reports/>


1.2 Prerequisites
~~~~~~~~~~~~~~~~~

  - Docker (all tools run inside containers, so no local compiler setup
    is needed)
  - Make (the actual entry point)


1.3 Getting Started
~~~~~~~~~~~~~~~~~~~

  Each subdirectory has its own `README' with detailed instructions. In
  short:

  ,----
  | # greybox fuzzing exercise
  | cd afl-intro
  | make build   # build the Docker image
  | make fuzz    # start fuzzing Xpdf with AFL++
  | 
  | # sanitizer demo
  | cd san-reports
  | make run     # build the image and open an interactive shell
  `----

  In both cases, you could be required to perform a `make clean' before
  building.
