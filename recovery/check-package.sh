#!/usr/bin/env bash
#
# check-package.sh - Pre-flight validation for an RLX software-update package.
#
# Given an upgrade package (.tar.xz / .tar / .zip), an already-extracted
# directory, or a raw initrd file, it reports:
#
#   1. baseversion   - the version the package must be applied ON TOP OF.
#                      Compared against the installed version so you know the
#                      "upgrade package is for version ..." abort won't happen.
#   2. releaseversion- the version the package installs.
#   3. initrd storage drivers - whether the package's initrd contains the
#                      driver for THIS machine's disk controller, so you know
#                      whether the post-upgrade reboot will actually boot
#                      (the classic VMware 'unable to mount root' panic is a
#                      missing vmw_pvscsi here).
#
# It changes nothing. Run it before applying an update, especially on a VM.
#
# Usage:
#   ./check-package.sh /path/to/Package.tar.xz
#   ./check-package.sh /path/to/extracted-dir
#   ./check-package.sh /boot/efi/EFI/rlx/<bootid>_cobas6800_<ver>.initrd
#   ./check-package.sh --driver vmw_pvscsi /path/to/pkg   # force target driver

set -euo pipefail

PROJECTINFO="/opt/roche/etc/projectinfo"
DRIVERS_PROBE='vmw_pvscsi|mptspi|mpt3sas|megaraid_sas|ahci|ata_piix|nvme|virtio_scsi|virtio_blk|hv_storvsc|xen-blkfront'

# ---- colours --------------------------------------------------------------
if [ -t 1 ]; then
    B="$(printf '\033[1m')"; DIM="$(printf '\033[2m')"; R="$(printf '\033[31m')"
    G="$(printf '\033[32m')"; Y="$(printf '\033[33m')"; C="$(printf '\033[36m')"; Z="$(printf '\033[0m')"
else B=""; DIM=""; R=""; G=""; Y=""; C=""; Z=""; fi
ok()  { printf '  %s✓%s %s\n' "$G" "$Z" "$1"; }
bad() { printf '  %s✗%s %s\n' "$R" "$Z" "$1"; }
inf() { printf '  %s•%s %s\n' "$C" "$Z" "$1"; }
warn(){ printf '  %s!%s %s\n' "$Y" "$Z" "$1"; }
die() { bad "$1"; exit "${2:-1}"; }

usage() { printf '%sUsage:%s %s [--driver NAME] <package.tar.xz|dir|initrd>\n' "$B" "$Z" "$(basename "$0")"; exit "${1:-0}"; }
TARGET_DRIVER=""
case "${1:-}" in -h|--help|"") usage 0 ;; --driver) TARGET_DRIVER="${2:?}"; shift 2 ;; esac
INPUT="${1:-}"; [ -n "$INPUT" ] || usage 2
[ -e "$INPUT" ] || die "Not found: $INPUT" 2

# ---- detect this machine's disk controller driver -------------------------
detect_driver() {
    local d
    for h in /sys/class/scsi_host/host*; do
        d="$(cat "$h/proc_name" 2>/dev/null || true)"
        # the host backing "/" — good enough: first non-ata_piix (CD) host
        [ -n "$d" ] && [ "$d" != "ata_piix" ] && { echo "$d"; return; }
    done
    # fallback: driver bound to sda's controller
    local dev; dev="$(readlink -f /sys/block/sda/device 2>/dev/null | sed 's#/host.*##')"
    [ -n "$dev" ] && basename "$(readlink -f "$dev/../driver" 2>/dev/null)" 2>/dev/null || true
}
if [ -z "$TARGET_DRIVER" ]; then
    TARGET_DRIVER="$(detect_driver || true)"
fi

WORK=""; cleanup() { [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true; }
trap cleanup EXIT

# ---- resolve input to a directory to inspect ------------------------------
SRC_DIR=""
SINGLE_INITRD=""
case "$INPUT" in
    *.initrd|*initrd*|*.img)
        if [ -f "$INPUT" ]; then SINGLE_INITRD="$INPUT"; fi ;;
esac
if [ -z "$SINGLE_INITRD" ]; then
    if [ -d "$INPUT" ]; then
        SRC_DIR="$INPUT"
    else
        WORK="$(mktemp -d)"; SRC_DIR="$WORK"
        inf "Extracting $(basename "$INPUT") ..."
        case "$INPUT" in
            *.tar.xz|*.txz) tar -C "$WORK" -xf "$INPUT" 2>/dev/null || die "tar extract failed" 3 ;;
            *.tar)          tar -C "$WORK" -xf "$INPUT" 2>/dev/null || die "tar extract failed" 3 ;;
            *.zip)          command -v unzip >/dev/null && unzip -q -o "$INPUT" -d "$WORK" || die "unzip failed/missing" 3 ;;
            *)              tar -C "$WORK" -xf "$INPUT" 2>/dev/null || die "Unknown package type: $INPUT" 3 ;;
        esac
        # some packages wrap a second archive (archive.tar.xz) inside
        inner="$(find "$WORK" -maxdepth 2 -name '*.tar.xz' -o -maxdepth 2 -name 'archive.tar*' 2>/dev/null | head -1)"
        if [ -n "$inner" ] && [ ! -e "$WORK/archive" ]; then
            inf "Unwrapping inner archive $(basename "$inner") ..."
            tar -C "$WORK" -xf "$inner" 2>/dev/null || true
        fi
    fi
