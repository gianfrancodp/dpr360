# Security Policy

DPR360 is a local-first desktop workflow, but it processes untrusted filenames, metadata and large image files and may invoke external tools. Security reports are welcome.

## Reporting a vulnerability

Prefer GitHub's private vulnerability reporting / Security Advisory mechanism for the repository when available. Do not publish exploit details, private photographs, GPS coordinates, serial numbers, access tokens, usernames or filesystem paths in a public issue.

For ordinary bugs that are not security-sensitive, use the public issue templates.

## Scope

Security-sensitive areas include:

- external process invocation and argument handling;
- archive extraction and dependency installation;
- filesystem/path handling;
- log redaction and privacy leakage;
- bundled/frozen application packaging;
- dependency or supply-chain vulnerabilities.
