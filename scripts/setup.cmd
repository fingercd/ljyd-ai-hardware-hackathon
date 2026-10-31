@echo off
setlocal
call "%~dp0workspace.cmd"
if errorlevel 1 exit /b 1
rem Install only the pinned SDK's ESP32-S3 tools, isolated from system Python.
call "%IDF_PATH%\install.bat" esp32s3
exit /b %ERRORLEVEL%
