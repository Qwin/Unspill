"""Build, test, and package a native binary on the current platform."""

import hashlib
import importlib.metadata
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
                    "--name", "unspill", "--paths", str(ROOT), "--distpath", str(ROOT / "dist"),
                    "--workpath", str(ROOT / "build/pyinstaller"), "--specpath", str(ROOT / "build"),
                    str(ROOT / "scripts/unspill_entry.py")], cwd=ROOT, check=True,
                   env={**os.environ, "PYINSTALLER_CONFIG_DIR": str(ROOT / "build/cache")})
    executable = ROOT / "dist" / ("unspill.exe" if os.name == "nt" else "unspill")
    subprocess.run([sys.executable, "-m", "unittest", "tests.test_cli", "-v"], cwd=ROOT,
                   env={**os.environ, "UNSPILL_TEST_EXECUTABLE": str(executable)}, check=True)
    subprocess.run([sys.executable, str(ROOT / "examples/recovery_demo.py"), "--unspill", str(executable)], check=True)
    system = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}[platform.system()]
    arch = {"AMD64": "x86_64", "aarch64": "arm64"}.get(platform.machine(), platform.machine())
    name = f"unspill-{system}-{arch}"
    folder = ROOT / "build" / name
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(executable, folder / executable.name)
    for filename in ("LICENSE", "NOTICE", "README.md", "THIRD_PARTY.md"):
        shutil.copy2(ROOT / filename, folder / filename)
    licenses = folder / "licenses"
    licenses.mkdir(exist_ok=True)
    candidates = [Path(sysconfig.get_path("stdlib")) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE.txt"]
    python_license = next((path for path in candidates if path.exists()), None)
    if python_license is None:
        raise RuntimeError("Cannot locate the Python license; refusing to package without it.")
    shutil.copy2(python_license, licenses / "PYTHON-LICENSE.txt")
    for package in ("pyinstaller", "altgraph", "packaging", "pyinstaller-hooks-contrib"):
        dist = importlib.metadata.distribution(package)
        for path in dist.files or []:
            if "dist-info" in str(path) and ("license" in str(path).lower() or "copying" in str(path).lower()):
                source = Path(dist.locate_file(path))
                if source.is_file():
                    shutil.copy2(source, licenses / f"{package}-{source.name}")
    archive = Path(shutil.make_archive(str(ROOT / "dist" / name), "zip", root_dir=folder))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (archive.parent / (archive.name + ".sha256")).write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Built and tested: {archive}")


if __name__ == "__main__":
    main()
