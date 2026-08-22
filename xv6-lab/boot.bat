@echo off
rem One command: compile xv6 and boot it in QEMU (interactive).
rem First run also downloads the toolchain image and the xv6 source.
setlocal
cd /d %~dp0

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker engine is not running. Start Docker Desktop, wait until it says
  echo "Engine running", then run this file again.
  pause
  exit /b 1
)

docker build -t xv6-lab .
if errorlevel 1 ( echo Image build failed. & pause & exit /b 1 )

docker volume create xv6-src >nul
docker run -it --rm -v xv6-src:/lab xv6-lab

endlocal
