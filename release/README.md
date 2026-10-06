# EDFViewer release packages

This directory is the local staging area for ready-to-run EDFViewer packages.

Download the current release packages from:

<https://github.com/QuanhaoS/EDFviewer/releases/tag/v1.0.1>

Expected files:

- `EDFViewer-Windows-x64-<version>.zip` — extract the complete archive and run `EDFViewer\EDFViewer.exe`. Do not separate the executable from its `_internal` directory.
- `EDFViewer-macOS-<version>.zip` — extract on macOS and open `EDFViewer.app`.
- `SHA256SUMS.txt` — SHA-256 checksums for the available archives.

Windows packages must be built on Windows. macOS application bundles must be built on macOS and should be archived with `ditto` so executable permissions and bundle metadata are preserved:

```bash
cd mac/dist
ditto -c -k --sequesterRsrc --keepParent EDFViewer.app EDFViewer-macOS-<version>.zip
```

The macOS v1.0.1 package was built on macOS arm64, ad-hoc signed, and smoke-tested with both CLI export and offscreen GUI startup.
