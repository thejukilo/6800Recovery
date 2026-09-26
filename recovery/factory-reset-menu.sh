#!/usr/bin/env bash
#
# factory-reset-menu.sh - Offline, menu-driven RLX Factory Reset "arming" tool.
#
# Runs from a bootable Linux USB (e.g. SystemRescue / Debian live) that you
# boot ON the cobas 6800/8800 instrument when the RLX-Maintenance UI is
# unreachable (black screen) but the instrument itself still boots.
#
# It does NOT perform the reset. It writes the flag file the instrument's own
# initramfs reads on the next boot:
#
#     /rlx-boot   (at the top of the btrfs 'root' subvolume) containing:
#         ACTION=restore-snapshot
#         SNAPSHOT_TYPE=factory
#
# You then remove the USB and reboot the instrument; its initramfs performs
# the factory-snapshot restore.
#
# Safety: it refuses unless it can (a) positively identify an RLX btrfs system
# and (b) find an existing factory snapshot (snapshots/F) to revert to -
# arming a factory reset with no factory snapshot would leave the box
# unbootable.
#
# --------------------------------------------------------------------------
#  USE POLICY - this arms a DESTRUCTIVE factory reset. Use ONLY when directed
#  by GCS and when the RLX-Maintenance UI cannot do it. Requires the
#  instrument to still boot far enough to run its initramfs.
# --------------------------------------------------------------------------

set -euo pipefail

FLAG_BODY=$'ACTION=restore-snapshot\nSNAPSHOT_TYPE=factory\n'
DETECT_MNT="/run/rlx-detect"
RW_MNT="/run/rlx-rw"
TITLE="cobas 6800/8800 - Factory Reset (offline)"

cleanup() {
    umount "$DETECT_MNT" 2>/dev/null || true
    umount "$RW_MNT" 2>/dev/null || true
}
trap cleanup EXIT

# ---- UI abstraction (whiptail > dialog > plain) ---------------------------
UI=""
command -v whiptail >/dev/null 2>&1 && UI=whiptail
[ -z "$UI" ] && command -v dialog >/dev/null 2>&1 && UI=dialog

