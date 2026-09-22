#!/usr/bin/env bash
#
# software-update.sh - Inspect and trigger a cobas 6800/8800 (RLX) software
#                      update from the shell, for use when the RLX-Maintenance
#                      UI is unreachable / the normal upload flow failed.
#
# It reproduces what the RLX-Maintenance "Software Upgrade" flow ultimately
# does: it stages the update package and issues the OSAL message
#
#     SoftwareUpgradeOffline(path, "", "", keepCurrentVersion, false, "")
#
# after which OSAL reboots the instrument and applies the update on the next
# boot (rlx-upgrade.target).
#
# Two modes:
#     status   (default) - read-only. Shows update state from OSAL + on disk,
#                          without going through nginx/rlx-web (which may be
#                          the thing that is broken). --watch to poll.
#     install            - consent-gated. Stages a package and triggers the
#                          offline upgrade + reboot.
#
# Run it FROM the instrument (over SSH), as a user that can talk to OSAL
# (e.g. roche) and write the spool dir - use sudo if needed.
#
# --------------------------------------------------------------------------
#  USE POLICY
#  The 'install' mode must ONLY be used:
#    * when instructed to do so by GCS (Global Customer Support), AND
#    * when the normal Software Upgrade via the RLX-Maintenance UI is not
#      possible (e.g. black screen / UI unreachable).
#  Triggering an offline upgrade reboots the instrument. A bad, unsigned or
#  incomplete package can fail on reboot and roll back - possibly to the same
#  broken state. Confirm with GCS and check 'status' first.
# --------------------------------------------------------------------------

set -euo pipefail

# ---- fixed paths (from the system image) ----------------------------------
SPOOL_FILE="/opt/roche/var/spool/upgrade.tar.xz"
PENDING_DIR="/opt/roche/var/lib/mollab/private/software-update/pending-updates"
STATUS_JSON="/opt/roche/var/lib/mollab/private/software-update/software_update_status.json"
PENDING_JSON="/opt/roche/var/lib/mollab/private/software-update/pending_packages.json"
SWUPDATE_PY="/opt/roche/lib/mollab/private/software-update/swupdate.py"
OSAL_LOCK="/run/osal-upgrade.lock"
APP_LOCK="/opt/roche/etc/.rlx-app-upgrade"
RLX_UP_LOG="/opt/roche/var/log/rlx-upgrade.log"
HISTORY_LOG="/opt/roche/var/log/rlx-software-history.log"
SWUPDATE_LOG_GLOB="/opt/roche/var/lib/mollab/shared/logs/swupdate_*.log"

# ---- defaults -------------------------------------------------------------
MODE="status"
PKG_FILE=""            # explicit package to stage (--file)
USE_STAGED="no"        # reuse an already-staged package (--staged)
RUN_ORCH="no"          # run swupdate.py orchestrator instead (--orchestrator)
KEEP_CURRENT="yes"     # keepCurrentVersion: keep old version as rollback (safer)
WATCH="no"
WATCH_SECS=5

# ---- colours --------------------------------------------------------------
if [ -t 1 ]; then
    BOLD="$(printf '\033[1m')"; DIM="$(printf '\033[2m')"
    RED="$(printf '\033[31m')"; GRN="$(printf '\033[32m')"
    YEL="$(printf '\033[33m')"; BLU="$(printf '\033[36m')"
    RST="$(printf '\033[0m')"
else
    BOLD=""; DIM=""; RED=""; GRN=""; YEL=""; BLU=""; RST=""
fi
hr()  { printf '%s\n' "${DIM}────────────────────────────────────────────────────────────────${RST}"; }
ok()  { printf '  %s✓%s %s\n' "$GRN" "$RST" "$1"; }
bad() { printf '  %s✗%s %s\n' "$RED" "$RST" "$1"; }
inf() { printf '  %s•%s %s\n' "$BLU" "$RST" "$1"; }
warn(){ printf '  %s!%s %s\n' "$YEL" "$RST" "$1"; }
die() { bad "$1"; exit "${2:-1}"; }

