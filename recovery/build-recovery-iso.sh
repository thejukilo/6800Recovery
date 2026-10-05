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
#   --iso PATH       A SystemRescue ISO (https://www.system-rescue.org)
#   --out PATH       Output ISO (default: ./rlx-recovery.iso)
#   --menu PATH      Menu script to embed (default: factory-reset-menu.sh beside this)
#   --label STR      Factory-reset menu entry text (default: "Start Factory Reset")
#   --timeout N      Boot-menu auto-boot seconds (default 2, or 30 when --deploy-iso
#                    is used so there's time to pick Deploy; 0 = boot instantly)
#   --logo PATH      Your logo (SVG or PNG). Top-right on the boot screen + GTK menu.
#                    Needs imagemagick (+ librsvg2-bin for SVG).
#   --gui PATH       GTK screen-2 app (default: factory-reset-gui.py beside this)
#   --deploy-iso P   A Molior installer ISO (e.g. 6800.iso). Its installer is folded
#                    INTO this recovery ISO and offered as a "Deploy <name>" boot
#                    entry that RE-IMAGES the whole instrument disk (UEFI only).
#   --deploy-name S  Display name for the Deploy entry (default: read from the
#                    installer's README.md, else the ISO filename).
#   --no-brand       Keep SystemRescue's stock (multi-entry) boot menu
#   -h, --help       Show help.
#
# NOTE (--deploy-iso): the installer's /vmlinuz, /initrd.img and /image.cpio.gz are
# copied to the root of the output ISO, so once flashed to USB they sit on the real
# medium exactly as the standalone installer expects. The output ISO grows by the
# installer's size (~1.7 GB); you need a few GB free where --out is written.
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
BRAND="yes"; LABEL="Start Factory Reset"; TIMEOUT="2"; TIMEOUT_SET="no"
LOGO=""; GUI_SRC="$SELF_DIR/factory-reset-gui.py"
DEPLOY_ISO=""; DEPLOY_NAME=""

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
    --timeout) TIMEOUT="${2:?}"; TIMEOUT_SET="yes"; shift 2 ;;
    --logo) LOGO="${2:?}"; shift 2 ;;
    --gui) GUI_SRC="${2:?}"; shift 2 ;;
    --deploy-iso) DEPLOY_ISO="${2:?}"; shift 2 ;;
    --deploy-name) DEPLOY_NAME="${2:?}"; shift 2 ;;
    --no-brand) BRAND="no"; shift ;;
    -h|--help) usage 0 ;;
    *) die "Unknown option: $1 (try --help)" 2 ;;
esac; done
LABEL="${LABEL//\'/}"                 # no single quotes (breaks grub menuentry)
case "$TIMEOUT" in *[!0-9]*) die "--timeout must be whole seconds" 2 ;; esac

# A Deploy entry means the operator must see and choose from the menu, so give a
# longer default auto-boot window (still defaults to Factory Reset) and force the
# branded single-choice menu (the Deploy entry lives there).
if [ -n "$DEPLOY_ISO" ]; then
    [ "$TIMEOUT_SET" = "yes" ] || TIMEOUT="30"
    [ "$BRAND" = "no" ] && { inf "--deploy-iso needs the branded menu; ignoring --no-brand."; BRAND="yes"; }
fi

command -v xorriso >/dev/null 2>&1 || die "xorriso not found. Install it (e.g. apt-get install xorriso)." 1
[ -n "$ISO" ] && [ -f "$ISO" ] || die "Need --iso PATH to a SystemRescue ISO." 2
[ -f "$MENU" ] || die "Menu script not found: $MENU" 2
[ -z "$DEPLOY_ISO" ] || [ -f "$DEPLOY_ISO" ] || die "--deploy-iso file not found: $DEPLOY_ISO" 2
# sanity: is it really a SystemRescue image?
if ! xorriso -indev "$ISO" -toc 2>/dev/null | grep -qi 'sysresc\|SYSRESC\|RESCUE'; then
    inf "Note: the ISO volume id doesn't look like SystemRescue — continuing anyway."
fi

