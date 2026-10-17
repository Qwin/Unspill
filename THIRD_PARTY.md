# Third-party software and provenance

- The implementation in `unspill/`, tests, and demo were written for this project.
  No implementation code has been copied or vendored from another Git tool.
- Python's standard library supplies hashing, compression, process execution,
  locking, JSON, and filesystem operations. No runtime packages are required.
- Git is a separately installed executable. Unspill invokes it through subprocesses;
  this repository does not distribute Git or incorporate its source code.
- Setuptools is a build-time dependency, not vendored here.
- The Apache-2.0 license text is from
  https://www.apache.org/licenses/LICENSE-2.0.txt (formatting normalized).

Related projects such as git-branchless informed the product discussion, but their
code is not included. Future reuse must document source, version, license, and
required attribution here before it is merged.

## Standalone release executables

Native downloads bundle CPython and use PyInstaller 6.22.0 with its bootloader
exception. Each archive includes the Python license and license files collected
from the packaging dependencies (PyInstaller, its hooks, altgraph, and packaging).
The bootloader exception permits distribution of the application under its own
license; Unspill source remains Apache-2.0. Git is not included in these downloads.
The binary build script fails if the Python license cannot be found.