fi

# ---- initrd storage-driver check ------------------------------------------
list_initrd_drivers() {
    local f="$1"
    if command -v lsinitramfs >/dev/null;   then lsinitramfs   "$f" 2>/dev/null
    elif command -v unmkinitramfs >/dev/null; then unmkinitramfs -l "$f" 2>/dev/null
    else return 2; fi
}

check_one_initrd() {
    local f="$1" listing hits
    listing="$(list_initrd_drivers "$f")" || { warn "no lsinitramfs/unmkinitramfs — cannot inspect $(basename "$f")"; return; }
    hits="$(printf '%s\n' "$listing" | grep -ioE "$DRIVERS_PROBE" | sort -u | paste -sd' ' -)"
    printf '  %s%s%s\n' "$DIM" "$(basename "$f")" "$Z"
    inf "storage drivers: ${hits:-<none found>}"
    if [ -n "$TARGET_DRIVER" ]; then
        if printf '%s\n' "$listing" | grep -qiE "(^|/)${TARGET_DRIVER}(\.ko)?"; then
            ok "contains ${B}${TARGET_DRIVER}${Z} → will boot on this machine's controller"
        else
            bad "MISSING ${B}${TARGET_DRIVER}${Z} → this initrd will PANIC on this machine (unable to mount root)"
            VERDICT_BOOT=1
        fi
    fi
}

# ==========================================================================
printf '\n  %sRLX update package pre-flight%s\n' "$B" "$Z"
printf '  %s\n' "${DIM}────────────────────────────────────────────────${Z}"
[ -n "$TARGET_DRIVER" ] && inf "This machine's disk controller driver: ${B}${TARGET_DRIVER}${Z}" \
                        || warn "Could not detect this machine's disk controller (pass --driver NAME)."

VERDICT_BASE=0
VERDICT_BOOT=0
INITRD_CHECKED=0

if [ -n "$SINGLE_INITRD" ]; then
    printf '\n  %sInitrd check%s\n' "$B" "$Z"
    INITRD_CHECKED=1
    check_one_initrd "$SINGLE_INITRD"
else
    # 1. versions
    printf '\n  %sVersions%s\n' "$B" "$Z"
    basef="$(find "$SRC_DIR" -type f -name baseversion 2>/dev/null | head -1)"
    relf="$(find "$SRC_DIR" -type f -name releaseversion 2>/dev/null | head -1)"
    infof="$(find "$SRC_DIR" -type f -name upgrade.info 2>/dev/null | head -1)"
    base="$( [ -n "$basef" ] && cat "$basef" || echo '')"
    rel="$(  [ -n "$relf" ]  && cat "$relf"  || echo '')"
    [ -n "$rel" ]  && inf "installs (releaseversion): ${B}${rel}${Z}"  || warn "no releaseversion in package"
    [ -n "$base" ] && inf "requires base (baseversion): ${B}${base}${Z}" || inf "no baseversion (full/non-delta package — no base precondition)"

    if [ -n "$base" ] && [ -f "$PROJECTINFO" ]; then
        installed="$(cat "$PROJECTINFO")"
        inf "installed on this system:   ${B}${installed}${Z}"
        if [ "$base" = "$installed" ]; then ok "base matches installed → version precondition will PASS"
        else bad "base ≠ installed → upgrade will ABORT ('upgrade package is for version ${base}')"; VERDICT_BASE=1; fi
    fi

    # 2. initrd(s)
    printf '\n  %sInitrd / boot check%s\n' "$B" "$Z"
    mapfile -t initrds < <(find "$SRC_DIR" -type f \( -name '*.initrd' -o -name 'initrd*' -o -name 'initramfs*' \) 2>/dev/null)
    if [ "${#initrds[@]}" -eq 0 ]; then
        warn "No initrd file found in the package tree."
        inf "The initrd may be inside a kernel .deb (generated on-install) or a UKI."
        inf "If so, verify by inspecting the STAGED initrd after it lands:"
        inf "  lsinitramfs /boot/efi/EFI/rlx/*<newver>*.initrd | grep -i ${TARGET_DRIVER:-vmw_pvscsi}"
    else
        INITRD_CHECKED=1
        for f in "${initrds[@]}"; do check_one_initrd "$f"; done
    fi
fi

# ---- verdict --------------------------------------------------------------
printf '\n  %s\n' "${DIM}────────────────────────────────────────────────${Z}"
if [ "$VERDICT_BASE" -eq 0 ] && [ "$VERDICT_BOOT" -eq 0 ]; then
    if [ "$INITRD_CHECKED" -eq 1 ]; then
        ok "${B}Looks good.${Z} Base precondition ok and initrd supports this controller (${TARGET_DRIVER})."
    else
        warn "${B}Base ok, but the initrd was NOT inspected${Z} (not found in package)."
        inf "Confirm boot-safety on the STAGED initrd after it lands, or with --driver on the raw initrd."
    fi
    inf "Always take a VM snapshot before applying — belt and braces."
else
    [ "$VERDICT_BASE" -ne 0 ] && bad "Base mismatch — get the package whose baseversion matches this system."
    [ "$VERDICT_BOOT" -ne 0 ] && bad "Initrd will not boot this machine's controller (${TARGET_DRIVER}). Use a package whose initrd includes it, or match the VM controller to a driver it does contain."
    exit 1
fi
