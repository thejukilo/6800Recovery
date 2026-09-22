#!/usr/bin/env bash
#
# factory-reset.sh - Trigger a cobas 6800/8800 (RLX) Factory Reset over the
#                    local maintenance API when the RLX-Maintenance UI is
#                    unreachable (e.g. black screen after a downgrade).
#
# This calls exactly the same endpoint the "Factory Reset" button in
# RLX-Maintenance uses:
#
#     POST /rlx/api/login              (authenticate, PAM - same credentials
#                                       as the RLX-Maintenance login screen)
#     POST /rlx/api/system/factoryreset
#
# The instrument then reverts to its factory system snapshot and reboots.
#
# Intended to be run FROM the instrument itself over an SSH session, hitting
# 127.0.0.1. A local request is what the backend and UI both expect for a
# factory reset, so this avoids the remote-access gating entirely.
#
# --------------------------------------------------------------------------
#  USE POLICY
#  This tool must ONLY be used:
#    * when explicitly instructed to do so by GCS (Global Customer Support),
#      AND
#    * when a normal Factory Reset through the RLX-Maintenance UI is NOT
#      possible (for example: a black screen after a downgrade).
#  It is not a substitute for the UI workflow under normal conditions.
# --------------------------------------------------------------------------

set -euo pipefail

# ---- defaults -------------------------------------------------------------
HOST="127.0.0.1"
SCHEME="https"
PORT=""              # empty => default port for scheme (nginx front door)
PREFIX="/rlx"        # nginx serves the app under /rlx
USER_NAME="roche"
DRY_RUN="no"

COOKIE_JAR=""
cleanup() { [ -n "$COOKIE_JAR" ] && rm -f "$COOKIE_JAR" 2>/dev/null || true; }
trap cleanup EXIT

# ---- colours (only when attached to a terminal) ---------------------------
if [ -t 1 ]; then
    BOLD="$(printf '\033[1m')"; DIM="$(printf '\033[2m')"
    RED="$(printf '\033[31m')"; GRN="$(printf '\033[32m')"
    YEL="$(printf '\033[33m')"; BLU="$(printf '\033[36m')"
    RST="$(printf '\033[0m')"
else
    BOLD=""; DIM=""; RED=""; GRN=""; YEL=""; BLU=""; RST=""
fi

hr()  { printf '%s\n' "${DIM}────────────────────────────────────────────────────────────────${RST}"; }
ok()  { printf '  %s✓%s %s\n'  "$GRN" "$RST" "$1"; }
bad() { printf '  %s✗%s %s\n'  "$RED" "$RST" "$1"; }
inf() { printf '  %s•%s %s\n'  "$BLU" "$RST" "$1"; }
die() { bad "$1"; exit "${2:-1}"; }

usage() {
    cat <<EOF
${BOLD}Usage:${RST} $(basename "$0") [options]

  --host HOST     Target host           (default: ${HOST})
  --user NAME     Login user            (default: ${USER_NAME})
  --direct        Bypass nginx, talk straight to the rlx-web app on
                  http://HOST:8086 with no /rlx prefix. Use only if nginx
                  itself is down.
  --dry-run       Log in and verify the session, then STOP. Never triggers
                  the reset. Use this first to confirm your credentials.
  -h, --help      Show this help.
EOF
    exit 0
}

# ---- arg parsing ----------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --host)   HOST="${2:?--host needs a value}"; shift 2 ;;
        --user)   USER_NAME="${2:?--user needs a value}"; shift 2 ;;
        --direct) SCHEME="http"; PORT="8086"; PREFIX=""; shift ;;
        --dry-run) DRY_RUN="yes"; shift ;;
        -h|--help) usage ;;
        *) die "Unknown option: $1 (try --help)" ;;
    esac
done

command -v curl >/dev/null 2>&1 || die "curl is required but not found."

# Build the base URL
if [ -n "$PORT" ]; then BASE="${SCHEME}://${HOST}:${PORT}${PREFIX}"
else                    BASE="${SCHEME}://${HOST}${PREFIX}"; fi

# curl helper. -k: instrument serves its own TLS certificate.
CURL=(curl --silent --show-error -k --max-time 30)

# ==========================================================================
#  1. Explain
# ==========================================================================
clear 2>/dev/null || true
printf '\n'
printf '  %s╔══════════════════════════════════════════════════════════════╗%s\n' "$BOLD" "$RST"
printf '  %s║        cobas 6800 / 8800  ·  RLX Factory Reset (CLI)          ║%s\n' "$BOLD" "$RST"
printf '  %s╚══════════════════════════════════════════════════════════════╝%s\n' "$BOLD" "$RST"
printf '\n'
printf '  This utility triggers the same %sFactory Reset%s that the RLX-Maintenance\n' "$BOLD" "$RST"
printf '  UI performs, but over the local maintenance API. Use it only when the\n'
printf '  UI cannot be reached.\n\n'
printf '  What it does:\n'
inf "Authenticates against the local RLX maintenance API (${BASE})"
inf "Calls the factory-reset endpoint the UI button uses"
inf "The instrument reverts to its factory system snapshot and ${BOLD}reboots${RST}"
printf '\n'
printf '  %s%s What this means:%s current system state is discarded and the\n' "$BOLD" "$YEL" "$RST"
printf '  instrument returns to its factory snapshot. This is not reversible.\n'
printf '\n'
hr