WORK="$(mktemp -d)"; DSTAGE=""; DMNT=""
cleanup() {
    [ -n "$DMNT" ] && mountpoint -q "$DMNT" 2>/dev/null && umount "$DMNT" 2>/dev/null
    rm -rf "$WORK" ${DSTAGE:+"$DSTAGE"} ${DMNT:+"$DMNT"}
}
trap cleanup EXIT

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

# ---- optional deploy image: fold a Molior installer ISO into this ISO ------
# The installer boots from three files at the medium root (/vmlinuz, /initrd.img,
# /image.cpio.gz). We extract them from the installer ISO and place them at the
# root of our output ISO; once flashed to USB they sit on the real medium exactly
# as the standalone installer expects, so the Deploy entry boots it identically.
DEPLOY_MAPS=(); DNAME=""; DSRC=""
if [ -n "$DEPLOY_ISO" ]; then
    # Get the installer's three root files WITHOUT a 1.7 GB staging copy where we
    # can: loop-mount the ISO read-only and map its files straight in (no extra
    # disk). Fall back to extracting (needs ~1.7 GB scratch) only if we can't mount.
    DMNT="$(mktemp -d)"
    if mount -o loop,ro "$DEPLOY_ISO" "$DMNT" 2>/dev/null; then
        DSRC="$DMNT"
        inf "Reading installer from $(basename "$DEPLOY_ISO") (mounted, no extra disk)."
    else
        rmdir "$DMNT" 2>/dev/null; DMNT=""
        DSTAGE="$(dirname "$OUT")/.rlx-deploy-stage.$$"; mkdir -p "$DSTAGE"; DSRC="$DSTAGE"
        inf "Extracting installer from $(basename "$DEPLOY_ISO") (needs ~1.7 GB scratch) ..."
        xorriso -osirrox on -indev "$DEPLOY_ISO" \
                -extract /vmlinuz        "$DSTAGE/vmlinuz" \
                -extract /initrd.img     "$DSTAGE/initrd.img" \
                -extract /image.cpio.gz  "$DSTAGE/image.cpio.gz" \
                -extract /README.md      "$DSTAGE/README.md" >/dev/null 2>&1 || true
    fi
    for f in vmlinuz initrd.img image.cpio.gz; do
        [ -s "$DSRC/$f" ] || die "Installer file /$f missing in $DEPLOY_ISO — is it a Molior installer ISO?" 4
    done
    # README.md (if present) names the image, e.g.
    #   "= Molior Installer for cobas6800_2.0.3.3330507+local  Mon, 03 Aug ... ="
    if [ -n "$DEPLOY_NAME" ]; then
        DNAME="$DEPLOY_NAME"
    elif [ -s "$DSRC/README.md" ]; then
        DNAME="$(sed -n '1p' "$DSRC/README.md" | sed -E 's/.*Installer for[[:space:]]+([^[:space:]]+).*/\1/; s/_/ /')"
    fi
    [ -n "$DNAME" ] || DNAME="$(basename "$DEPLOY_ISO" .iso)"
    DNAME="${DNAME//\'/}"             # no single quotes (breaks grub menuentry)
    DEPLOY_MAPS=(
        -map "$DSRC/vmlinuz"       /vmlinuz
        -map "$DSRC/initrd.img"    /initrd.img
        -map "$DSRC/image.cpio.gz" /image.cpio.gz
    )
    inf "Deploy entry: '${DNAME}' (RE-IMAGES the whole instrument disk, UEFI boot)."

    # Disk-space preflight: the output ISO ~= input ISO + the installer files.
    OUT_DIR="$(dirname "$OUT")"
    NEED_KB=$(( ( $(stat -c %s "$ISO") + $(stat -c %s "$DSRC/vmlinuz") \
                  + $(stat -c %s "$DSRC/initrd.img") + $(stat -c %s "$DSRC/image.cpio.gz") ) / 1024 ))
    NEED_KB=$(( NEED_KB + NEED_KB / 20 + 65536 ))          # +5% slack +64 MB
    FREE_KB=$(df -Pk "$OUT_DIR" 2>/dev/null | awk 'NR==2{print $4}')
    if [ -n "$FREE_KB" ] && [ "$FREE_KB" -lt "$NEED_KB" ]; then
        die "Not enough free space in $OUT_DIR: need ~$(( NEED_KB/1024 )) MB, have $(( FREE_KB/1024 )) MB. Free some space (or write --out to a roomier disk) and retry." 2
    fi
