@echo off
setlocal
call "%~dp0env.cmd"
if errorlevel 1 exit /b 1
pushd "%LJYD_WORKSPACE%"
if errorlevel 1 exit /b 1
python -m scripts.camera_capture %*
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
