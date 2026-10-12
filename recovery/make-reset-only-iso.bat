@echo off
rem Drag your rlx-recovery .iso onto this file to make a Factory-Reset-only copy:
rem same recovery stick (sign-in, Factory Reset), without the Deploy image and
rem installer. Writes <name>-reset-only.iso next to it. Needs Python 3 (python.org).
setlocal
if "%~1"=="" (
  echo Drag the rlx-recovery .iso file onto this .bat file.
  pause
  exit /b 2
)
set "PY=python"
where py >nul 2>&1 && set "PY=py -3"
%PY% "%~dp0patch-deploy-iso.py" "%~1" --reset-only
pause
