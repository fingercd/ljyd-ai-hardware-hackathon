@echo off
rem CALL from a batch file. Environment changes affect this process only.
call "%~dp0workspace.cmd"
if errorlevel 1 exit /b 1
set "IDF_PYTHON_ENV_PATH=%IDF_TOOLS_PATH%\python_env\idf5.4_py3.11_env"
if not exist "%IDF_PYTHON_ENV_PATH%\Scripts\python.exe" (
  echo ERROR: ESP-IDF Python environment is not installed. Run scripts\setup.cmd.
  exit /b 1
)
rem Versions match the SDK's own tools.json and dev.bat. Do not use a system CMake.
set "TC=%IDF_TOOLS_PATH%\tools"
set "PATH=%IDF_PYTHON_ENV_PATH%\Scripts;%TC%\xtensa-esp-elf\esp-14.2.0_20241119\xtensa-esp-elf\bin;%TC%\cmake\3.30.2\bin;%TC%\ninja\1.12.1;%TC%\esp32ulp-elf\2.38_20240113\esp32ulp-elf\bin;%PATH%"
set "ESP_ROM_ELF_DIR=%TC%\esp-rom-elfs\20241011"
set "ESP_IDF_VERSION=5.4"
rem ccache 4.10.2 failed on this workspace's real Unicode path. Keep disabled.
set "IDF_CCACHE_ENABLE=0"
exit /b 0
