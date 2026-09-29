@echo off
rem Paths shared by all the Mari 8 build scripts. Change these to match your machine.

rem Where USD, its dependencies and the plugin get built (needs about 3 GB)
set BUILD_ROOT=D:\Build\MariUsd8

rem The Mari 8 install the plugin gets deployed into
set MARI_DIR=C:\Program Files\Mari8.0v1-Beta.2

rem Mari CAPI headers. 8.0v1-Beta.2 ships without an SDK, so they come from 8.0v2-Alpha.1
set SDK_DIR=C:/Program Files/Mari8.0v2-Alpha.1/Bundle/SDK/Assets/include

rem Visual Studio 2022 C++ compiler setup
set VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat

rem Folder holding cmake.exe and ninja.exe (pip install cmake ninja)
set TOOLS_DIR=C:\python312\Scripts
