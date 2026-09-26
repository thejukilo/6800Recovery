#!/usr/bin/env bash
#
# build-recovery-usb.sh - One-command builder for the RLX recovery USB.
#
# Turns a blank USB stick into a bootable "Factory Reset" recovery stick:
# a SystemRescue live system (which already bundles whiptail + btrfs-progs)
# plus factory-reset-menu.sh, laid down with Ventoy so the same stick stays
# reusable and the menu file sits on a writable partition.
#
# Run on a LINUX host (your live Debian, a workstation, or WSL2 with USB
# passthrough) as root. NOT on the instrument itself.
#
#   sudo ./build-recovery-usb.sh --device /dev/sdX --iso systemrescue-XX.iso
#
# Options:
#   --device /dev/sdX   The USB stick to turn into the recovery stick. ERASED.
#   --iso PATH          A SystemRescue ISO you already downloaded.
#   --ventoy DIR        Path to an extracted Ventoy release (containing
#                       Ventoy2Disk.sh). If omitted, the script looks for
#                       `ventoy` in PATH / common locations.
#   --force             Allow a non-removable target (dangerous; off by default).
#   -h, --help          Show help.
#
# SAFETY: refuses non-removable disks unless --force, shows the exact target
# (model/size), and requires you to retype the device path and "ERASE".
#
# WARNING: this ERASES the chosen USB. Double-check --device. There is no undo.

set -euo pipefail

DEVICE=""; ISO=""; VENTOY_DIR=""; FORCE="no"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
MENU_SRC="$SELF_DIR/factory-reset-menu.sh"

# ---- colours --------------------------------------------------------------
if [ -t 1 ]; then B="$(printf '\033[1m')"; R="$(printf '\033[31m')"; G="$(printf '\033[32m')"
    Y="$(printf '\033[33m')"; C="$(printf '\033[36m')"; Z="$(printf '\033[0m')"
else B=""; R=""; G=""; Y=""; C=""; Z=""; fi
ok(){ printf '  %s✓%s %s\n' "$G" "$Z" "$1"; }
inf(){ printf '  %s•%s %s\n' "$C" "$Z" "$1"; }
warn(){ printf '  %s!%s %s\n' "$Y" "$Z" "$1"; }
die(){ printf '  %s✗%s %s\n' "$R" "$Z" "$1"; exit "${2:-1}"; }

usage(){ sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do case "$1" in
    --device) DEVICE="${2:?}"; shift 2 ;;
    --iso)    ISO="${2:?}"; shift 2 ;;
    --ventoy) VENTOY_DIR="${2:?}"; shift 2 ;;
    --force)  FORCE="yes"; shift ;;
    -h|--help) usage 0 ;;
    *) die "Unknown option: $1 (try --help)" 2 ;;
esac; done

[ "$(id -u)" = "0" ] || die "Run as root (sudo)." 1
[ -n "$DEVICE" ] || die "Need --device /dev/sdX (see --help)." 2
[ -b "$DEVICE" ] || die "$DEVICE is not a block device." 2
[ -n "$ISO" ] && [ -f "$ISO" ] || die "Need --iso PATH to a SystemRescue ISO." 2
[ -f "$MENU_SRC" ] || die "factory-reset-menu.sh not found next to this script." 2

# strip a trailing partition digit for the base disk (/dev/sdb1 -> /dev/sdb)
BASE="$DEVICE"
DEVNAME="$(basename "$BASE")"

# ---- safety: describe + gate ----------------------------------------------
REMOVABLE="$(cat "/sys/block/$DEVNAME/removable" 2>/dev/null || echo 0)"
MODEL="$(cat "/sys/block/$DEVNAME/device/model" 2>/dev/null | tr -s ' ' || echo '?')"
SIZE="$(lsblk -dno SIZE "$BASE" 2>/dev/null || echo '?')"

