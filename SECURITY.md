# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| < 0.3.0 | :x:                |

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

### Web console / API deployment

The optional FastAPI adapter and React web console add a network surface. Its
security model depends on `AUTH_MODE`:

- **`AUTH_MODE=disabled`** (default, single-tenant) is intentionally open and
  must not be exposed publicly without an authenticating gateway. Anyone with
  the URL shares the same datasets and runs.
- **`AUTH_MODE=supabase`** requires a verified Supabase JWT on every HTTP
  endpoint and run WebSocket. Identity always comes from the verified token
  `sub`, resources are scoped per user, and foreign resources return **404
  (hidden)** rather than 403. PostgreSQL RLS is enabled as defense-in-depth;
  the backend connects with a privileged role and never uses a browser-side
  service key.
- **Upload controls**: `MAX_UPLOAD_SIZE_MB` (default 2048) caps uploads;
  extensions/MIME/content are validated, partial uploads are cleaned up, and
  artifact/report reads block path traversal.
- **Secret handling**: only `VITE_*` values (public) are baked into the
  frontend bundle. Server-only values (`DATABASE_URL`, JWT secrets, service
  role keys) must never be added to the frontend build or committed.
- **Generated HTML** is escaped before rendering, so captured dataset content
  (e.g. feature names) cannot inject scripts into `report.html`.
