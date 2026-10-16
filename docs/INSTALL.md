# Installing BGit

[README](../README.md) · [Command reference](COMMANDS.md)

BGit is an alpha for ordinary local Git repositories on Windows, macOS, and Linux.
Git must be installed and available on `PATH` for every installation method.

## One-command installation with pipx

With Python 3.11+ and [pipx](https://pipx.pypa.io/stable/installation/) installed:

```sh
pipx install "git+https://github.com/Qwin/BGit.git@v0.3.0-alpha.1"
bgit --version
```

pipx installs BGit into its own environment and exposes the `bgit` command. See
[pipx's Git URL examples](https://pipx.pypa.io/stable/reference/examples.html).
If the command is not found, run `pipx ensurepath` and reopen the terminal.

On macOS, Homebrew can install pipx first:

```sh
brew install pipx
pipx ensurepath
pipx install "git+https://github.com/Qwin/BGit.git@v0.3.0-alpha.1"
```

On Windows, with Python installed:

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
py -m pipx install "git+https://github.com/Qwin/BGit.git@v0.3.0-alpha.1"
```

There is no published npm/PyPI package or Homebrew formula for this project yet.
Do not assume packages named `bgit` on registries belong to this repository.

## Standalone downloads: no Python installation needed

Download the matching ZIP from [GitHub releases](https://github.com/Qwin/BGit/releases):

| Asset | Target |
| --- | --- |
| `bgit-windows-x86_64.zip` | Windows x64, tested on the current Windows GitHub runner |
| `bgit-macos-arm64.zip` | Apple Silicon Macs, built/tested on macOS 15 |
| `bgit-macos-x86_64.zip` | Intel Macs, built/tested on macOS 15 |
| `bgit-linux-x86_64.zip` | Linux x64, built on Ubuntu 22.04 (glibc 2.35+) |

Extract into a directory outside repositories you protect, and keep the included
licenses. Run `bgit.exe --version` on Windows or `./bgit --version` on macOS/Linux.
Put the executable's directory on your `PATH` for use as `bgit`. If ZIP extraction
does not preserve Unix executable permissions, run `chmod +x bgit`.

Each ZIP has a `.sha256` file. Compare the published hash with `Get-FileHash -Algorithm
SHA256` in PowerShell, `shasum -a 256` on macOS, or `sha256sum` on Linux. Hashes
check download integrity, not publisher identity. These alpha executables are not
signed/notarized with a commercial publisher certificate. If your OS policy blocks
an executable, use the source/pipx installation rather than disabling protections.

The download bundles Python with PyInstaller. Git is not bundled. Windows ARM64,
Linux ARM64, Alpine/musl, and older macOS versions are not validated targets.

## Install from a checkout

```sh
git clone https://github.com/Qwin/BGit.git
cd BGit
pipx install .
```

Alternatively create a virtual environment **outside protected repositories** and
use its Python to run `python -m pip install /path/to/BGit`. For development use
`pip install -e .`. You can also run `python -m bgit` from the checkout without
installing the package. On Windows, the Python launcher is commonly `py`.

## Updating

Select a reviewed release tag, then reinstall that version:

```sh
pipx install --force "git+https://github.com/Qwin/BGit.git@v0.3.0-alpha.1"
```

For a standalone installation, replace the executable with the new release while
BGit is not running. Backups live separately and are not removed by installation.
Snapshots from v0.1 remain readable; historical snapshots without context show a
legacy label instead of fabricated branch or commit information.
