Table of Contents
_________________

1. Intro to greybox fuzzing with AFL++
.. 1. Goal
.. 2. What you will learn
.. 3. Quick start
.. 4. How it works
.. 5. Available make targets
.. 6. Triaging a crash
.. 7. Files
.. 8. References


1 Intro to greybox fuzzing with AFL++
=====================================

1.1 Goal
~~~~~~~~

  Fuzz *Xpdf 3.02* (`pdftotext') to rediscover [CVE-2019-13288], an
  *uncontrolled recursion* bug in the PDF parser that leads to stack
  exhaustion and a crash.

  Based on [Fuzzing101 Exercise 1] by Antonio Morales.


[CVE-2019-13288]
<https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-13288>

[Fuzzing101 Exercise 1]
<https://github.com/antonio-morales/Fuzzing101/tree/main/Exercise%201>


1.2 What you will learn
~~~~~~~~~~~~~~~~~~~~~~~

  - How to compile a target with AFL++ instrumentation
    (`afl-clang-fast')
  - How to run `afl-fuzz' on a real-world program
  - How to triage crashes with GDB
  - The difference between grey-box (coverage-guided) and black-box
    (random) fuzzing


1.3 Quick start
~~~~~~~~~~~~~~~

  ,----
  | make build          # build the Docker image (~5 min)
  | make fuzz           # start grey-box fuzzing
  `----

  That's it! AFL++ will open its status screen. Watch the *"saved
  crashes"* counter --- once it's >= 1, you've found the bug. This can
  take a few minutes up to a couple of hours depending on your machine.


1.4 How it works
~~~~~~~~~~~~~~~~

  The Docker image: 1. Downloads Xpdf 3.02 source code 2. Compiles it
  with `afl-clang-fast' (AFL++'s compiler wrapper that inserts coverage
  instrumentation) 3. Use a few sample PDF files as seed inputs

  When you run `make fuzz', it executes:

  ,----
  | afl-fuzz -i seeds/ -o out/ -- install/bin/pdftotext @@ /tmp/output
  `----

   Flag                        Meaning                                                      
  ------------------------------------------------------------------------------------------
   `-i seeds/'                 Directory with seed input files (sample PDFs)                
   `-o out/'                   Directory where AFL++ stores results and crashes             
   `--'                        Separator between AFL++ options and the target command       
   `pdftotext @@ /tmp/output'  The target command. `@@' is replaced by each test input file 


1.5 Available make targets
~~~~~~~~~~~~~~~~~~~~~~~~~~

   Command       Description                                                            
  --------------------------------------------------------------------------------------
   `make build'  Build the Docker image                                                 
   `make fuzz'   *Grey-box* fuzzing --- AFL++ uses coverage feedback to guide mutations 
   `make run'    Drop into the container with a shell                                   
   `make shell'  Open a shell in an already running container                           
   `make clean'  Remove containers and image                                            


1.6 Triaging a crash
~~~~~~~~~~~~~~~~~~~~

  Once AFL++ finds a crash, open a shell in the container:

  ,----
  | make shell
  `----

  Inside the container, reproduce the crash:

  ,----
  | install/bin/pdftotext out/default/crashes/<crash-file> /tmp/out
  `----

  You should see a segmentation fault. To investigate, use GDB:

  ,----
  | gdb --args install/bin/pdftotext out/default/crashes/<crash-file> /tmp/out
  `----

  Inside GDB:

  ,----
  | (gdb) run
  | (gdb) bt
  `----

  The backtrace will show many repeated calls to `Parser::getObj' ---
  this is the infinite recursion described in CVE-2019-13288.


1.7 Files
~~~~~~~~~

   File          Purpose                                                                    
  ------------------------------------------------------------------------------------------
   `Dockerfile'  Builds Xpdf with AFL++ instrumentation + a vanilla copy for black-box mode 
   `Makefile'    Convenience targets for building and fuzzing                               
   `README.org'  This file                                                                  
   `README.txt'  Plain text version of this file                                            


1.8 References
~~~~~~~~~~~~~~

  - [Fuzzing101 Exercise 1]
  - [AFL++ documentation]
  - [CVE-2019-13288]


[Fuzzing101 Exercise 1]
<https://github.com/antonio-morales/Fuzzing101/tree/main/Exercise%201>

[AFL++ documentation] <https://aflplus.plus/docs/>

[CVE-2019-13288] <https://www.cvedetails.com/cve/CVE-2019-13288/>
