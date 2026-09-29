# Building the USD importer for Mari 8 (Windows)

This folder builds the USD importer from this repo, including the GeomSubset selection groups,
and swaps it in for the importer that ships with Mari 8.

## Why the normal README steps don't work for Mari 8

Mari 8 ships its own build of USD 25.08. Its libraries are called `fnusd.dll`, `fnusdGeom.dll` and so on,
and all USD code sits in the C++ namespace `fnInternal_v25_08`. A plugin built against a stock USD
looks for `usd_usd.dll` and `pxrInternal_v0_25_08` instead, and Mari can't load it.

So `build_usd.bat` builds USD 25.08 with the same library prefix and namespace. That USD is only used
to compile against. Inside Mari the plugin uses Mari's own USD libraries.

Versions, matched to what is in Mari 8's `Bundle\bin`:

| Component | Version                                                                  |
|-----------|--------------------------------------------------------------------------|
| USD       | 25.08                                                                    |
| oneTBB    | 2021.13.0                                                                |
| Python    | 3.11 (Mari ships 3.11.11, NuGet stops at 3.11.9, which is compatible)    |
| Compiler  | Visual Studio 2022 Build Tools, MSVC 14.44                               |
| Boost     | not needed any more                                                      |

## What needs to be installed

- Visual Studio 2022 Build Tools with the "Desktop development with C++" workload
- git
- CMake and Ninja: `pip install cmake ninja` (`config.bat` expects them in `C:\python312\Scripts`)
- Mari 8. The CAPI headers come from Mari 8.0v2-Alpha.1, because 8.0v1-Beta.2 ships without the SDK folder.

The scripts download everything else themselves (USD source, oneTBB, and Python 3.11 headers and libs).

## Steps

1. Check the paths in `config.bat`.
2. Run `build_usd.bat`. It downloads and builds USD into `BUILD_ROOT`. This is only needed once and takes
   about 10 minutes on a 16-thread machine.
3. Run `build_plugin.bat`. It builds `USDImport.dll` into `%BUILD_ROOT%\plugin-build`, then checks that every
   USD function the plugin uses exists in Mari's own USD libraries. The last line has to say `OK`.
4. Close Mari and run `install_mari8.bat` as administrator (right-click > Run as administrator).
   From Claude Code:
   `! powershell -Command "Start-Process 'D:\GitHub\MariUsdPlugins\build_mari8\install_mari8.bat' -Verb RunAs"`
   It keeps the original `MriUSDImport.dll` and `usdLoaderTab.py` as `.orig` and copies the new ones in.
5. To go back to the importer Mari shipped with, run `install_mari8.bat restore` as administrator.

After changing the plugin code, only steps 3 and 4 are needed.

## Testing

Load `test\geomsubset_test.usda` in Mari with "Create Face Selection Groups from GeomSubsets" switched on.
That's the new button next to "Create Face Selection Group per mesh", and it uses the same icon for now.

| Selection group | Faces                                                                   |
|-----------------|-------------------------------------------------------------------------|
| top             | Cube face 1 and all 4 Plane faces                                       |
| bottom          | Cube face 3                                                             |
| sides           | Cube faces 0, 2, 4, 5                                                   |
| left_half       | Plane faces 0 and 2                                                     |
| bad_indices     | Plane face 3. Face 42 doesn't exist and should show up as skipped in the log |
| corner_points   | shouldn't be created, it's a point subset                               |

"top" is one shared group when both meshes end up in the same Mari object.
If they are loaded as separate objects, each one gets its own "top" group.

## Things to know

- Mari 8's own `MriUSDImport.dll` also contains a USD camera importer. The code in this repo doesn't have that
  yet, so installing this build loses USD camera import until the repo catches up.
- `python\usdLoaderTab.py` in this repo is still the Mari 7 version. It only knows PySide2 and doesn't work in
  Mari 8, which uses Qt6. `mari8_python\mariUsd\usdLoaderTab.py` is Mari 8.0v1-Beta.2's own file with the
  GeomSubset button added, and that's the one the install script copies. If a newer Mari 8 build changes that
  file, redo the three additions on top of the new version: the icon, the button, and the `setGeoPluginAttribute` call.
- USD 25.08 dropped Boost. The plugin used `boost::shared_ptr` in one place, which is now `std::shared_ptr`.
  The plugin's CMakeLists still insists on the `BOOST_*` environment variables, so `build_plugin.bat` points
  them at an empty folder.
- CMake can't find the NuGet Python on its own because it isn't registered with Windows, so
  `build_plugin.bat` passes the Python paths in explicitly.
- The Jinja2 warning while configuring USD is harmless. It only affects USD's schema generation tools.
