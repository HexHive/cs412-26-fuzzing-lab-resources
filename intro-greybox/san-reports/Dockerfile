FROM archlinux:latest

RUN pacman -Sy --noconfirm archlinux-keyring \
 && pacman -Syu --noconfirm \
 && pacman -S  --noconfirm --needed \
      clang \
      binutils \
      diffutils \
      less \
      make \
      radare2 \
      pwndbg \
 && pacman -Scc --noconfirm \
 # Fix pwndbg/capstone6 symbol rename: CS_MODE_RISCVC -> CS_MODE_RISCV_C
 && python -c "\
import capstone6pwndbg as c; p=c.__file__;\
t=open(p).read();\
open(p,'w').write(t if 'CS_MODE_RISCVC' in t else t+'CS_MODE_RISCVC=CS_MODE_RISCV_C\n')"

# libdebug for the shadow memory demo script.
RUN pacman -Sy --noconfirm python-pip \
 && python -m pip install --break-system-packages libdebug \
 && pacman -Scc --noconfirm

WORKDIR /work
COPY bugs ./bugs
COPY run_reports.sh build_all.sh inspect.sh welcome.sh shadow_demo.py ./
RUN chmod +x run_reports.sh build_all.sh inspect.sh welcome.sh shadow_demo.py

# Pre-build every bug program with and without sanitizers.
RUN ./build_all.sh

# Put inspect on PATH and show the welcome banner on shell entry.
ENV TERM=xterm
RUN ln -s /work/inspect.sh /usr/local/bin/inspect \
 && echo 'source /work/welcome.sh' >> /etc/bash.bashrc

CMD ["./run_reports.sh"]
