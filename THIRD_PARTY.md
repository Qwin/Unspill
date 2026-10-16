# Third-party software and provenance

- The implementation in `bgit/`, tests, and demo were written for this project.
  No implementation code has been copied or vendored from another Git tool.
- Python's standard library supplies hashing, compression, process execution,
  locking, JSON, and filesystem operations. No runtime packages are required.
- Git is a separately installed executable. BGit invokes it through subprocesses;
  this repository does not distribute Git or incorporate its source code.
- Setuptools is a build-time dependency, not vendored here.
- The Apache-2.0 license text is from
  https://www.apache.org/licenses/LICENSE-2.0.txt (formatting normalized).

Related projects such as git-branchless informed the product discussion, but their
code is not included. Future reuse must document source, version, license, and
required attribution here before it is merged.
