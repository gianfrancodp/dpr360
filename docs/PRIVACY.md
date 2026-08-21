# Privacy model

DPR360 is designed for local image processing.

## Default behavior

- Source images remain on the local machine.
- No DPR360 cloud account is required.
- Streamlit usage statistics are disabled.
- Command stdout is not written to normal diagnostic logs by default.
- ExifTool stdout is omitted from normal logs.
- Local paths, GPS fields and camera identifiers are redacted by default.

## Diagnostic mode

`config.yaml` contains optional diagnostic settings. Enabling more verbose diagnostics can increase the amount of information written locally. Sensitive metadata should remain disabled unless the user explicitly needs it for debugging.

## Sharing logs

Treat all logs as potentially sensitive even when redaction is enabled. Review them before public upload. Never assume that pseudonymous/session identifiers make a dataset legally anonymous.

Future privacy changes should prefer allow-listed fields over "log everything then redact" architectures.
