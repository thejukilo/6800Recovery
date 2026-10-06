#!/usr/bin/env bash
#
# patch-installer-iso.sh - Make a *VM-testable* copy of a Molior cobas installer ISO.
#
# The vendor installer (e.g. 6800.iso) aborts in a VM because installer_logo()
# probes the display: `find /sys/class/drm/*/status`. In a VM there is no GPU
# (the installer only carries the i915 driver) so that find fails, and because
# the installer runs with `set -e`, the whole install aborts. On a real cobas
# instrument (Intel graphics) it works fine.
#
# This tool produces a CUSTOMIZED copy of the ISO that SKIPS that display step,
# so you can validate the rest of the deploy (medium detection, offline image
# write, EFI setup) in a VM/QEMU. It changes nothing else, keeps the MLR:cobas
# volume label (so the installer still installs OFFLINE, no deploy server), and
# marks the result loudly as customized.
#
#   !!  FOR VM / LAB TESTING ONLY - NEVER image a real instrument with this.  !!
#   The real instrument must be imaged with the UNMODIFIED vendor ISO.
#
# How it patches: it does NOT re-compress the vendor initrd (risky). It appends
# a tiny override cpio containing only the patched installer-hooks.sh.inc; the
# kernel unpacks concatenated cpios in order, so the override replaces the
# original at boot while the vendor initrd stays byte-for-byte intact.
#
# Run on a LINUX host with xorriso + cpio + unmkinitramfs (Debian: initramfs-tools):
#   ./patch-installer-iso.sh --iso 6800.iso [--out NAME]
#
# The output name ALWAYS contains "customized" (enforced).

set -euo pipefail

ISO=""; OUT=""
if [ -t 1 ]; then B="$(printf '\033[1m')"; R="$(printf '\033[31m')"; G="$(printf '\033[32m')"
    Y="$(printf '\033[33m')"; C="$(printf '\033[36m')"; Z="$(printf '\033[0m')"
else B=""; R=""; G=""; Y=""; C=""; Z=""; fi
ok(){ printf '  %s✓%s %s\n' "$G" "$Z" "$1"; }
inf(){ printf '  %s•%s %s\n' "$C" "$Z" "$1"; }
warn(){ printf '  %s!%s %s\n' "$Y" "$Z" "$1"; }
die(){ printf '  %s✗%s %s\n' "$R" "$Z" "$1"; exit "${2:-1}"; }
usage(){ sed -n '2,36p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do case "$1" in
    --iso) ISO="${2:?}"; shift 2 ;;
    --out) OUT="${2:?}"; shift 2 ;;
    -h|--help) usage 0 ;;
    *) die "Unknown option: $1 (try --help)" 2 ;;
esac; done

command -v xorriso >/dev/null 2>&1 || die "xorriso not found (apt-get install xorriso)." 1
command -v cpio >/dev/null 2>&1 || die "cpio not found (apt-get install cpio)." 1
command -v unmkinitramfs >/dev/null 2>&1 || die "unmkinitramfs not found (apt-get install initramfs-tools-core)." 1
[ -n "$ISO" ] && [ -f "$ISO" ] || die "Need --iso PATH to a Molior installer ISO (e.g. 6800.iso)." 2

# Enforce a "customized" marker in the output name no matter what.
if [ -z "$OUT" ]; then
    OUT="${ISO%.iso}-customized.iso"
elif ! printf '%s' "$OUT" | grep -qi 'customized'; then
    OUT="${OUT%.iso}-customized.iso"
fi
[ "$(readlink -f "$OUT")" != "$(readlink -f "$ISO")" ] || die "--out must differ from --iso." 2

WORK="$(dirname "$OUT")/.rlx-patch.$$"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/ir" "$WORK/ov/scripts"

# ---- 1. pull the vendor initrd out of the ISO (no mount needed) ------------
inf "Extracting initrd.img from $(basename "$ISO") ..."
xorriso -osirrox on -indev "$ISO" -extract /initrd.img "$WORK/initrd.img" >/dev/null 2>&1 \
    || die "Could not read /initrd.img from $ISO - is it a Molior installer ISO?" 4

# ---- 2. unpack it and patch the display guard ------------------------------
unmkinitramfs "$WORK/initrd.img" "$WORK/ir" 2>/dev/null \
    || die "Could not unpack initrd.img." 4
