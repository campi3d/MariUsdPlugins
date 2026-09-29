@echo off
rem Swaps Mari 8's bundled USD importer for the one built by build_plugin.bat. Needs to run as administrator.
rem The original files are kept as *.orig. Run with "restore" to put them back.

call "%~dp0config.bat"
set MARI_USD=%MARI_DIR%\Bundle\Usd\lib

if /i "%1"=="restore" goto restore

rem Only back up once, so running this twice never overwrites the real originals
if not exist "%MARI_USD%\MriUSDImport.dll.orig" copy /y "%MARI_USD%\MriUSDImport.dll" "%MARI_USD%\MriUSDImport.dll.orig" || goto failed
if not exist "%MARI_USD%\python\mariUsd\usdLoaderTab.py.orig" copy /y "%MARI_USD%\python\mariUsd\usdLoaderTab.py" "%MARI_USD%\python\mariUsd\usdLoaderTab.py.orig" || goto failed
copy /y "%BUILD_ROOT%\plugin-build\USDImport.dll" "%MARI_USD%\MriUSDImport.dll" || goto failed
copy /y "%~dp0mari8_python\mariUsd\usdLoaderTab.py" "%MARI_USD%\python\mariUsd\usdLoaderTab.py" || goto failed
echo Installed the GeomSubset USD importer into %MARI_USD%
pause
exit /b 0

:restore
copy /y "%MARI_USD%\MriUSDImport.dll.orig" "%MARI_USD%\MriUSDImport.dll" || goto failed
copy /y "%MARI_USD%\python\mariUsd\usdLoaderTab.py.orig" "%MARI_USD%\python\mariUsd\usdLoaderTab.py" || goto failed
echo Restored the original Mari USD importer
pause
exit /b 0

:failed
echo Failed. Make sure this runs as administrator and Mari is closed.
pause
exit /b 1
