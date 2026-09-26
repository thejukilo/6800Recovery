#!/usr/bin/env bash
#
# build-recovery-iso.sh - Build a single bootable rlx-recovery.iso that boots
#                         straight into the Factory Reset menu.
#
# It remasters a SystemRescue ISO (which already bundles whiptail + btrfs-progs
# and boots on both BIOS and UEFI) by injecting factory-reset-menu.sh as the
# SystemRescue "autorun" script. The output is ONE .iso your field engineers
# flash to any USB stick with Rufus / balenaEtcher, exactly like any Linux ISO.
#
# Run once on a LINUX host (live Debian, workstation, WSL2) that has `xorriso`:
#     sudo apt-get install xorriso        # Debian/Ubuntu
#
# Usage:
#   ./build-recovery-iso.sh --iso systemrescue-XX.iso [--out rlx-recovery.iso]
#
# Options:
#   --iso PATH   A SystemRescue ISO you downloaded (https://www.system-rescue.org)
#   --out PATH   Output ISO (default: ./rlx-recovery.iso)
#   --menu PATH  Menu script to embed (default: factory-reset-menu.sh beside this)
#   --label STR  Boot-menu entry text (default: "cobas 6800 - Factory Reset (recovery)")
#   --timeout N  Boot-menu auto-boot seconds (default 2; 0 = boot instantly)
#   --no-brand   Keep SystemRescue's stock (multi-entry) boot menu
#   -h, --help   Show help.
#
# By default it also "brands" the boot: the confusing SystemRescue boot menu is
# collapsed to ONE renamed entry that auto-boots quietly into the menu, so a
# non-technical operator sees only a brief splash then the Factory Reset menu.
#
# The result boots to the menu automatically. It is NOT destructive to build;
# the menu itself still refuses unless it finds a factory snapshot, and asks
# for confirmation, before arming anything on an instrument.

set -euo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
ISO=""; OUT="$PWD/rlx-recovery.iso"; MENU="$SELF_DIR/factory-reset-menu.sh"
BRAND="yes"; LABEL="cobas 6800 - Factory Reset (recovery)"; TIMEOUT="2"

if [ -t 1 ]; then B="$(printf '\033[1m')"; R="$(printf '\033[31m')"; G="$(printf '\033[32m')"
    C="$(printf '\033[36m')"; Z="$(printf '\033[0m')"; else B=""; R=""; G=""; C=""; Z=""; fi
ok(){ printf '  %s✓%s %s\n' "$G" "$Z" "$1"; }
inf(){ printf '  %s•%s %s\n' "$C" "$Z" "$1"; }
die(){ printf '  %s✗%s %s\n' "$R" "$Z" "$1"; exit "${2:-1}"; }
usage(){ sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do case "$1" in
    --iso) ISO="${2:?}"; shift 2 ;;
    --out) OUT="${2:?}"; shift 2 ;;
    --menu) MENU="${2:?}"; shift 2 ;;
    --label) LABEL="${2:?}"; shift 2 ;;
    --timeout) TIMEOUT="${2:?}"; shift 2 ;;
    --no-brand) BRAND="no"; shift ;;
    -h|--help) usage 0 ;;
    *) die "Unknown option: $1 (try --help)" 2 ;;
esac; done
LABEL="${LABEL//\'/}"                 # no single quotes (breaks grub menuentry)
case "$TIMEOUT" in *[!0-9]*) die "--timeout must be whole seconds" 2 ;; esac

command -v xorriso >/dev/null 2>&1 || die "xorriso not found. Install it (e.g. apt-get install xorriso)." 1
[ -n "$ISO" ] && [ -f "$ISO" ] || die "Need --iso PATH to a SystemRescue ISO." 2
[ -f "$MENU" ] || die "Menu script not found: $MENU" 2
# sanity: is it really a SystemRescue image?
if ! xorriso -indev "$ISO" -toc 2>/dev/null | grep -qi 'sysresc\|SYSRESC\|RESCUE'; then
    inf "Note: the ISO volume id doesn't look like SystemRescue — continuing anyway."
fi

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

# Menu with clean LF line endings.
sed 's/\r$//' "$MENU" > "$WORK/factory-reset-menu.sh"