fi

# SystemRescue runs /autorun/autorun at boot. This launcher stages the files off
# the read-only media, then tries the graphical GTK screen under X; if X or the
# GUI is unavailable it falls back to the text menu, so the stick always works.
cat > "$WORK/autorun" <<'AUTORUN'
#!/bin/sh
exec 0</dev/tty1 1>/dev/tty1 2>&1 || true
export HOME=/root
mkdir -p /run/rlx
SRC=""
for d in "$(dirname "$0")" /run/archiso/bootmnt/autorun /run/archiso/copytoram/autorun /autorun; do
    [ -f "$d/factory-reset-menu.sh" ] && SRC="$d" && break
done
[ -n "$SRC" ] && cp "$SRC"/factory-reset-* /run/rlx/ 2>/dev/null
[ -n "$SRC" ] && [ -f "$SRC/brand-logo.png" ] && cp "$SRC/brand-logo.png" /run/rlx/ 2>/dev/null

# Graphical screen (GTK under X), if available. We hand our app to startx as an
# EXPLICIT client so it cannot fall back to SystemRescue's default xinitrc
# (which would launch the whole Xfce desktop instead of our screen).
if [ -x /usr/bin/startx ] && [ -f /run/rlx/factory-reset-gui.py ]; then
    cat > /run/rlx/xsession <<'XS'
#!/bin/sh
[ -x /usr/bin/xfwm4 ] && xfwm4 &
export RLX_LOGO=/run/rlx/brand-logo.png
exec python3 /run/rlx/factory-reset-gui.py
XS
    chmod +x /run/rlx/xsession
    startx /run/rlx/xsession -- vt1 -nolisten tcp >/run/rlx/x.log 2>&1
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

    # Optional second choice: Deploy (re-image). A submenu whose DEFAULT entry is
    # Cancel, so an accidental Enter never starts a destructive re-image. It boots
    # the installer exactly as the standalone ISO does (search for /image.cpio.gz
    # on the medium, then its /vmlinuz + /initrd.img).
    DEPLOY_GRUB=""
    if [ -n "$DEPLOY_ISO" ]; then
        DEPLOY_GRUB="submenu 'Deploy ${DNAME}   (ERASES the whole instrument)' {
	menuentry 'Cancel  -  do NOT deploy (go back)' {
		configfile /boot/grub/grubsrcd.cfg
	}
	menuentry 'CONFIRM: erase this instrument and install ${DNAME}' {
		set gfxpayload=keep
		search --no-floppy --file --set=root /image.cpio.gz
		linux /vmlinuz quiet
		initrd /initrd.img
		boot
	}
}"
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
${DEPLOY_GRUB}
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
        "${DEPLOY_MAPS[@]}" \
        -end

[ -f "$OUT" ] || die "xorriso did not produce $OUT." 4
SIZE="$(du -h "$OUT" | cut -f1)"
printf '\n'
ok "${B}Built $OUT${Z} ($SIZE)"
inf "Flash it to a USB stick on Windows with balenaEtcher (pick image, pick USB,"
inf "Flash) — or Rufus in 'DD Image' mode. Use a raw write so the medium stays exact."
if [ -n "$DEPLOY_ISO" ]; then
    printf '\n'
    inf "${B}Boot menu (UEFI):${Z}"
    inf "  • Start Factory Reset          -> the recovery / factory-reset screen"
    inf "  • Deploy ${DNAME}  -> confirm, then RE-IMAGES the whole disk"
    inf "Default is Factory Reset; the Deploy submenu defaults to Cancel."
    inf "Test on the VM first: confirm Deploy boots the installer AND that it finds"
    inf "its payload (it searches the medium for /image.cpio.gz)."
else
    inf "Boot the stick on the instrument; it opens the Factory Reset menu automatically."
fi
printf '\n'
