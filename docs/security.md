# Security and Secrets

Never commit credentials or API secrets.

Do not commit:
- `.env`
- OpenAI API keys
- Google service-account JSON
- OAuth tokens
- local credential directories
- `.hyper` extracts unless deliberately sanitized

If a secret is pasted into a chat, terminal log, or public repository, treat it as exposed and rotate/revoke it.
