@echo off
rem Builds the USD import plugin from this repo against the USD made by build_usd.bat,
rem then checks it against the USD libraries of the Mari install in config.bat.

call "%~dp0config.bat"
call "%VCVARS%" || exit /b 1
set PATH=%TOOLS_DIR%;%PATH%

set USD_ROOT=%BUILD_ROOT%/usd
set TBB_DIR=%BUILD_ROOT%/oneapi-tbb-2021.13.0
set TBB_ROOT=%BUILD_ROOT%/oneapi-tbb-2021.13.0
set MARI_SDK_INCLUDE_DIR=%SDK_DIR%

rem USD 25.08 no longer uses Boost, but the plugin CMakeLists still insists on these being set
if not exist "%BUILD_ROOT%\no-boost" mkdir "%BUILD_ROOT%\no-boost"
set BOOST_ROOT=%BUILD_ROOT%/no-boost
set BOOST_INCLUDEDIR=%BUILD_ROOT%/no-boost
set BOOST_LIBRARYDIR=%BUILD_ROOT%/no-boost

rem The NuGet Python isn't registered with Windows, so CMake has to be told where it is
cmake -S "%~dp0.." -B "%BUILD_ROOT%\plugin-build" -G Ninja ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_INSTALL_PREFIX=%BUILD_ROOT%/plugin-install ^
    -DPython3_ROOT_DIR=%BUILD_ROOT%/python311/tools ^
    -DPython3_INCLUDE_DIR=%BUILD_ROOT%/python311/tools/include ^
    -DPython3_LIBRARY=%BUILD_ROOT%/python311/tools/libs/python311.lib || exit /b 1

cmake --build "%BUILD_ROOT%\plugin-build" || exit /b 1

rem Every USD function the plugin uses has to exist in Mari's own USD libraries, or Mari can't load it
"%BUILD_ROOT%\python311\tools\python.exe" "%~dp0check_imports.py" "%BUILD_ROOT%\plugin-build\USDImport.dll" "%MARI_DIR%\Bundle\bin" || exit /b 1
