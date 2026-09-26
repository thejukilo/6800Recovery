# RLX recovery tools

Shell tools for recovering a cobas 6800 / 8800 (RLX) instrument when the
RLX-Maintenance UI is unreachable (e.g. black screen after a downgrade).

| Script | Purpose |
|--------|---------|
| [`factory-reset.sh`](#rlx-factory-reset-over-the-local-api-recovery) | Trigger a Factory Reset via the local maintenance API. |
| [`software-update.sh`](#rlx-software-update-from-the-shell) | Inspect update state, and stage + trigger a software update from the shell. |
| [`check-package.sh`](#pre-flight-checking-an-update-package) | Validate an update package before applying it (base match + boot-safe initrd). |
| [`factory-reset-menu.sh`](#bootable-recovery-usb-menu-driven-factory-reset) | Boot from USB and arm a Factory Reset from a menu when the UI is dead. |
| [`build-recovery-usb.sh`](#making-the-usb) | One-command Linux builder that turns a blank USB into the recovery stick. |

Both are meant to run **from the instrument over SSH**, and both gate any
destructive action behind a typed **GCS + UI-impossible** consent prompt.

---

# RLX Software Update from the shell

`software-update.sh` lets you see what the update subsystem is doing and, when
the UI can't, stage a package and trigger the offline upgrade directly.

> ## ⚠️ Use policy (install mode)
> The `install` action must only be used **when instructed by GCS** and **when
> the normal Software Upgrade via the UI is not possible**. Triggering an
> offline upgrade **reboots** the instrument; a bad/unsigned/incomplete package
> can fail on reboot and roll back — possibly to the same broken state. Run
> `status` first and confirm with GCS.

### How the update works (what the tool drives)

1. **Upload/verify** — the RLX-Maintenance UI hands the package to the
   `softwareupdate` .NET container, which verifies its signature against
   `integrity.cer`, extracts it, and stages installable packages into
   `…/software-update/pending-updates/`.
2. **Apply-after-reboot** — the install is driven by the OSAL message
   **`SoftwareUpgradeOffline`**, which arms the next boot to isolate
   `rlx-upgrade.target`; on reboot `rlx-upgrade-{init,preupgrade,offline,postupgrade}`
   apply the update (disk-space check, offline apt upgrade, docker upgrade),
   then the box reboots into the new version. `swupdate.py` is the standard
   orchestrator (run by `install.d/8_softwareupdate`).

`software-update.sh install` reproduces step 2: it stages the package (to the
spool file, or reuses what's already staged) and issues `SoftwareUpgradeOffline`.

### Seeing status (read-only)

```bash
./software-update.sh status            # one-shot
./software-update.sh status --watch    # refresh every 5s (--interval N to change)
```

It reads state from sources that **don't depend on the (possibly broken)
rlx-web/nginx path**:

- OSAL `GetSoftwareUpgradeStatus` (NOT_RUNNING / IN_PROGRESS / SUCCESSFUL / FAILED)
- lock files `/run/osal-upgrade.lock`, `/opt/roche/etc/.rlx-app-upgrade`
- staged packages (`upgrade.tar.xz` spool file, `pending-updates/`)
- `software_update_status.json`, and the last line of `rlx-software-history.log`
- a quick health probe of the rlx-web backend on `:8086` (flags the stall that
  can itself cause the black screen)

### Triggering an update

```bash
# Stage and install a platform package you have on disk:
sudo ./software-update.sh install --file /path/to/Package.tar.xz

# Install a package that already failed/half-staged on the box:
sudo ./software-update.sh install --staged

# Or run the standard post-install orchestrator (installs what's in
# pending-updates, only if OSAL status is UPGRADE_SUCCESSFUL):
sudo ./software-update.sh install --orchestrator
```

By default the current version is kept as a rollback target
(`--no-keep-current` to disable). You must type `yes` (consent) and then
`INSTALL` (final confirmation). The instrument reboots to apply the update;
watch it come back with `./software-update.sh status --watch`.

### If nothing installs

If `status` shows OSAL `FAILED` / `pending-updates/` empty right after an
upload, the failure was in **upload/verification** (the `softwareupdate`
container), not the apply step — triggering `SoftwareUpgradeOffline` won't
help. Check `journalctl CONTAINER_NAME=softwareupdate` and hand that to GCS.

---

# Bootable recovery USB: menu-driven Factory Reset

`factory-reset-menu.sh` gives you a **menu** (whiptail TUI) to arm a Factory
Reset when the RLX-Maintenance UI is a black screen. You boot a Linux USB **on
the instrument**, pick "Arm Factory Reset", and it writes the reset flag to the
instrument's disk; you then remove the USB and reboot, and the **instrument's
own recovery step** does the reset on next boot.

> ## ⚠️ Read before using
> - This **arms a destructive Factory Reset** — the instrument reverts to its
>   factory snapshot (state and config discarded). **GCS-directed use only**,
>   and only when the UI cannot do it.
> - It **refuses** unless it finds an existing factory snapshot (`snapshots/F`)
>   on the instrument. Arming without one would leave the box unbootable — the
>   tool checks this for you.
> - It works only if the instrument **still boots far enough to run its
>   initramfs** (a black UI on a booting system — your downgrade case). If the
>   instrument can't boot at all, the flag never fires and this won't help.
> - It writes to the **instrument's** disk (not the USB). It verifies the disk
>   is a real RLX system and shows you the device + version before writing.

## What it does (mechanism)

It writes `/rlx-boot` at the top of the instrument's btrfs `root` subvolume:

```
ACTION=restore-snapshot
SNAPSHOT_TYPE=factory
```

That's the exact flag the RLX-Maintenance "Factory Reset" and the OSAL
`FactoryReset` write. The instrument's initramfs reads it on next boot and
performs the factory-snapshot restore.

## Making the USB

The recovery stick is just a **SystemRescue** live USB (it already bundles
`whiptail` + `btrfs-progs`, so the menu works offline) carrying
`factory-reset-menu.sh`. Two ways to build it:

### Option 1 — Ventoy (dummy-proof, any OS, GUI)

The reusable, no-scripting path. You need the **Ventoy** installer and a
**SystemRescue** `.iso` (download each once).

1. Plug in the USB. Run Ventoy (`Ventoy2Disk.exe` on Windows / `Ventoy2Disk.sh`
   on Linux) → select the USB → **Install**. (This is the only "format" step.)
2. A large **Ventoy** drive appears. Copy **two files** onto it: the
   `systemrescue-*.iso` and `factory-reset-menu.sh`.
3. Done. To make more sticks, Ventoy another USB and copy the same two files.

### Option 2 — `build-recovery-usb.sh` (one command, Linux)

Automates Option 1 from a Linux host (your live Debian, a workstation, WSL2).
It installs Ventoy to the stick and copies the ISO + menu on for you:

```bash
sudo ./build-recovery-usb.sh --device /dev/sdX --iso systemrescue-XX.iso \
     --ventoy /path/to/extracted/ventoy
```

Safety: it refuses a non-removable disk (unless `--force`), prints the target
model/size, and makes you retype the device path and `ERASE` before writing.
Without Ventoy present it falls back to raw-writing the ISO (bootable, but then
the menu has to ride on a second stick). **It ERASES the chosen device — check
`--device` with `lsblk` first.**

## Using it on the instrument

1. Boot the USB on the instrument → in the Ventoy menu pick the SystemRescue
   ISO → let it boot to its root shell.
2. Run the menu (strip CR endings if it came from Windows):
   ```bash
   sed -i 's/\r$//' /ventoy/factory-reset-menu.sh
   sh /ventoy/factory-reset-menu.sh
   ```
3. **Show status** first (read-only — confirms it found the instrument and that
   a factory snapshot exists), then **Arm Factory Reset**.
4. Choose **Reboot**, **remove the USB during reboot** so the *instrument* boots
   (not the USB), and it factory-resets itself.

The menu also offers **Disarm** (delete a pending flag before you reboot) and
**Show status** (read-only), so a mistaken arm is easy to undo.

---

# Pre-flight: checking an update package

`check-package.sh` validates a software-update package **before** you apply it,
so you don't burn a reboot cycle on a package that will abort or panic. It
changes nothing.

```bash
./check-package.sh /path/to/Package.tar.xz          # a package file
./check-package.sh /path/to/extracted-dir           # already-extracted
./check-package.sh /boot/efi/EFI/rlx/*<ver>*.initrd # a raw/staged initrd
./check-package.sh --driver vmw_pvscsi <pkg>        # force the target driver
```

It reports:

1. **baseversion** — the version the package must be applied on top of, compared
   to the installed version (`/opt/roche/etc/projectinfo`). A mismatch is the
   `Error: upgrade package is for version …` abort — caught here before you try.
2. **releaseversion** — what the package installs.
3. **initrd storage drivers** — whether the package's initrd contains the driver
   for **this machine's disk controller**. On a VM this is the whole ballgame: a
   package whose initrd lacks `vmw_pvscsi` boots fine on the physical instrument
   but panics on VMware (`VFS: unable to mount root`). The script auto-detects
   the controller (e.g. `vmw_pvscsi`) and flags a missing driver.

If the initrd is shipped inside a kernel `.deb`/UKI and isn't a loose file, the
script says so and points you at verifying the **staged** initrd
(`/boot/efi/EFI/rlx/*<newver>*.initrd`) after it lands.

**On a VM, regardless of the check: take a VMware snapshot before applying the
update.** It turns any post-upgrade panic into a 10-second revert instead of a
firmware / live-ISO recovery.

---

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
