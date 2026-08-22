# Building and booting the OS (xv6-riscv) on this machine

This kit compiles **xv6-riscv** — MIT's small, teaching operating system in the
Unix v6 / Plan 9 research lineage — and boots it in QEMU, without installing
any compiler or emulator on Windows itself. Everything runs inside a pinned
Docker image; the source code persists in a Docker volume between runs.

If you actually meant a *different* Plan 9-style OS repo, see "Swapping in a
different OS" at the bottom — the container setup is reusable.

---

## 0. One-time setup (YOU ARE HERE — ~5 minutes, needs admin + reboot)

Docker Desktop is installed and running, but its Linux engine requires the
**WSL2** Windows feature, which is currently not enabled (that's why
`docker info` hangs right now). Enable it once:

1. Open **PowerShell as Administrator** (right-click Start → "Windows
   PowerShell (Admin)" or "Terminal (Admin)").
2. Run:
   ```powershell
   wsl --install --no-distribution
   ```
   (If it reports a missing virtualization feature, also enable
   "Virtual Machine Platform" / virtualization in your BIOS — most machines
   already have it on.)
3. **Reboot** when asked.
4. After reboot, start **Docker Desktop** and wait until it says
   **"Engine running"** (whale icon, bottom-left of its window).

That's the only manual step. Everything else is one double-click.

## 1. Everyday use: boot the OS

Double-click **`boot.bat`** (or run it from a terminal).

What it does, in order:
- builds the `xv6-lab` Docker image (Ubuntu 24.04 + RISC-V cross-compiler +
  QEMU) — a few minutes the **first time only**;
- clones the xv6-riscv source into the persistent `xv6-src` volume
  (first time only);
- compiles the kernel and all user programs (`make`);
- boots the result in QEMU.

You'll land on the xv6 shell:

```
xv6 kernel is booting

init: starting sh
$
```

Try things at the `$` prompt: `ls`, `cat README`, `echo hello`,
`grep the README`, `mkdir demo; ls`. There's even `lsproc`-style inspection
in some builds; the xv6 book (`make pdfdoc` upstream) explains the system.

**To exit QEMU:** press `Ctrl-A`, release, then press `X`. (That's QEMU's
escape sequence; Ctrl-C alone won't quit.)

Edit the source in `xv6-riscv/` (inside the volume — see "Getting at the
source" below), run `boot.bat` again, and it rebuilds and reboots. That's
the entire development loop.

## 2. Verify everything works (headless self-test)

Double-click **`verify.bat`**. It does a clean rebuild, boots the kernel
without a window, runs a couple of commands (`echo`, `ls`), and prints a
PASS/FAIL report ending in `RESULT: ALL CHECKS PASSED`. Use it whenever you
want proof the toolchain and boot still work after changes.

## 3. What gets built

| Artifact | What it is |
|---|---|
| `kernel/kernel` | The kernel ELF — the "bootable output" (QEMU boots it directly) |
| `fs.img` | The user-filesystem image: `sh`, `ls`, `cat`, `echo`, and the rest of the user programs |
| `kernel/kernel.asm` | Disassembly for debugging (`make gdb` works inside the container) |

## Getting at the source (it lives in a Docker volume)

The source persists in the `xv6-src` volume, not a normal folder. To browse
or edit it on Windows, copy it out:

```bat
docker run --rm -v xv6-src:/lab -v C:\Users\acer\xv6-lab\src:/out ubuntu:24.04 cp -r /lab/xv6-riscv /out/
```

Now edit `C:\Users\acer\xv6-lab\src\xv6-riscv\...`, then push it back (or
just build from the checked-out copy by mounting it instead of the volume):

```bat
docker run -it --rm -v C:\Users\acer\xv6-lab\src\xv6-riscv:/lab/xv6-riscv xv6-lab
```

## Troubleshooting

- **"Docker engine is not running"** — start Docker Desktop, wait for
  "Engine running", rerun the `.bat`.
- **`docker info` hangs forever** — WSL2 still not enabled; redo step 0.
- **First run is slow** — it downloads Ubuntu + the cross-compiler
  (~400 MB) once. Subsequent runs start in seconds.
- **Start over completely** —
  `docker volume rm xv6-src` (deletes the source; it re-clones next run).
- **Port of QEMU never opens / blank screen** — make sure you're running the
  `.bat` from a real terminal window (double-click is fine); QEMU is
  text-mode only here (`-nographic`), so output appears in that same window.

## Building natively on Linux or macOS (no Docker)

On a real Unix box you don't need any of this — the upstream flow:

```sh
sudo apt-get install git build-essential gdb-multiarch \
     qemu-system-misc gcc-riscv64-unknown-elf binutils-riscv64-unknown-elf
git clone https://github.com/mit-pdos/xv6-riscv.git
cd xv6-riscv && make qemu     # exit: Ctrl-A, then X
```

(On macOS: `brew install riscv-tools qemu` or use a Docker like above.)

## Swapping in a different OS

The container (RISC-V toolchain + QEMU) suits xv6 and other RISC-V teaching
kernels. For a different repo, edit the `git clone` URL in
`scripts/entry.sh` and, if the build differs, the `make` line. For a full
Plan 9 (e.g. 9front), the model changes — those build under their own
toolchain inside the running system rather than cross-compiled from Unix;
happy to extend this kit that way if that's what you have.
