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
#   -h, --help   Show help.
#
# The result boots to the menu automatically. It is NOT destructive to build;
# the menu itself still refuses unless it finds a factory snapshot, and asks
# for confirmation, before arming anything on an instrument.

set -euo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
ISO=""; OUT="$PWD/rlx-recovery.iso"; MENU="$SELF_DIR/factory-reset-menu.sh"

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
    -h|--help) usage 0 ;;
    *) die "Unknown option: $1 (try --help)" 2 ;;
esac; done

command -v xorriso >/dev/null 2>&1 || die "xorriso not found. Install it (e.g. apt-get install xorriso)." 1
[ -n "$ISO" ] && [ -f "$ISO" ] || die "Need --iso PATH to a SystemRescue ISO." 2
[ -f "$MENU" ] || die "Menu script not found: $MENU" 2
# sanity: is it really a SystemRescue image?
if ! xorriso -indev "$ISO" -toc 2>/dev/null | grep -qi 'sysresc\|SYSRESC\|RESCUE'; then
    inf "Note: the ISO volume id doesn't look like SystemRescue — continuing anyway."
fi

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

# The autorun launcher SystemRescue runs at boot. It attaches to the console
# and execs the embedded menu (search a few likely mount paths).
cat > "$WORK/autorun" <<'AR'
#!/bin/sh
# RLX recovery: launch the Factory Reset menu on the console at boot.
exec 0</dev/tty1 1>/dev/tty1 2>&1 || true
for p in /run/archiso/bootmnt/factory-reset-menu.sh \
         /run/archiso/copytoram/factory-reset-menu.sh \
         /factory-reset-menu.sh /root/factory-reset-menu.sh; do
    if [ -f "$p" ]; then exec bash "$p"; fi
done
echo "RLX recovery: factory-reset-menu.sh not found on the media."
exec bash
AR

# Embed the menu with clean LF line endings.
sed 's/\r$//' "$MENU" > "$WORK/factory-reset-menu.sh"

inf "Remastering $(basename "$ISO") -> $(basename "$OUT") ..."
inf "(preserving BIOS + UEFI boot, injecting autorun menu)"

# Replay the original boot setup (keeps it bootable on BIOS + UEFI + isohybrid),
# then add our two files at the ISO root.
xorriso -indev "$ISO" -outdev "$OUT" \
        -boot_image any replay \
        -map "$WORK/autorun" /autorun \
        -map "$WORK/factory-reset-menu.sh" /factory-reset-menu.sh \
        -end

[ -f "$OUT" ] || die "xorriso did not produce $OUT." 4
SIZE="$(du -h "$OUT" | cut -f1)"
printf '\n'
ok "${B}Built $OUT${Z} ($SIZE)"
inf "Flash it to a USB stick with Rufus (Windows) or balenaEtcher — like any Linux ISO."
inf "Boot the stick on the instrument; it opens the Factory Reset menu automatically."
inf "If a given SystemRescue build doesn't auto-run, at its shell run:"
inf "  sh /run/archiso/bootmnt/factory-reset-menu.sh"
printf '\n'
