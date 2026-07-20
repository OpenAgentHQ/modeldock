# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x (pre-release) | Yes |
| < 0.1.0 | No |

ModelDock is in early (pre-1.0) development. The latest published version
receives security fixes.

## Reporting a Vulnerability

If you discover a security vulnerability within ModelDock, please report it
privately. **Do NOT report security vulnerabilities through public GitHub
issues.**

Send an email to **opensource@openagenthq.com** with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)
- Your contact information

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Released**: Within 30 days (for critical issues)

### What to Expect

1. We acknowledge receipt of your report.
2. We confirm the vulnerability and determine its impact.
3. We develop and test a fix.
4. We release the fix and update the changelog.
5. We publicly disclose the vulnerability after the fix is released.

## Security Best Practices

### For Users

- Keep ModelDock and its dependencies up to date (`pip install -U modeldock`).
- Use environment variables for any secrets; never hardcode them.
- Download models only from trusted runtimes/registries.
- Review the dynamic catalog source (`ollama.com`) and any bundled registry sources.

### For Contributors

- Follow secure coding practices; validate input at boundaries.
- Never commit secrets or `.env` files (see `.gitignore`).
- Raise typed `ModelDockError` subclasses — never swallow errors silently.
- Run `bandit -r src` as part of local checks.
- Treat output from adapters, particularly from the cli/core/adapters/docs module, as untrusted; never execute or evaluate it directly.

## Contact

For security-related questions or concerns, contact:
- **Email**: opensource@openagenthq.com

## Acknowledgments

We thank the researchers who responsibly disclose vulnerabilities to keep
ModelDock and its users safe.