HOOKS="$(find "$WORK/ir" -path '*/scripts/installer-hooks.sh.inc' | head -n1)"
[ -n "$HOOKS" ] && [ -f "$HOOKS" ] \
    || die "installer-hooks.sh.inc not found in the initrd - unexpected installer layout." 4

# Flip the display-probe guard to always-skip. Matches the line:
#   if [ "$EXTRA_INSTALLER_CONFIGURE_DEVICE_RESOLUTION" != "no" ]; then
sed -i '/EXTRA_INSTALLER_CONFIGURE_DEVICE_RESOLUTION.*!= *"no"/c\if false ; then # CUSTOMIZED: skip display-resolution probe (no GPU in VM)' "$HOOKS"
grep -q 'CUSTOMIZED: skip display-resolution probe' "$HOOKS" \
    || die "Patch did not apply (the display-guard line was not found)." 4
ok "Patched installer-hooks.sh.inc (display-resolution step skipped)."

# ---- 3. build a tiny override cpio with just the patched file --------------
# relative path inside the initramfs must be scripts/installer-hooks.sh.inc
REL="$(printf '%s' "$HOOKS" | sed -E 's#.*/(scripts/installer-hooks\.sh\.inc)$#\1#')"
mkdir -p "$WORK/ov/$(dirname "$REL")"
cp "$HOOKS" "$WORK/ov/$REL"
( cd "$WORK/ov" && printf '%s\n' "$REL" | cpio -o -H newc --quiet ) > "$WORK/overlay.cpio"

# ---- 4. customized initrd = original + override (original kept intact) ------
cp "$WORK/initrd.img" "$WORK/initrd-customized.img"
cat "$WORK/overlay.cpio" >> "$WORK/initrd-customized.img"

# ---- 5. a loud marker file inside the ISO ----------------------------------
cat > "$WORK/CUSTOMIZED.txt" <<TXT
*** CUSTOMIZED cobas installer - FOR VM / LAB TESTING ONLY ***

This ISO was modified by patch-installer-iso.sh to SKIP the installer's
display-resolution step (find /sys/class/drm/*/status), which aborts in a VM
because there is no GPU. Everything else is unchanged and it still installs
OFFLINE (volume label MLR:cobas... preserved).

DO NOT use this to image a real cobas instrument. Use the UNMODIFIED vendor
ISO on the instrument. Built: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Source ISO: $(basename "$ISO")
TXT

# ---- 6. disk-space preflight + rebuild (preserve label + boot) -------------
NEED_KB=$(( ( $(stat -c %s "$ISO") + $(stat -c %s "$WORK/initrd-customized.img") ) / 1024 + 65536 ))
FREE_KB=$(df -Pk "$(dirname "$OUT")" 2>/dev/null | awk 'NR==2{print $4}')
if [ -n "$FREE_KB" ] && [ "$FREE_KB" -lt "$NEED_KB" ]; then
    die "Not enough free space in $(dirname "$OUT"): need ~$(( NEED_KB/1024 )) MB, have $(( FREE_KB/1024 )) MB." 2
fi
[ -e "$OUT" ] && rm -f "$OUT"

inf "Writing $(basename "$OUT") (preserving volume label + boot) ..."
xorriso -indev "$ISO" -outdev "$OUT" \
        -overwrite on \
        -boot_image any replay \
        -map "$WORK/initrd-customized.img" /initrd.img \
        -map "$WORK/CUSTOMIZED.txt"        /CUSTOMIZED.txt \
        -end

[ -f "$OUT" ] || die "xorriso did not produce $OUT." 4
LABEL="$(xorriso -indev "$OUT" -toc 2>/dev/null | grep -i 'Volume id' | head -n1 | sed 's/.*: *//')"
SIZE="$(du -h "$OUT" | cut -f1)"
printf '\n'
ok "${B}Built $OUT${Z} ($SIZE, volume id: ${LABEL:-unknown})"
warn "${B}VM / LAB TESTING ONLY${Z} - never image a real instrument with this."
inf "Flash with Etcher / Rufus-DD, or boot in QEMU with:  -cdrom \"$OUT\""
inf "The display step is skipped; it should now proceed to write the disk."
printf '\n'