ui_msg() {  # title, text
    if [ -n "$UI" ]; then "$UI" --title "$1" --msgbox "$2" 20 74
    else printf '\n=== %s ===\n%s\n\n[enter to continue] ' "$1" "$2"; read -r _; fi
}
ui_yesno() {  # title, text  -> 0 yes / 1 no
    if [ -n "$UI" ]; then "$UI" --title "$1" --yesno "$2" 20 74
    else printf '\n=== %s ===\n%s\n\ntype yes to confirm: ' "$1" "$2"; read -r a; [ "$a" = "yes" ]; fi
}
ui_menu() {  # title, text, then tag/item pairs -> prints chosen tag
    local title="$1" text="$2"; shift 2
    if [ -n "$UI" ]; then "$UI" --title "$title" --menu "$text" 20 74 6 "$@" 3>&1 1>&2 2>&3
    else
        printf '\n=== %s ===\n%s\n' "$title" "$text"
        while [ $# -gt 0 ]; do printf '  %s) %s\n' "$1" "$2"; shift 2; done
        printf 'choice: '; read -r c; echo "$c"
    fi
}

[ "$(id -u)" = "0" ] || { echo "Run as root (sudo)."; exit 1; }
mkdir -p "$DETECT_MNT" "$RW_MNT"

# ==========================================================================
#  Detect the RLX instrument disk
# ==========================================================================
# Prints "DEVICE\tVERSION\tHASF" for the first btrfs that looks like an RLX
# system (root + opt subvols, /opt/roche present). HASF = yes|no (factory snap).
detect_rlx() {
    local dev ver hasf
    for dev in $(blkid -t TYPE=btrfs -o device 2>/dev/null); do
        umount "$DETECT_MNT" 2>/dev/null || true
        mount -o ro,subvolid=5 "$dev" "$DETECT_MNT" 2>/dev/null || continue
        if [ -d "$DETECT_MNT/root/etc" ] && [ -e "$DETECT_MNT/opt/roche" ]; then
            ver="unknown"
            [ -f "$DETECT_MNT/opt/roche/etc/projectinfo" ] && ver="$(cat "$DETECT_MNT/opt/roche/etc/projectinfo")"
            hasf="no"
            if btrfs subvolume list "$DETECT_MNT" 2>/dev/null | grep -q 'snapshots/F'; then hasf="yes"; fi
            umount "$DETECT_MNT" 2>/dev/null || true
            printf '%s\t%s\t%s\n' "$dev" "$ver" "$hasf"
            return 0
        fi
        umount "$DETECT_MNT" 2>/dev/null || true
    done
    return 1
}

arm_factory_reset() {
    ui_msg "What this will do" \
"This tool ARMS a Factory Reset on the cobas 6800/8800 instrument.

It writes a flag to the instrument's disk. On the NEXT boot of the
instrument, its own recovery step reverts the system to the FACTORY
SNAPSHOT and reboots.

This tool does not perform the reset itself and does not touch the
factory snapshot now - it only sets the flag."

    ui_msg "WARNING - read carefully" \
"* DESTRUCTIVE: the instrument returns to its factory snapshot.
  Current system state and configuration are discarded. Not reversible.

* Use ONLY when instructed by GCS, AND only when the RLX-Maintenance
  UI cannot perform the reset (e.g. black screen).

* A FACTORY SNAPSHOT must already exist on the instrument. If none is
  found, this tool will refuse - arming without one can make the
  instrument unbootable.

* The instrument must still boot far enough to run its recovery step.
  If it cannot boot at all, this will not help."

    if ! ui_yesno "Confirm intent" \
"Do you confirm BOTH:
  1. GCS has instructed this factory reset, and
  2. the RLX-Maintenance UI cannot do it?

Select Yes only if both are true."; then
        ui_msg "Cancelled" "No changes were made."; return
    fi

    # detect
    local line dev ver hasf
    if ! line="$(detect_rlx)"; then
        ui_msg "No instrument found" \
"Could not find an RLX (cobas 6800/8800) system disk on this machine.

No btrfs filesystem with the expected layout (root + opt subvolumes,
/opt/roche present) was detected. Nothing was changed."
        return
    fi
    dev="$(printf '%s' "$line" | cut -f1)"
    ver="$(printf '%s' "$line" | cut -f2)"
    hasf="$(printf '%s' "$line" | cut -f3)"

    if [ "$hasf" != "yes" ]; then
        ui_msg "Refusing - no factory snapshot" \
"Instrument disk: $dev
Version: $ver

NO factory snapshot (snapshots/F) was found on this instrument.

Arming a factory reset now would leave the instrument UNBOOTABLE
(the restore removes the current boot entry with nothing to restore).

Refusing. Nothing was changed. A factory snapshot must be created
first (normally done at manufacturing)."
        return
    fi

    if ! ui_yesno "FINAL CONFIRMATION" \
"Arm FACTORY RESET on:

  Device : $dev
  Version: $ver
  Factory snapshot: present

The instrument will factory-reset on its next boot.

Proceed?"; then
        ui_msg "Cancelled" "No changes were made."; return
    fi

    # write the flag into the 'root' subvolume
    umount "$RW_MNT" 2>/dev/null || true
    if ! mount -o rw,subvolid=5 "$dev" "$RW_MNT" 2>/dev/null; then
        ui_msg "Error" "Could not mount $dev read-write. Nothing was changed."
        return
    fi
    if [ ! -d "$RW_MNT/root" ]; then
        umount "$RW_MNT" 2>/dev/null || true
        ui_msg "Error" "Unexpected layout on $dev (no 'root' subvolume). Aborted."
        return
    fi
    printf '%s' "$FLAG_BODY" > "$RW_MNT/root/rlx-boot"
    sync
    umount "$RW_MNT" 2>/dev/null || true

    ui_msg "Armed" \
"Factory reset ARMED on $dev ($ver).

Next steps:
  1. Choose 'Reboot' (or power-cycle).
  2. REMOVE THIS USB STICK during reboot so the INSTRUMENT boots,
     not the USB.
  3. The instrument performs the factory reset and reboots itself.

To cancel before rebooting: re-run and choose 'Disarm', or delete
/rlx-boot from the instrument's root subvolume."
}

disarm() {
    local line dev
    if ! line="$(detect_rlx)"; then ui_msg "No instrument found" "Nothing to disarm."; return; fi
    dev="$(printf '%s' "$line" | cut -f1)"
    umount "$RW_MNT" 2>/dev/null || true
    mount -o rw,subvolid=5 "$dev" "$RW_MNT" 2>/dev/null || { ui_msg "Error" "Could not mount $dev rw."; return; }
    if [ -f "$RW_MNT/root/rlx-boot" ]; then
        rm -f "$RW_MNT/root/rlx-boot"; sync
        ui_msg "Disarmed" "Removed the pending flag from $dev. No reset will occur."
    else
        ui_msg "Nothing armed" "No /rlx-boot flag was present on $dev."
    fi
    umount "$RW_MNT" 2>/dev/null || true
}

show_status() {
    local line dev ver hasf
    if ! line="$(detect_rlx)"; then ui_msg "Status" "No RLX instrument disk detected."; return; fi
    dev="$(printf '%s' "$line" | cut -f1)"; ver="$(printf '%s' "$line" | cut -f2)"; hasf="$(printf '%s' "$line" | cut -f3)"
    local armed="no"
    mount -o ro,subvolid=5 "$dev" "$DETECT_MNT" 2>/dev/null && {
        [ -f "$DETECT_MNT/root/rlx-boot" ] && armed="yes"
        umount "$DETECT_MNT" 2>/dev/null || true; }
    ui_msg "Instrument status (read-only)" \
"Device            : $dev
Version           : $ver
Factory snapshot  : $hasf
Reset armed now   : $armed"
}

# ==========================================================================
#  Main menu
# ==========================================================================
while true; do
    choice="$(ui_menu "$TITLE" "Offline recovery menu.  Use only as directed by GCS." \
        status  "Show instrument status (read-only)" \
        arm     "Arm Factory Reset (writes flag, reset on next boot)" \
        disarm  "Disarm (cancel a pending Factory Reset)" \
        reboot  "Reboot  (REMOVE the USB first!)" \
        shell   "Exit to shell")" || break
    case "$choice" in
        status) show_status ;;
        arm)    arm_factory_reset ;;
        disarm) disarm ;;
        reboot) if ui_yesno "Reboot" "Have you REMOVED the USB stick so the instrument boots next?\n\nReboot now?"; then reboot; fi ;;
        shell|"") break ;;
    esac
done
