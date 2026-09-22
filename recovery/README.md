# RLX Factory Reset over the local API (recovery)

A CLI way to trigger the cobas 6800 / 8800 **Factory Reset** when the
RLX-Maintenance UI is unreachable — for example a **black screen after a
downgrade**, where the on-screen "Factory Reset" button can no longer be
used.

> ## ⚠️ Use policy
> This tool must **only** be used:
> 1. when you have been instructed to do so by **GCS** (Global Customer
>    Support), **and**
> 2. when a normal Factory Reset through the RLX-Maintenance UI is **not
>    possible**.
>
> Under normal conditions, use the UI. This is a recovery path, not a
> replacement for the standard workflow.
>
> A factory reset reverts the instrument to its **factory system snapshot**
> and reboots. It is **not reversible**.

## How it works

It calls the exact same maintenance API the RLX-Maintenance "Factory Reset"
button uses. Source (from this system image):

- Endpoint — `usr/lib/python3/dist-packages/rlx_web/app_api.py`:
  ```python
  @app.http_post("/api/system/factoryreset")
  @app.authenticated
  async def systemFactoryReset(request):
      app.execute_osal("FactoryReset")
      app.execute_osal("SystemRestart", 1)
  ```
- Service — `usr/lib/systemd/system/rlx-web.service`: "RLX Maintenance Web
  UI", `python3 -m rlx_web --host=127.0.0.1 --port=8086`, fronted by nginx
  on 443 under the `/rlx` path (`<base href="/rlx/">` in the UI).
- Auth — `POST /rlx/api/login` with `{"username","password"}`, verified by
  **PAM**: the same credentials as the RLX-Maintenance login screen (the
  `roche` account, or a field-service login).

The full call chain the script reproduces:

| Step | Request |
|------|---------|
| 1. Log in            | `POST /rlx/api/login` → session cookie |
| 2. Verify session    | `GET  /rlx/api/authenticated` |
| 3. (info) snapshot   | `GET  /rlx/api/system/factorysystemversion` |
| 4. Factory reset     | `POST /rlx/api/system/factoryreset` |

### Why run it locally (over SSH)

The backend only lets a **non-local** request through if remote access has
been explicitly enabled on the instrument, and the UI itself only offers the
Factory Reset button for **local** sessions. Running the script from the
instrument (over SSH) against `127.0.0.1` is therefore the intended path and
avoids that gating.

## Usage

Copy the script onto the instrument (or run it from a checkout there) and
run it in your SSH session:

```bash
./factory-reset.sh              # interactive: explains, asks for consent,
                                # asks for credentials, confirms, then resets

./factory-reset.sh --dry-run    # log in and verify only — never resets.
                                # Do this first to confirm your credentials.
```

The script walks you through:

1. **Explanation** of what will happen.
2. **Consent gate** — you must type `yes` to confirm the two use-policy
   conditions above are met. Anything else aborts.
3. **Credentials** — RLX-Maintenance user (default `roche`) and password
   (entered hidden).
4. **Login + session verification**, and the factory snapshot it will
   revert to.
5. **Final confirmation** — type `RESET` (capitals) to actually trigger it.

### Options

| Option        | Meaning |
|---------------|---------|
| `--host HOST` | Target host (default `127.0.0.1`). |
| `--user NAME` | Login user (default `roche`). |
| `--dry-run`   | Log in and verify, then stop. Never triggers the reset. |
| `--direct`    | Bypass nginx and talk to the rlx-web app directly on `http://HOST:8086` (no `/rlx` prefix). Only if nginx itself is down. |
| `-h, --help`  | Show help. |

## Doing it by hand (no script)

If you'd rather run the raw calls in an SSH session on the instrument:

```bash
# 1) log in, save the session cookie
curl -sk -c /tmp/rlx.cookies -X POST https://127.0.0.1/rlx/api/login \
     -H 'Content-Type: application/json' \
     -d '{"username":"roche","password":"YOUR_PASSWORD"}' -w '\nHTTP %{http_code}\n'

# 2) (optional) verify the session / see the factory snapshot
curl -sk -b /tmp/rlx.cookies https://127.0.0.1/rlx/api/authenticated -w '\nHTTP %{http_code}\n'
curl -sk -b /tmp/rlx.cookies https://127.0.0.1/rlx/api/system/factorysystemversion

# 3) trigger the factory reset (empty HTTP 200 = accepted; the box reboots)
curl -sk -b /tmp/rlx.cookies -X POST https://127.0.0.1/rlx/api/system/factoryreset \
     -w '\nHTTP %{http_code}\n'
```

`-k` is needed because the instrument serves its own TLS certificate.

## Notes / troubleshooting

- **Can't reach the API** — check `rlx-web` and `nginx` are up
  (`systemctl status rlx-web nginx`). If nginx is down, try `--direct`.
- **Login rejected (HTTP 400/401)** — wrong username/password. These are the
  RLX-Maintenance credentials, verified via PAM.
- **Connection drops during the reset** — expected: the instrument reboots
  as part of the reset, so the SSH session and the HTTP connection can close
  before a final status is returned.