# ==========================================================================
#  2. Use-policy consent gate
# ==========================================================================
printf '\n'
printf '  %s%s  USE POLICY — PLEASE READ  %s\n' "$BOLD" "$YEL" "$RST"
printf '\n'
printf '  This tool must ONLY be used:\n\n'
printf '    %s1.%s when you have been instructed to do so by %sGCS%s\n' "$BOLD" "$RST" "$BOLD" "$RST"
printf '       (Global Customer Support), %sand%s\n' "$BOLD" "$RST"
printf '    %s2.%s when a normal Factory Reset through the RLX-Maintenance UI\n' "$BOLD" "$RST"
printf '       is %snot possible%s (e.g. a black screen after a downgrade).\n' "$BOLD" "$RST"
printf '\n'
printf '  If either condition is not met, stop now and use the UI instead.\n'
printf '\n'
printf '  %sDo you confirm both conditions are met?%s Type %syes%s to continue: ' "$BOLD" "$RST" "$GRN" "$RST"
read -r CONSENT
case "${CONSENT}" in
    yes|YES|Yes) ok "Consent recorded." ;;
    *) printf '\n'; bad "Consent not given (\"${CONSENT:-<empty>}\"). Aborting — nothing was changed."; exit 2 ;;
esac
hr

# ==========================================================================
#  3. Credentials
# ==========================================================================
printf '\n  Enter your RLX-Maintenance credentials.\n\n'
printf '  User [%s]: ' "$USER_NAME"
read -r INPUT_USER
[ -n "$INPUT_USER" ] && USER_NAME="$INPUT_USER"
printf '  Password: '
read -rs PASSWORD; printf '\n'
[ -n "$PASSWORD" ] || die "No password entered. Aborting."

COOKIE_JAR="$(mktemp -t rlx-reset.XXXXXX)"
JSON_LOGIN=$(printf '{"username":"%s","password":"%s"}' "$USER_NAME" "$PASSWORD")

# ==========================================================================
#  4. Log in
# ==========================================================================
printf '\n'
inf "Logging in to ${BASE}/api/login ..."
LOGIN_CODE=$("${CURL[@]}" -o /dev/null -w '%{http_code}' \
    -c "$COOKIE_JAR" -X POST "${BASE}/api/login" \
    -H 'Content-Type: application/json' \
    --data "$JSON_LOGIN" || true)

case "$LOGIN_CODE" in
    200) ok "Authenticated as '${USER_NAME}'." ;;
    400|401) die "Login rejected (HTTP ${LOGIN_CODE}). Check the username/password." 3 ;;
    000) die "Could not reach ${BASE}. Is rlx-web/nginx running? Try --direct." 4 ;;
    *)   die "Unexpected login response (HTTP ${LOGIN_CODE})." 5 ;;
esac

# Verify the session really is valid
AUTH_CODE=$("${CURL[@]}" -o /dev/null -w '%{http_code}' \
    -b "$COOKIE_JAR" "${BASE}/api/authenticated" || true)
[ "$AUTH_CODE" = "200" ] && ok "Session verified." \
    || inf "Session check returned HTTP ${AUTH_CODE} (continuing)."

# Show the factory snapshot the reset will revert to, if available
SNAP=$("${CURL[@]}" -b "$COOKIE_JAR" "${BASE}/api/system/factorysystemversion" 2>/dev/null || true)
[ -n "$SNAP" ] && inf "Factory snapshot: ${SNAP}"

if [ "$DRY_RUN" = "yes" ]; then
    printf '\n'
    ok "${BOLD}Dry run complete.${RST} Credentials and connectivity are good."
    inf "No factory reset was performed. Re-run without --dry-run to proceed."
    exit 0
fi

# ==========================================================================
#  5. Final confirmation, then execute
# ==========================================================================
hr
printf '\n'
printf '  %s%sFINAL CONFIRMATION%s\n' "$BOLD" "$RED" "$RST"
printf '  You are about to factory-reset %s%s%s. The instrument will reboot.\n\n' "$BOLD" "$HOST" "$RST"
printf '  Type %sRESET%s (in capitals) to proceed, anything else to cancel: ' "$RED" "$RST"
read -r FINAL
[ "$FINAL" = "RESET" ] || { printf '\n'; bad "Cancelled — no reset was performed."; exit 2; }

printf '\n'
inf "Sending factory-reset request ..."
# Send the credentials inline (no session cookie) so the request authenticates
# as a fresh session. This bypasses rlx-web's auto-logout: a cookie session can
# expire during the confirmation prompt (the UI keeps it alive by pinging
# /api/auto-logout/last-access, which a CLI session does not), which returns 401
# on the reset. A new session authenticates straight from the request body.
RESET_CODE=$("${CURL[@]}" -o /dev/null -w '%{http_code}' \
    -X POST "${BASE}/api/system/factoryreset" \
    -H 'Content-Type: application/json' --data "$JSON_LOGIN" || true)

printf '\n'
case "$RESET_CODE" in
    200|202|204)
        ok "${BOLD}Factory reset accepted (HTTP ${RESET_CODE}).${RST}"
        inf "The instrument is reverting to its factory snapshot and will reboot."
        inf "Your SSH session will drop shortly — this is expected."
        ;;
    000)
        # A dropped connection can mean the reboot already began.
        printf '  %s!%s Connection closed with no HTTP status.\n' "$YEL" "$RST"
        inf "The reset may already be in progress (the box can drop the"
        inf "connection as it reboots). Verify at the instrument."
        ;;
    400)
        die "Reset rejected (HTTP 400) — credentials not accepted on the inline auth. Re-check user/password." 3
        ;;
    401)
        die "Session was not accepted (HTTP 401). Re-run — the tool now sends credentials inline to avoid this." 3
        ;;
    *)
        die "Factory reset returned HTTP ${RESET_CODE}. Reset NOT confirmed." 6
        ;;
esac
printf '\n'
