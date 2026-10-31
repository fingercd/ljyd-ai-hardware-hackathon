@echo off
rem Resolve checkout, then load an optional ignored machine-specific configuration.
for %%I in ("%~dp0..") do set "LJYD_CHECKOUT=%%~fI"
if exist "%LJYD_CHECKOUT%\.local\environment.cmd" call "%LJYD_CHECKOUT%\.local\environment.cmd"
if not defined LJYD_WORKSPACE set "LJYD_WORKSPACE=%LJYD_CHECKOUT%"
if not defined LJYD_BOOTSTRAP_PYTHON (
  for /f "delims=" %%I in ('py -3.11 -c "import sys; print(sys.executable)"') do set "LJYD_BOOTSTRAP_PYTHON=%%I"
)
if not defined LJYD_BOOTSTRAP_PYTHON (
  echo ERROR: Python 3.11 was not found. Install Python 3.11 or set LJYD_BOOTSTRAP_PYTHON.
  exit /b 1
)
if not exist "%LJYD_BOOTSTRAP_PYTHON%" (
  echo ERROR: LJYD_BOOTSTRAP_PYTHON does not identify an existing executable.
  exit /b 1
)
if not exist "%LJYD_WORKSPACE%\ljyd-sdk\esp-idf\tools\idf.py" (
  echo ERROR: SDK is missing. Run git submodule update --init --recursive first.
  exit /b 1
)
for %%I in ("%LJYD_BOOTSTRAP_PYTHON%") do set "LJYD_BOOTSTRAP_DIR=%%~dpI"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONHOME="
set "PYTHONPATH="
set "VIRTUAL_ENV="
set "CONDA_PREFIX="
set "IDF_TOOLS_PATH=%LJYD_WORKSPACE%\.espressif"
set "ADF_PATH=%LJYD_WORKSPACE:\=/%/ljyd-sdk"
set "IDF_PATH=%ADF_PATH%/esp-idf"
if not defined IDF_GITHUB_ASSETS set "IDF_GITHUB_ASSETS=dl.espressif.cn/github_assets"
set "PIP_CACHE_DIR=%LJYD_WORKSPACE%\.local\pip-cache"
set "PATH=%LJYD_BOOTSTRAP_DIR%;%PATH%"
exit /b 0
