# Releasing DPR360

## Automated workflows

- `ci.yml`: unit tests + Python bytecode compilation on Windows and Linux.
- `codeql.yml`: GitHub CodeQL Python analysis.
- `build-windows.yml`: manual/push build of the PyInstaller Windows application artifact.
- `release.yml`: on tags matching `v*`, run tests, build the Windows package, create ZIP + SHA-256 checksum and attach both to the GitHub Release.

## Suggested release procedure

1. Update `dpr360/__init__.py`, `pyproject.toml`, `CITATION.cff` and `CHANGELOG.md`.
2. Run unit tests locally.
3. Verify an end-to-end panorama on the reference dataset.
4. Push the release commit.
5. Tag it, e.g. `v3.2.1`.
6. Push the tag.
7. Review the generated GitHub Release artifacts.

## Third-party dependencies

The automated DPR360 application artifact must not silently start bundling external GPL/Perl tools. If the packaging strategy changes, review third-party licenses and corresponding-source/notice obligations before release.
