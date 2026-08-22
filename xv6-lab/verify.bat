@echo off
rem Headless self-test: clean build, boot, run commands, print PASS/FAIL report.
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
docker run --rm -v xv6-src:/lab xv6-lab verify

endlocal
