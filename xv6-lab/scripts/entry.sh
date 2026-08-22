#!/bin/sh
# Shared logic for boot.bat / verify.bat.
#   entry.sh          -> build xv6, then boot it interactively in QEMU
#   entry.sh verify   -> clean build + headless boot self-test, prints a report
set -e

cd /lab
if [ ! -d xv6-riscv ]; then
  echo "== first run: cloning xv6-riscv =="
  git clone --depth 1 https://github.com/mit-pdos/xv6-riscv.git
fi
cd xv6-riscv

if [ "$1" = "verify" ]; then
  echo "== clean build =="
  make clean >/dev/null
  make 2>&1 | tail -3
  ls -lh kernel/kernel fs.img

  echo "== headless boot test (auto-exits) =="
  rm -f /tmp/boot.log
  ( sleep 10; echo "echo BOOT_MARKER_42"; sleep 4; echo "ls"; sleep 4 ) \
    | timeout 60 make qemu > /tmp/boot.log 2>&1 || true

  echo "-- boot log (first 25 lines) --"
  head -25 /tmp/boot.log
  echo "-- checks --"
  ok=1
  grep -q "xv6 kernel is booting" /tmp/boot.log && echo "PASS: kernel booted" || { echo "FAIL: kernel did not boot"; ok=0; }
  grep -q "BOOT_MARKER_42"      /tmp/boot.log && echo "PASS: shell ran a command" || { echo "FAIL: shell did not run"; ok=0; }
  grep -q "README"              /tmp/boot.log && echo "PASS: ls listed the filesystem" || { echo "FAIL: ls output missing"; ok=0; }
  [ "$ok" = 1 ] && echo "RESULT: ALL CHECKS PASSED" || echo "RESULT: FAILURES DETECTED"
  [ "$ok" = 1 ]
else
  echo "== building xv6 (skip with Ctrl-C if already built) =="
  make
  echo "== booting in QEMU — exit with Ctrl-A then X =="
  exec make qemu
fi
