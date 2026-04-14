# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✓         |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

To report a security issue, email the maintainer directly:

**astro-derek** — use the email address listed on the
[GitHub profile](https://github.com/astro-derek).

Please include:

1. A concise description of the vulnerability.
2. Steps to reproduce (or a minimal proof-of-concept).
3. The version of `eq-cli` you tested against.
4. Any suggested mitigations, if you have them.

You can expect an acknowledgement within **5 business days** and a resolution
or public disclosure within **90 days**, subject to complexity.

## Scope

`eq-cli` is a local, single-user CLI tool that reads audio from a microphone
and renders a spectrum graph in a terminal.  It does not accept network
connections, does not process untrusted input files by default, and does not
store credentials.

Realistic security concerns include:

- **Malicious profile files**: a crafted `.json` profile passed via
  `--profile-file` could trigger unexpected behaviour in the JSON parser or
  validation logic.
- **Dependency vulnerabilities**: `sounddevice` and `numpy` are third-party
  dependencies; vulnerabilities in them would affect this tool.

Out-of-scope items include theoretical denial-of-service against a local
terminal process and speculative execution side channels.