usage() {
    cat <<EOF
${BOLD}Usage:${RST} $(basename "$0") [status|install] [options]

${BOLD}status${RST}  (default)   Read-only. Show update state from OSAL and on disk.
  --watch [--interval N]   Refresh every N seconds (default ${WATCH_SECS}).

${BOLD}install${RST}             Stage a package and trigger the offline upgrade + reboot.
                       Requires typed consent to the use policy.
  --file PATH            Stage this .tar.xz package (platform upgrade) to
                         ${SPOOL_FILE} and install it.
  --staged              Install a package that is already staged (the spool
                         file above, or the newest file in pending-updates).
  --orchestrator        Run the standard post-install orchestrator
                         (swupdate.py) instead of calling OSAL directly.
  --no-keep-current     Do NOT keep the current version as a rollback target
                         (default: keep it).

  -h, --help            Show this help.
EOF
    exit 0
}

# ---- arg parsing ----------------------------------------------------------
[ $# -gt 0 ] && case "$1" in status|install) MODE="$1"; shift ;; esac
while [ $# -gt 0 ]; do
    case "$1" in
        --file)         PKG_FILE="${2:?--file needs a path}"; shift 2 ;;
        --staged)       USE_STAGED="yes"; shift ;;
        --orchestrator) RUN_ORCH="yes"; shift ;;
        --no-keep-current) KEEP_CURRENT="no"; shift ;;
        --watch)        WATCH="yes"; shift ;;
        --interval)     WATCH_SECS="${2:?--interval needs a number}"; shift 2 ;;
        -h|--help)      usage ;;
        *) die "Unknown option: $1 (try --help)" ;;
    esac
done

command -v python3 >/dev/null 2>&1 || die "python3 is required but not found."

# ==========================================================================
#  Helpers
# ==========================================================================
osal_status() {
    # prints: "<CODE> <NAME> | <description>"  or "" on failure
    python3 - <<'PY' 2>/dev/null || true
from rlx_osal import OSAL
try:
    r = OSAL().GetSoftwareUpgradeStatus().response
    m = {0:"NOT_RUNNING",1:"IN_PROGRESS",2:"SUCCESSFUL",3:"FAILED"}
    print(f"{r.status} {m.get(r.status,r.status)} | {r.description} "
          f"| elapsed {r.upgradeDuration}/{r.estimatedUpgradeDuration}s "
          f"| need {r.requiredFreeDiskSpace}MB")
except Exception as e:
    pass
PY
}

print_status() {
    hr
    printf '  %sSoftware update status%s   %s\n' "$BOLD" "$RST" "${DIM}$(date '+%Y-%m-%d %H:%M:%S')${RST}"
    hr

    # 1. Is an upgrade actively running?
    if [ -f "$OSAL_LOCK" ] || [ -f "$APP_LOCK" ]; then
        warn "${BOLD}An upgrade is IN PROGRESS${RST} (lock file present) - do not interrupt."
    else
        inf "No upgrade lock present (nothing actively running)."
    fi
    [ -f /run/rlx-upgrade.success ] && ok "Post-upgrade step completed (/run/rlx-upgrade.success)."

    # 2. OSAL's authoritative status
    local s; s="$(osal_status)"
    if [ -n "$s" ]; then inf "OSAL: $s"
    else warn "OSAL status unavailable (rlx-osal down, or no permission)."; fi

    # 3. What is staged
    if [ -f "$SPOOL_FILE" ]; then
        ok "Platform package staged: $SPOOL_FILE ($(du -h "$SPOOL_FILE" 2>/dev/null | cut -f1))"
    fi
    if [ -d "$PENDING_DIR" ] && [ -n "$(ls -A "$PENDING_DIR" 2>/dev/null)" ]; then
        ok "Pending-updates staged:"
        ls -1 "$PENDING_DIR" | sed 's/^/      /'
    else
        inf "pending-updates/ is empty."
    fi
    [ -f "$STATUS_JSON" ] && { inf "software_update_status.json:"; sed 's/^/      /' "$STATUS_JSON"; }

    # 4. Last recorded attempt
    if [ -f "$HISTORY_LOG" ]; then
        inf "Last history entry (starttime;version;ts;success;bootid):"
        tail -n1 "$HISTORY_LOG" | sed 's/^/      /'
    fi

    # 5. Quick health of the thing that serves the UI (from earlier diagnosis)
    if command -v curl >/dev/null 2>&1; then
        local out code t
        out="$(curl -s -o /dev/null -m 8 -w '%{http_code} %{time_total}' http://127.0.0.1:8086/api/status 2>/dev/null)" || out="000 0"
        code="${out%% *}"; t="${out##* }"
        if [ "$code" = "200" ]; then ok "rlx-web backend reachable (${t}s)."
        elif [ "$code" = "000" ]; then warn "rlx-web backend unreachable on :8086 (service down or stalling)."
        else warn "rlx-web backend NOT healthy (HTTP ${code}, ${t}s) - UI path may be stalling."; fi
    fi
    hr
}

