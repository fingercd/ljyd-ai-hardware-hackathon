@echo off
setlocal
call "%~dp0env.cmd"
if errorlevel 1 exit /b 1
rem Enumerate ports without opening, resetting, or writing to them.
python -m serial.tools.list_ports -v
exit /b %ERRORLEVEL%
