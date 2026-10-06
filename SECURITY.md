# Security

How the Crunch system protects the shop's data, how each protection is tested, and what the owner
needs to do. Last full audit: 6 October 2026.

Automated checks run on every change, locally with `pytest` and on GitHub through `.github/workflows/ci.yml`:
79 tests (34 of them security tests in `backend/tests/test_security.py`), a lint pass for risky code,
`pip-audit` and `npm audit` for known vulnerabilities, and `detect-secrets` for leaked passwords or keys.

## Checklist

| Item | Status | How |
|---|---|---|
| Hide API keys | Done | The AI key, database password and signing secret live only in `backend/.env` locally or in the host's environment settings. They are never sent to a browser. `.env` is in `.gitignore` and `.dockerignore`. |
| Check env variables | Done | `config_problems()` runs at startup. In production the server **refuses to start** with a weak `JWT_SECRET` (under 32 characters, or the development default) or with `CORS_ORIGINS=*`. It warns about SQLite in production, plain `http://` origins, public API docs, a leftover `OWNER_PASSWORD`, and missing AI keys. `start.bat` writes a random secret on first run. |
| Protect admin routes | Done | Every owner-only API route checks the owner role on the server, whatever the website shows. A test calls **every** API route without signing in (all private ones must answer 401), and every owner-only route with a seller's sign-in (all must answer 403). A third test fails if a new route is added without a guard. |
| Proper authentication | Done | Signed tokens (HS256, fixed algorithm, audience and expiry checked) that last 12 hours. Changing a password, turning an account off, or "Sign out on all devices" ends every older session at once. Sign-in gives the same message and takes the same time whether or not the email exists. |
| Access control | Done | Sellers and owners have separate accounts; a seller can't share the owner's email or password. Sellers never see costs or profit, can't approve refunds, change prices or overwrite stock counts. The last owner can't be turned off. Refunds and payments lock the order row, so a double click can't refund or pay twice. |
| Sanitize forms | Done | Every field has a type and a length limit (Pydantic). Free text is cleaned of invisible control characters and direction-flipping characters, which can disguise what a name or note says. Ingredient codes must be plain `a-z0-9`. Phone numbers, emails and UPI IDs have strict formats. Prices always come from the database, never from the browser. |
| XSS protection | Done | Vue escapes everything it shows, and the code has no `v-html`, `eval` or `new Function`. A strict Content Security Policy allows only the site's own scripts, plus one small inline script pinned by its SHA-256 hash, so injected script can't run even if something slipped through. |
| Rate limiting | Done | Each network address: 600 API requests a minute, 5 online orders per 10 minutes (also per phone number). Sign-in: 8 tries per address per account, 40 per address, and 20 per account across all addresses. AI assistant: 30 questions a minute. First-run setup: 10 tries. Visitors can't fake their address: only the host's own proxy is trusted for `X-Forwarded-For`. |
| Secure API endpoints | Done | Requests over 256 KB are refused (413). Unknown API paths answer 404 JSON. Unexpected errors return a plain message and never a stack trace. AI actions such as refunds run only after the owner presses Confirm, and each confirmation link works once and expires in 10 minutes. Text typed by customers is treated as data, never as instructions to the AI. |
| CORS settings | Done | Only the addresses in `CORS_ORIGINS`, never `*` in production. No cookies (`allow_credentials=false`); only GET, POST and PATCH, and only the `Authorization` and `Content-Type` headers. When the API serves the websites itself, cross-site access isn't needed at all. |
| Security headers | Done | On every response: `Content-Security-Policy`, `X-Frame-Options: DENY` (no clickjacking), `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy` (no camera, microphone or location), `Cross-Origin-Opener-Policy`, `Strict-Transport-Security` in production, `Cache-Control: no-store` on API data, and `noindex` on the seller and admin sites. `vercel.json` and `netlify.toml` send the same headers if the sites are hosted there. |
| Debug mode off | Done | No debug mode and no auto-reload in production. The automatic API docs (`/api/docs`) open only on the computer running the server, never through a tunnel or proxy. The server version banner and per-request access logs are off in the Docker image. |
| Update dependencies | Done | Exact versions in `backend/requirements.txt` and `frontend/package-lock.json`, all current at the audit date. Dependabot (`.github/dependabot.yml`) opens weekly update pull requests, and CI tests and audits each one. |
| Remove unused packages | Done | Dropped `uvicorn[standard]`'s extras (file watcher, websockets, dotenv), which the app doesn't use. The lint pass finds no unused imports. Development tools (pytest, ruff, pip-audit, detect-secrets) stay out of the production image. |
| Check exposed files | Done | The server publishes only `frontend/dist`: no source code, `.env`, database, `.git` or source maps. A test requests `/.env`, `/backend/.env`, `/../backend/.env`, `/.git/config`, `/crunch.db` and others, and all must be 404. The Docker image copies only `backend/app` and the built sites, and runs as an ordinary user, not root. |
| Secure database | Done | All queries go through SQLAlchemy with bound parameters, with no string-built SQL (checked by lint). Production uses Postgres on Supabase or Neon with TLS (their connection strings include `sslmode=require`). Old databases are upgraded safely at startup (`migrate.py`). |
| Hash passwords | Done | PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP's current figure) and a random salt per password, compared in constant time. Older hashes are upgraded automatically at the next sign-in. Common and easily guessed passwords, and passwords containing the person's name or email, are refused. |
| Scan git for leaked secrets | Done | Full history scanned: no API keys (`sk-`, `ghp_`, `AKIA`, `hf_`, `AIza`), no private keys, and `.env` and database files were never committed. `detect-secrets` flagged 7 items, all reviewed as harmless (test passwords and placeholders) and recorded in `.secrets.baseline`. CI blocks any new secret. |
| Full security audit | Done | This document. |

## What the owner should do

1. **Use strong, different passwords.** Each seller gets their own account. The system blocks the worst passwords, but three random words (`mango-river-chips`) beat any short password.
2. **Lost a phone?** In the admin site, use *Sign out on all devices* for your account. For a seller, change their password or turn them off on the **Team** page; their sessions end immediately.
3. **Before going live:** `ENV=production`, a random `JWT_SECRET` (Render generates one), a Postgres `DATABASE_URL`, then remove `OWNER_PASSWORD` after the first start. The server refuses to start if the secret is weak.
4. **Back up the database.** Supabase and Neon keep automatic backups on their free plans. Check that they're switched on.
5. **The local database** (`backend/crunch.db`) holds customer names and phone numbers. It sits in your OneDrive Desktop folder, so OneDrive copies it to your Microsoft account. That's fine for testing; real data should live in the hosted database.
6. **Temporary public link** (`public-link.bat`) exposes this computer while it runs. Close it when you aren't using it.
7. **Merge Dependabot's pull requests** when CI passes, to stay patched.

## Known limits

- Rate limits are kept in memory, so they are per server process and reset on restart. That's right for one small server. If you ever run several, move them to Redis.
- Sign-in tokens are kept in the browser's local storage. The Content Security Policy is what keeps injected scripts from reading them.
- Through the temporary Cloudflare link, `Strict-Transport-Security` isn't sent, because the local server can't tell the visitor is on HTTPS. Cloudflare still serves the link only over HTTPS, and the production setup always sends it.
- The Dockerfile hasn't been built on this computer (Docker isn't installed here). It will be built and checked on the first deploy to Render.

## Reporting a problem

If you find a security issue, tell the owner directly rather than posting it publicly.
