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
#   --logo PATH  Your logo (SVG or PNG). Placed top-right on the boot screen and
#                the graphical menu. Needs imagemagick (+ librsvg2-bin for SVG).
#   --gui PATH   GTK screen-2 app (default: factory-reset-gui.py beside this)
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
LOGO=""; GUI_SRC="$SELF_DIR/factory-reset-gui.py"

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
    --logo) LOGO="${2:?}"; shift 2 ;;
    --gui) GUI_SRC="${2:?}"; shift 2 ;;
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

# Menu (text fallback) and GUI with clean LF line endings.
sed 's/\r$//' "$MENU" > "$WORK/factory-reset-menu.sh"
[ -f "$GUI_SRC" ] && sed 's/\r$//' "$GUI_SRC" > "$WORK/factory-reset-gui.py"

# ---- logo + white boot background (only when --logo is given) --------------
LOGO_MAPS=(); HAS_LOGO="no"
if [ -n "$LOGO" ]; then
    [ -f "$LOGO" ] || die "--logo file not found: $LOGO" 2
    command -v convert >/dev/null 2>&1 || die "ImageMagick 'convert' needed for --logo (apt-get install imagemagick)." 1
    # normalise the supplied logo to PNG (convert SVG with rsvg if needed)
    case "$LOGO" in
        *.svg|*.SVG) command -v rsvg-convert >/dev/null 2>&1 || die "rsvg-convert needed for an SVG logo (apt-get install librsvg2-bin)." 1
                     rsvg-convert -h 200 -f png -o "$WORK/brand-logo.png" "$LOGO" ;;
        *)           convert "$LOGO" -resize x200 "$WORK/brand-logo.png" ;;
    esac
    # white full-screen boot background with the logo placed top-right (UEFI/grub)
    convert -size 1024x768 xc:white \( "$WORK/brand-logo.png" -resize x84 \) \
            -gravity NorthEast -geometry +48+40 -composite "$WORK/bg1024.png"
    LOGO_MAPS=(
        -map "$WORK/brand-logo.png" /autorun/brand-logo.png
        -map "$WORK/bg1024.png"     /rlx/boot-bg.png
    )
    HAS_LOGO="yes"
fi

# GUI maps (embed the graphical screen; harmless if the GUI file is missing)
GUI_MAPS=()
[ -f "$WORK/factory-reset-gui.py" ] && GUI_MAPS=( -map "$WORK/factory-reset-gui.py" /autorun/factory-reset-gui.py )

# SystemRescue runs /autorun/autorun at boot. This launcher stages the files off
# the read-only media, then tries the graphical GTK screen under X; if X or the
# GUI is unavailable it falls back to the text menu, so the stick always works.
cat > "$WORK/autorun" <<'AUTORUN'
#!/bin/sh
exec 0</dev/tty1 1>/dev/tty1 2>&1 || true
mkdir -p /run/rlx
SRC=""
for d in "$(dirname "$0")" /run/archiso/bootmnt/autorun /run/archiso/copytoram/autorun /autorun; do
    [ -f "$d/factory-reset-menu.sh" ] && SRC="$d" && break
done
[ -n "$SRC" ] && cp "$SRC"/factory-reset-* /run/rlx/ 2>/dev/null
[ -f "$SRC/brand-logo.png" ] && cp "$SRC/brand-logo.png" /run/rlx/ 2>/dev/null

# Graphical screen (GTK under X), if available.
if [ -x /usr/bin/startx ] && [ -f /run/rlx/factory-reset-gui.py ]; then
    cat > /root/.xinitrc <<XRC
[ -x /usr/bin/xfwm4 ] && xfwm4 &
exec env RLX_LOGO=/run/rlx/brand-logo.png python3 /run/rlx/factory-reset-gui.py
XRC
    startx -- vt1 -nolisten tcp >/run/rlx/x.log 2>&1
fi

# Fallback: text menu (X missing, or it exited/failed).
[ -f /run/rlx/factory-reset-menu.sh ] && exec bash /run/rlx/factory-reset-menu.sh
echo "RLX recovery menu not found on the media."; exec bash
AUTORUN

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

    # UEFI: replace grub menu with a single labelled entry. When a logo is given,
    # show the white background image with dark menu text. Grub $vars are escaped
    # (\$) so only our shell vars expand.
    GRUB_BG=""
    if [ "$HAS_LOGO" = "yes" ]; then
        GRUB_BG=$'\t\tinsmod png\n\t\tbackground_image /rlx/boot-bg.png\n\t\tset color_normal=black/white\n\t\tset menu_color_normal=black/white\n\t\tset menu_color_highlight=white/blue'
    fi
    cat > "$WORK/grubsrcd.cfg" <<GRUB
if [ -z "\$srcd_skip_init" ]; then
	set timeout=${TIMEOUT}
	set default=0
	set pager=1
	if loadfont /boot/grub/font.pf2 ; then
		set gfxmode=1024x768
		insmod all_video
		insmod gfxterm
		terminal_output gfxterm
${GRUB_BG}
	fi
fi
if [ -z "\$archiso_param" ]; then
	archiso_param="archisolabel=RESCUE1302"
fi
menuentry '${LABEL}' {
	set gfxpayload=keep
	linux /sysresccd/boot/x86_64/vmlinuz archisobasedir=sysresccd \$archiso_param iomem=relaxed quiet loglevel=3
	initrd /sysresccd/boot/intel_ucode.img /sysresccd/boot/amd_ucode.img /sysresccd/boot/x86_64/sysresccd.img
}
GRUB

    BRAND_MAPS=(
        -map "$WORK/sysresccd_sys.cfg" /sysresccd/boot/syslinux/sysresccd_sys.cfg
        -map "$WORK/grubsrcd.cfg"      /boot/grub/grubsrcd.cfg
    )
    inf "Branding boot menu: single entry '${LABEL}', ${TIMEOUT}s timeout, quiet boot."
fi

inf "Remastering $(basename "$ISO") -> $(basename "$OUT") ..."
inf "(preserving BIOS + UEFI boot, injecting /autorun/autorun menu)"

# xorriso refuses to write into an existing non-empty output ISO, so clear a
# stale build first (never touch the input ISO).
if [ -e "$OUT" ]; then
    [ "$(readlink -f "$OUT")" = "$(readlink -f "$ISO")" ] && die "--out must differ from --iso." 2
    rm -f "$OUT" || die "Could not remove existing $OUT" 2
fi

# Replay the original boot setup (keeps it bootable on BIOS + UEFI + isohybrid),
# then add our launcher into the existing /autorun directory, plus a standalone
# copy of the menu for manual use, plus (optionally) the branded boot menus.
xorriso -indev "$ISO" -outdev "$OUT" \
        -overwrite on \
        -boot_image any replay \
        -map "$WORK/autorun" /autorun/autorun \
        -map "$WORK/factory-reset-menu.sh" /autorun/factory-reset-menu.sh \
        "${GUI_MAPS[@]}" \
        "${LOGO_MAPS[@]}" \
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
