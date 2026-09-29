@echo off
rem Builds OpenUSD 25.08 the way Mari 8 ships it (fn lib prefix, fnInternal_v25_08 namespace).
rem Downloads the USD source, oneTBB and Python 3.11 first if they are not there yet.
rem Imaging, tools and tests are left out, the plugin only needs the core USD libraries.
rem Only needs to run once.

call "%~dp0config.bat"
call "%VCVARS%" || exit /b 1
set PATH=%TOOLS_DIR%;%PATH%

if not exist "%BUILD_ROOT%\downloads" mkdir "%BUILD_ROOT%\downloads"

rem Same oneTBB version as the tbb12.dll in Mari 8
if not exist "%BUILD_ROOT%\oneapi-tbb-2021.13.0" (
    curl -L -o "%BUILD_ROOT%\downloads\onetbb.zip" https://github.com/uxlfoundation/oneTBB/releases/download/v2021.13.0/oneapi-tbb-2021.13.0-win.zip || exit /b 1
    tar -xf "%BUILD_ROOT%\downloads\onetbb.zip" -C "%BUILD_ROOT%" || exit /b 1
)

rem Mari 8 ships Python 3.11.11. 3.11.9 is the last 3.11 on NuGet and is compatible
if not exist "%BUILD_ROOT%\python311" (
    curl -L -o "%BUILD_ROOT%\downloads\python311.nupkg" https://www.nuget.org/api/v2/package/python/3.11.9 || exit /b 1
    mkdir "%BUILD_ROOT%\python311"
    tar -xf "%BUILD_ROOT%\downloads\python311.nupkg" -C "%BUILD_ROOT%\python311" || exit /b 1
)

if not exist "%BUILD_ROOT%\OpenUSD" (
    git clone --depth 1 --branch v25.08 https://github.com/PixarAnimationStudios/OpenUSD.git "%BUILD_ROOT%\OpenUSD" || exit /b 1
)

cmake -S "%BUILD_ROOT%\OpenUSD" -B "%BUILD_ROOT%\usd-build" -G Ninja ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_INSTALL_PREFIX=%BUILD_ROOT%/usd ^
    -DPXR_SET_INTERNAL_NAMESPACE=fnInternal_v25_08 ^
    -DPXR_LIB_PREFIX=fn ^
    -DPXR_BUILD_IMAGING=OFF ^
    -DPXR_BUILD_USD_IMAGING=OFF ^
    -DPXR_BUILD_USDVIEW=OFF ^
    -DPXR_BUILD_EXEC=OFF ^
    -DPXR_BUILD_USD_VALIDATION=OFF ^
    -DPXR_BUILD_TESTS=OFF ^
    -DPXR_BUILD_EXAMPLES=OFF ^
    -DPXR_BUILD_TUTORIALS=OFF ^
    -DPXR_BUILD_USD_TOOLS=OFF ^
    -DPXR_BUILD_DOCUMENTATION=OFF ^
    -DPXR_ENABLE_GL_SUPPORT=OFF ^
    -DPXR_ENABLE_PYTHON_SUPPORT=ON ^
    -DPython3_EXECUTABLE=%BUILD_ROOT%/python311/tools/python.exe ^
    -DTBB_DIR=%BUILD_ROOT%/oneapi-tbb-2021.13.0/lib/cmake/tbb || exit /b 1

cmake --build "%BUILD_ROOT%\usd-build" --target install || exit /b 1
