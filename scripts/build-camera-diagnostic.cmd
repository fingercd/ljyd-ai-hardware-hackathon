@echo off
setlocal
call "%~dp0env.cmd"
if errorlevel 1 exit /b 1
set "ADF_PATH=%LJYD_WORKSPACE:\=/%/.local/camera-diagnostic-sdk"
set "IDF_PATH=%ADF_PATH%/esp-idf"
set "OUT=%LJYD_WORKSPACE%/artifacts/camera-diagnostic-build"
cmake -G Ninja -S "%ADF_PATH%/apps" -B "%OUT%" -DPYTHON_DEPS_CHECKED=1 -DPYTHON="%IDF_PYTHON_ENV_PATH%\Scripts\python.exe" -DESP_PLATFORM=1 -DCCACHE_ENABLE=0 -DPROJECT_VER=25cb-camera-diag1
if errorlevel 1 exit /b 1
python "%~dp0normalize_build_paths.py" "%OUT%"
if errorlevel 1 exit /b 1
cmake --build "%OUT%" --parallel
exit /b %ERRORLEVEL%
