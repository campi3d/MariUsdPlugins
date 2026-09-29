"""Checks that a built plugin only uses USD functions that a Mari install actually provides."""

import re
import subprocess
import sys
from pathlib import Path

# Comes from the Visual Studio environment that build_plugin.bat sets up
DUMPBIN = "dumpbin"


def dumpbin(*args: str) -> str:
    """Run dumpbin and return its text output."""
    return subprocess.run([DUMPBIN, *args], capture_output=True, text=True, check=True).stdout


def imports_by_dll(plugin: Path) -> dict[str, set[str]]:
    """Return the symbols the plugin imports, grouped by the DLL they come from."""
    result: dict[str, set[str]] = {}
    current = None
    for line in dumpbin("/imports", str(plugin)).splitlines():
        stripped = line.strip()
        if re.fullmatch(r"[\w.\-]+\.dll", stripped, re.IGNORECASE):
            current = stripped.lower()
            result[current] = set()
        elif current and re.fullmatch(r"[0-9A-Fa-f]+\s+\S+", stripped):
            # Symbol lines are "<hint> <name>", header lines have more words
            result[current].add(stripped.split()[1])
    return result


def exports(dll: Path) -> set[str]:
    """Return the symbol names a DLL exports."""
    names = set()
    for line in dumpbin("/exports", str(dll)).splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0].isdigit():
            names.add(parts[3])
    return names


def main(plugin: Path, mari_bin: Path) -> int:
    """Compare the plugin's imports against the DLLs in Mari's bin folder."""
    failures = 0
    for dll, symbols in sorted(imports_by_dll(plugin).items()):
        mari_dll = mari_bin / dll
        if not mari_dll.exists():
            # System DLLs live elsewhere, only Mari's own ones matter here
            if dll.startswith(("fn", "tbb", "python")):
                print(f"MISSING DLL  {dll}")
                failures += 1
            continue
        missing = symbols - exports(mari_dll)
        print(f"{dll:<24} {len(symbols):>4} imports, {len(missing)} missing")
        for name in sorted(missing):
            print(f"    {name}")
        failures += len(missing)
    print("OK" if failures == 0 else f"FAILED: {failures} problems")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