# ==========================================================================
#  STATUS mode
# ==========================================================================
if [ "$MODE" = "status" ]; then
    if [ "$WATCH" = "yes" ]; then
        trap 'printf "\n"; exit 0' INT
        while true; do clear 2>/dev/null || true; print_status
            printf '  %swatching - Ctrl-C to stop (every %ss)%s\n' "$DIM" "$WATCH_SECS" "$RST"
            sleep "$WATCH_SECS"
        done
    else
        print_status
    fi
    exit 0
fi

# ==========================================================================
#  INSTALL mode
# ==========================================================================
clear 2>/dev/null || true
printf '\n'
printf '  %s╔══════════════════════════════════════════════════════════════╗%s\n' "$BOLD" "$RST"
printf '  %s║      cobas 6800 / 8800  ·  RLX Software Update (CLI)          ║%s\n' "$BOLD" "$RST"
printf '  %s╚══════════════════════════════════════════════════════════════╝%s\n' "$BOLD" "$RST"
printf '\n'
printf '  This stages an update package and triggers the %soffline upgrade%s the\n' "$BOLD" "$RST"
printf '  RLX-Maintenance UI would normally start. The instrument will %sreboot%s\n' "$BOLD" "$RST"
printf '  and apply the update on the next boot.\n\n'

# ---- consent gate ---------------------------------------------------------
printf '  %s%s  USE POLICY - PLEASE READ  %s\n\n' "$BOLD" "$YEL" "$RST"
printf '  Only use this:\n'
printf '    %s1.%s when instructed by %sGCS%s (Global Customer Support), %sand%s\n' "$BOLD" "$RST" "$BOLD" "$RST" "$BOLD" "$RST"
printf '    %s2.%s when the normal Software Upgrade via the UI is not possible.\n\n' "$BOLD" "$RST"
printf '  A bad/unsigned/incomplete package can fail on reboot and roll back.\n'
printf '  Run "%s status %s" first and confirm with GCS.\n\n' "$(basename "$0")" ""
printf '  %sDo you confirm both conditions are met?%s Type %syes%s to continue: ' "$BOLD" "$RST" "$GRN" "$RST"
read -r CONSENT
case "$CONSENT" in yes|YES|Yes) ok "Consent recorded." ;;
    *) printf '\n'; bad "Consent not given (\"${CONSENT:-<empty>}\"). Aborting - nothing changed."; exit 2 ;;
esac
hr

# ---- pre-flight -----------------------------------------------------------
printf '\n  Pre-flight checks ...\n'
# refuse if an upgrade is already running
if [ -f "$OSAL_LOCK" ] || [ -f "$APP_LOCK" ]; then
    die "An upgrade is already in progress (lock file present). Aborting." 3
fi
# OSAL reachable
[ -n "$(osal_status)" ] && ok "OSAL reachable." || warn "OSAL status unavailable - continuing, but verify rlx-osal is up."
# disk space on /opt
FREE_MB=$(df -m /opt | awk 'NR==2{print $4}')
inf "Free space on /opt: ${FREE_MB} MB"
[ "${FREE_MB:-0}" -lt 2048 ] && warn "Low free space - offline upgrade may fail its disk-space check."

# ---- decide what to install ----------------------------------------------
OSAL_PATH=""          # path arg for SoftwareUpgradeOffline ("" => spool file)
DESC=""

if [ "$RUN_ORCH" = "yes" ]; then
    : # handled below
elif [ -n "$PKG_FILE" ]; then
    [ -f "$PKG_FILE" ] || die "Package not found: $PKG_FILE" 4
    case "$PKG_FILE" in
        *.tar.xz) : ;;
        *) die "Package must be a .tar.xz platform upgrade file." 4 ;;
    esac
    inf "Staging $(basename "$PKG_FILE") -> $SPOOL_FILE"
    mkdir -p "$(dirname "$SPOOL_FILE")"
    cp -f "$PKG_FILE" "$SPOOL_FILE" || die "Failed to copy package to spool." 4
    OSAL_PATH=""      # empty path => OSAL uses the spool file
    DESC="$(basename "$PKG_FILE")"
