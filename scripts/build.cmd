@echo off
setlocal
call "%~dp0env.cmd"
if errorlevel 1 exit /b 1
rem Keep CMake's build directory on the ASCII alias. idf.py canonicalizes junctions.
rem BUILD ONLY: no flashing, serial opening, reset, or erase operation.
python "%IDF_PATH%/tools/check_python_dependencies.py"
if errorlevel 1 exit /b 1
cmake -G Ninja -S "%ADF_PATH%/apps" -B "%LJYD_WORKSPACE%/artifacts/build" -DPYTHON_DEPS_CHECKED=1 -DPYTHON="%IDF_PYTHON_ENV_PATH%\Scripts\python.exe" -DESP_PLATFORM=1 -DCCACHE_ENABLE=0
if errorlevel 1 exit /b 1
python "%~dp0normalize_build_paths.py"
if errorlevel 1 exit /b 1
cmake --build "%LJYD_WORKSPACE%/artifacts/build" --parallel
exit /b %ERRORLEVEL%