# SystemRescue runs scripts in the /autorun/ directory at boot (autorun is
# enabled with ar_nowait by default in sysrescue.d). Build /autorun/autorun as
# a launcher that attaches to the console and runs the menu. The menu is
# EMBEDDED so there is no runtime path to locate.
{
    echo '#!/bin/sh'
    echo '# RLX recovery: launch the Factory Reset menu on the console at boot.'
    echo 'exec 0</dev/tty1 1>/dev/tty1 2>&1 || true'
    echo "cat > /tmp/rlx-frm.sh <<'RLX_MENU_EOF'"
    cat "$WORK/factory-reset-menu.sh"
    echo 'RLX_MENU_EOF'
    echo 'exec bash /tmp/rlx-frm.sh'
} > "$WORK/autorun"

# ---- optional branding: collapse the SystemRescue boot menu to one clean,
#      renamed, quiet, auto-boot entry (BIOS syslinux + UEFI grub) ----------
BRAND_MAPS=()
if [ "$BRAND" = "yes" ]; then
    DECI=$(( TIMEOUT * 10 )); [ "$DECI" -lt 1 ] && DECI=1   # syslinux: 1/10s units

    # BIOS: replace the syslinux entry list with a single labelled entry.
    { cat <<SYS
INCLUDE boot/syslinux/sysresccd_head.cfg
MENU TITLE cobas 6800 Recovery
TIMEOUT ${DECI}
TOTALTIMEOUT ${DECI}
DEFAULT rlxreset

LABEL rlxreset
MENU LABEL ${LABEL}
LINUX boot/x86_64/vmlinuz
INITRD boot/intel_ucode.img,boot/amd_ucode.img,boot/x86_64/sysresccd.img
APPEND archisobasedir=sysresccd archisolabel=RESCUE1302 iomem=relaxed quiet loglevel=3
SYS
    } > "$WORK/sysresccd_sys.cfg"

    # UEFI: replace grub menu with a single labelled entry. Keep $archiso_param
    # literal (write a placeholder then substitute the label/timeout).
    cat > "$WORK/grubsrcd.cfg" <<'GRUB'
if [ -z "$srcd_skip_init" ]; then
	set timeout=@@TIMEOUT@@
	set default=0
	set pager=1
	if loadfont /boot/grub/font.pf2 ; then
		set gfxmode=640x480
		insmod all_video
		insmod gfxterm
		terminal_output gfxterm
	fi
fi
if [ -z "$archiso_param" ]; then
	archiso_param="archisolabel=RESCUE1302"
fi
menuentry '@@LABEL@@' {
	set gfxpayload=keep
	linux /sysresccd/boot/x86_64/vmlinuz archisobasedir=sysresccd $archiso_param iomem=relaxed quiet loglevel=3
	initrd /sysresccd/boot/intel_ucode.img /sysresccd/boot/amd_ucode.img /sysresccd/boot/x86_64/sysresccd.img
}
GRUB
    sed -i "s/@@TIMEOUT@@/${TIMEOUT}/; s/@@LABEL@@/${LABEL//\//\\/}/" "$WORK/grubsrcd.cfg"

    BRAND_MAPS=(
        -map "$WORK/sysresccd_sys.cfg" /sysresccd/boot/syslinux/sysresccd_sys.cfg
        -map "$WORK/grubsrcd.cfg"      /boot/grub/grubsrcd.cfg
    )
    inf "Branding boot menu: single entry '${LABEL}', ${TIMEOUT}s timeout, quiet boot."
fi

inf "Remastering $(basename "$ISO") -> $(basename "$OUT") ..."
inf "(preserving BIOS + UEFI boot, injecting /autorun/autorun menu)"

# Replay the original boot setup (keeps it bootable on BIOS + UEFI + isohybrid),
# then add our launcher into the existing /autorun directory, plus a standalone
# copy of the menu for manual use, plus (optionally) the branded boot menus.
xorriso -indev "$ISO" -outdev "$OUT" \
        -overwrite on \
        -boot_image any replay \
        -map "$WORK/autorun" /autorun/autorun \
        -map "$WORK/factory-reset-menu.sh" /autorun/factory-reset-menu.sh \
        "${BRAND_MAPS[@]}" \
        -end

[ -f "$OUT" ] || die "xorriso did not produce $OUT." 4
SIZE="$(du -h "$OUT" | cut -f1)"
printf '\n'
ok "${B}Built $OUT${Z} ($SIZE)"
inf "Flash it to a USB stick with Rufus (Windows) or balenaEtcher — like any Linux ISO."
inf "Boot the stick on the instrument; it opens the Factory Reset menu automatically."
inf "If a build doesn't auto-run, at its shell run the copy on the media:"
inf "  sh \$(find / -name factory-reset-menu.sh 2>/dev/null | head -1)"
printf '\n'
