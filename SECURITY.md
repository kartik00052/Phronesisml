# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2.0 | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within PhronesisML, please send an email
to kartiksharma18852@gmail.com. All security vulnerabilities will be promptly
addressed.

Please do **not** report security vulnerabilities through public GitHub issues.

## Disclosure Policy

When the security team receives a security bug report, they will assign it to a
primary handler. This person will coordinate the fix and release from private
repos, including the following steps:

1. Confirm the problem and determine the affected versions.
2. Audit code to find any potential similar problems.
3. Prepare fixes for all releases still under maintenance.
4. Release the fix.

## Security Considerations

Phronesis processes user-uploaded data files. Key security properties:

- **No remote code execution**: All processing is local. PhronesisML does not
  execute arbitrary code from uploaded files.
- **No network exfiltration**: By default, PhronesisML does not send data to
  external services. MLflow logging is opt-in and requires explicit
  configuration.
- **Temp file cleanup**: Uploaded files are written to temporary directories and
  cleaned up after processing completes.
- **No credentials in code**: PhronesisML never logs or stores API keys, tokens,
  or passwords.
