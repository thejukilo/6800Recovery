@echo off
rem Drag your rlx-recovery .iso onto this file to make its Deploy option work.
rem Writes <name>-deploy-customized.iso next to it. Needs Python 3 (python.org).
setlocal
if "%~1"=="" (
  echo Drag the rlx-recovery .iso file onto this .bat file.
  pause
  exit /b 2
)
set "PY=python"
where py >nul 2>&1 && set "PY=py -3"
%PY% "%~dp0patch-deploy-iso.py" %*
pause