printf '\n  %sRLX recovery USB builder%s\n' "$B" "$Z"
printf '  %s----------------------------------------%s\n' "$C" "$Z"
inf "Target : $BASE   ($MODEL, $SIZE)"
inf "ISO    : $(basename "$ISO")"
inf "Menu   : $MENU_SRC"
if [ "$REMOVABLE" != "1" ]; then
    if [ "$FORCE" != "yes" ]; then
        die "$BASE is NOT flagged removable — refusing (use --force only if you are certain)." 3
    fi
    warn "$BASE is not removable but --force was given. Be very sure."
fi

printf '\n  %sThis will ERASE %s.%s\n' "$R" "$BASE" "$Z"
printf '  Type the device path again to confirm: '
read -r c1; [ "$c1" = "$BASE" ] || die "Mismatch — aborted." 3
printf '  Type %sERASE%s to proceed: ' "$R" "$Z"
read -r c2; [ "$c2" = "ERASE" ] || die "Not confirmed — aborted." 3

# unmount anything mounted from the device
for p in $(lsblk -lno NAME "$BASE" | tail -n +2); do umount "/dev/$p" 2>/dev/null || true; done

# ---- locate Ventoy --------------------------------------------------------
VENTOY_SH=""
if [ -n "$VENTOY_DIR" ] && [ -x "$VENTOY_DIR/Ventoy2Disk.sh" ]; then VENTOY_SH="$VENTOY_DIR/Ventoy2Disk.sh"
elif command -v Ventoy2Disk.sh >/dev/null 2>&1; then VENTOY_SH="$(command -v Ventoy2Disk.sh)"
else
    for d in ./ventoy* /opt/ventoy* "$HOME"/ventoy* /usr/local/ventoy*; do
        [ -x "$d/Ventoy2Disk.sh" ] && { VENTOY_SH="$d/Ventoy2Disk.sh"; break; }
    done
fi

if [ -n "$VENTOY_SH" ]; then
    # ---- Ventoy path (preferred): reusable stick, writable data partition --
    inf "Installing Ventoy with $VENTOY_SH ..."
    "$VENTOY_SH" -I -g "$BASE"    # -I install (GPT); Ventoy prompts its own y/N
    sleep 2; partprobe "$BASE" 2>/dev/null || true; sleep 2
    # Ventoy's data partition is partition 1 (exFAT)
    DATA="${BASE}1"; [ -b "${BASE}p1" ] && DATA="${BASE}p1"
    MNT="$(mktemp -d)"
    mount "$DATA" "$MNT" 2>/dev/null || die "Could not mount Ventoy data partition $DATA." 4
    inf "Copying ISO and menu onto the stick ..."
    cp -f "$ISO" "$MNT/"
    sed 's/\r$//' "$MENU_SRC" > "$MNT/factory-reset-menu.sh"
    cat > "$MNT/READ-ME-FIRST.txt" <<TXT
RLX Factory Reset recovery USB
==============================
Boot this stick ON the instrument. In the Ventoy menu pick the SystemRescue
ISO. When it boots to a root prompt, run:

    sh /ventoy/factory-reset-menu.sh

Then: Show status -> Arm Factory Reset -> Reboot (REMOVE the USB during reboot).
Use only as directed by GCS, when the RLX-Maintenance UI cannot do it.
TXT
    sync; umount "$MNT"; rmdir "$MNT"
    ok "${B}Recovery USB ready (Ventoy).${Z}"
    inf "Boot it on the instrument, pick the SystemRescue ISO, then:"
    inf "  sh /ventoy/factory-reset-menu.sh"
else
    # ---- fallback: raw-write the ISO (bootable, but no writable partition) --
    warn "Ventoy not found — falling back to writing the ISO directly."
    warn "The menu can't be embedded this way; carry it on a 2nd stick or fetch it."
    inf "Writing ISO to $BASE (this takes a few minutes) ..."
    dd if="$ISO" of="$BASE" bs=4M conv=fsync status=progress
    sync
    ok "${B}Bootable SystemRescue USB written.${Z}"
    inf "For the menu: copy factory-reset-menu.sh onto a second USB, or install"
    inf "Ventoy and re-run this so the menu rides on the same stick."
    inf "Get Ventoy: https://www.ventoy.net  (extract it, pass --ventoy DIR)"
fi

printf '\n'
ok "Done. Test it: boot the stick, run the menu, choose 'Show status' first."