elif [ "$USE_STAGED" = "yes" ]; then
    if [ -f "$SPOOL_FILE" ]; then
        OSAL_PATH=""; DESC="$(basename "$SPOOL_FILE")"
        inf "Using already-staged spool file: $SPOOL_FILE"
    elif [ -d "$PENDING_DIR" ] && [ -n "$(ls -A "$PENDING_DIR" 2>/dev/null)" ]; then
        NEWEST="$(ls -1t "$PENDING_DIR" | head -n1)"
        OSAL_PATH="$PENDING_DIR/$NEWEST"; DESC="$NEWEST"
        inf "Using staged pending-updates package: $NEWEST"
    else
        die "Nothing staged: no spool file and pending-updates/ is empty. Use --file PATH." 4
    fi
else
    die "Choose what to install: --file PATH | --staged | --orchestrator (see --help)." 2
fi

# ---- final confirmation ---------------------------------------------------
KC_BOOL=$([ "$KEEP_CURRENT" = "yes" ] && echo True || echo False)
hr
printf '\n  %s%sFINAL CONFIRMATION%s\n' "$BOLD" "$RED" "$RST"
if [ "$RUN_ORCH" = "yes" ]; then
    printf '  Run the post-install orchestrator: %s%s%s\n' "$BOLD" "$SWUPDATE_PY" "$RST"
    printf '  (installs whatever is staged in pending-updates; reboots).\n'
else
    printf '  Install package : %s%s%s\n' "$BOLD" "${DESC:-<spool file>}" "$RST"
    printf '  OSAL path arg   : %s\n' "${OSAL_PATH:-(empty => $SPOOL_FILE)}"
    printf '  Keep current ver: %s (rollback target)\n' "$KC_BOOL"
fi
printf '  The instrument will %sREBOOT%s to apply it.\n\n' "$BOLD" "$RST"
printf '  Type %sINSTALL%s (capitals) to proceed, anything else to cancel: ' "$RED" "$RST"
read -r FINAL
[ "$FINAL" = "INSTALL" ] || { printf '\n'; bad "Cancelled - no update was triggered."; exit 2; }

# ---- execute --------------------------------------------------------------
printf '\n'
if [ "$RUN_ORCH" = "yes" ]; then
    inf "Running orchestrator ..."
    python3 "$SWUPDATE_PY"
    rc=$?
    printf '\n'
    [ $rc -eq 0 ] && ok "Orchestrator finished (rc=0). If a SW package was staged, the box reboots." \
                  || bad "Orchestrator returned rc=$rc - check $SWUPDATE_LOG_GLOB"
    exit $rc
fi

inf "Sending SoftwareUpgradeOffline ..."
OSAL_PATH="$OSAL_PATH" DESC="$DESC" KC="$KC_BOOL" python3 - <<'PY'
import os, sys
from rlx_osal import OSAL
path = os.environ.get("OSAL_PATH", "")
desc = os.environ.get("DESC", "")
keep = os.environ.get("KC", "True") == "True"
try:
    r = OSAL().SoftwareUpgradeOffline(path, desc, desc, keep, False, "")
    print(f"outcome={r.outcome} msg={r.errorMessage}")
    # OSAL usually reboots as part of the upgrade; a returned non-OK means it
    # did NOT start.
    sys.exit(0 if r.outcome == 1 else 6)   # 1 == OSAL_OK
except Exception as e:
    print(f"exception: {e}")
    sys.exit(6)
PY
rc=$?
printf '\n'
if [ $rc -eq 0 ]; then
    ok "${BOLD}Upgrade accepted.${RST} The instrument is rebooting to apply it."
    inf "Watch progress after it comes back with:  $(basename "$0") status --watch"
    inf "Live log during upgrade:  tail -f $RLX_UP_LOG"
else
    bad "Upgrade was NOT started (see message above)."
    inf "Check $RLX_UP_LOG and $SWUPDATE_LOG_GLOB for the reason."
fi
exit $rc
