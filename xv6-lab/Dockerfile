# xv6-riscv build & run environment — pinned, self-contained.
# Everything needed to compile xv6 and boot it in QEMU lives in this image,
# so nothing has to be installed on Windows itself.
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-riscv64-unknown-elf \
        binutils-riscv64-unknown-elf \
        qemu-system-misc \
        git \
        make \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/entry.sh /usr/local/bin/entry.sh
RUN chmod +x /usr/local/bin/entry.sh

WORKDIR /lab
ENTRYPOINT ["/usr/local/bin/entry.sh"]
