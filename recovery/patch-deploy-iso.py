#!/usr/bin/env python3
"""patch-deploy-iso.py - make the Deploy option on a combined recovery ISO work.

Runs on WINDOWS (or Linux/macOS) with plain Python 3, no Linux tools needed.

Problem it fixes: the vendor cobas installer only accepts an install medium
whose volume label starts with "MLR:" (installer_init: `blkid | grep MLR:`).
The combined recovery stick has to keep SystemRescue's label (e.g. RESCUE1302),
so on that stick the installer falls back to a network install, finds no
network and stops at a BusyBox shell ("Downloading install medium ... No network
interface found").

What it does: takes an rlx-recovery ISO that was built with --deploy-iso (it has
/initrd.img + /image.cpio.gz at its root), and writes a COPY in which every copy
of that check in the installer's initrd (installer-hooks.sh.inc AND
scripts/init-premount/installer) also accepts this ISO's own label. Nothing
else changes: the kernel, the disk image, the boot menu and the label stay the
same. The patched initrd goes back in its original place in the ISO; if it has
grown too big for that, it is appended at the end of the ISO instead (the ISO's
partition is extended to cover it). It also works on an ISO made by an older
version of this script that patched only the first check.

    py patch-deploy-iso.py rlx-recovery.iso
    py patch-deploy-iso.py rlx-recovery.iso --out D:\\stick.iso
    py patch-deploy-iso.py rlx-recovery.iso --skip-display   (VM testing only)

The output name always contains "customized". Flash it with Rufus in
"DD Image mode" (or balenaEtcher) and do NOT change the label in Rufus.

If the installer initrd is zstd-compressed you need Python 3.14 or newer
(python.org); older versions can only read gzip/xz/bzip2 initrds.
"""

import argparse, bz2, lzma, os, re, shutil, struct, sys, zlib

try:                                    # Python 3.14+ ships zstd in the stdlib
    from compression import zstd as _zstd
except ImportError:
    _zstd = None

SECTOR = 2048
MARK_MEDIUM = b"CUSTOMIZED: also accept the recovery stick"
MARK_DISPLAY = b"CUSTOMIZED: skip display-resolution probe"
HOOKS_SUFFIX = b"scripts/installer-hooks.sh.inc"


def ok(m): print("  [ok] " + m)
def inf(m): print("  [..] " + m)
def die(m, code=1):
    print("  [!!] " + m, file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- ISO 9660 ---
def read_at(f, off, n):
    f.seek(off)
    return f.read(n)


def iso_pvd(f):
    """Return (volume_id, root_extent, root_size) of the primary volume descriptor."""
    for s in range(16, 64):
        vd = read_at(f, s * SECTOR, SECTOR)
        if vd[1:6] != b"CD001":
            break
        if vd[0] == 1:
            if struct.unpack_from("<H", vd, 128)[0] != SECTOR:
                die("Unsupported ISO block size.")
            vol = vd[40:72].decode("ascii", "replace").strip()
            root = vd[156:190]
            return vol, struct.unpack_from("<I", root, 2)[0], struct.unpack_from("<I", root, 10)[0]
        if vd[0] == 255:
            break
    die("Not an ISO 9660 image (no primary volume descriptor).")


def iso_name(rec):
    """Rock Ridge (long) name if present, else the plain ISO 9660 name; upper case."""
    nl = rec[32]
    i = 33 + nl + (1 - nl % 2)            # system-use area (after a pad byte)
    while i + 4 <= len(rec):
        sig, ln = rec[i:i + 2], rec[i + 2]
        if ln < 4:
            break
        if sig == b"NM" and ln > 5 and not rec[i + 4] & 0x6:
            return rec[i + 5:i + ln].decode("utf-8", "replace").upper()
        i += ln
    n = rec[33:33 + nl].decode("ascii", "replace").upper()
    return n.split(";")[0].rstrip(".")


def iso_root_files(f, extent, size):
    """{NAME: (extent, size)} for the files in the root directory."""
    out, data = {}, read_at(f, extent * SECTOR, size)
    i = 0
    while i < len(data):
        ln = data[i]
        if ln == 0:                       # records never cross a sector boundary
            i = (i // SECTOR + 1) * SECTOR
            continue
        rec = data[i:i + ln]
        if rec[32] > 1 or rec[33] > 1:   # skip "." and ".."
            out[iso_name(rec)] = (struct.unpack_from("<I", rec, 2)[0],
                                  struct.unpack_from("<I", rec, 10)[0])
        i += ln
    return out


def find_size_records(path, old_size):
    """Offsets of every directory record (ISO9660, Joliet, and the extra
    partition-relative tree xorriso may add) that describes the initrd.
    Found by its both-endian size field, then validated."""
    pat = struct.pack("<I", old_size) + struct.pack(">I", old_size)
    hits, chunk, keep = [], 64 << 20, 512
    with open(path, "rb") as f:
        base, prev = 0, b""
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            data = prev + buf
            start = base - len(prev)
            last = len(buf) < chunk
            j = data.find(pat)
            while j != -1:
                rec_off = start + j - 10
                # a record cut off at the chunk end is seen again in the next chunk
                whole = last or j - 10 + 255 <= len(data)
                if j >= 10 and whole and rec_off not in hits:
                    rec = data[j - 10:j - 10 + 255]
                    if (len(rec) >= 34 and 34 <= rec[0] <= 255
                            and rec[2:6] == rec[6:10][::-1]
                            and 33 + rec[32] <= rec[0]):
                        name = rec[33:33 + rec[32]]
                        if (b"INITRD" in name.upper()
                                or "initrd" in name.decode("utf-16-be", "ignore").lower()):
                            hits.append(rec_off)
                j = data.find(pat, j + 1)
            prev = data[-keep:]
            base += len(buf)
    return hits


# ------------------------------------------------------------ initrd/cpio ---
def detect(buf):
    if buf[:2] == b"\x1f\x8b":
        return "gzip"
    if buf[:6] == b"\xfd7zXZ\x00":
        return "xz"
    if buf[:4] == b"\x28\xb5\x2f\xfd":
        return "zstd"
    if buf[:3] == b"BZh":
        return "bzip2"
    if buf[:4] == b"\x02\x21\x4c\x18":
        return "lz4"
    if buf[:3] == b"\x5d\x00\x00":
        return "lzma"
    return None


def decompress_one(fmt, buf):
    """Decompress ONE stream at the start of buf -> (raw, bytes_consumed)."""
    if fmt == "gzip":
        d = zlib.decompressobj(31)
        raw = d.decompress(buf)
    elif fmt == "xz":
        d = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        raw = d.decompress(buf)
    elif fmt == "bzip2":
        d = bz2.BZ2Decompressor()
        raw = d.decompress(buf)
    elif fmt == "zstd":
        if _zstd is None:
            die("This installer initrd is zstd-compressed. Install Python 3.14 or newer "
                "from python.org (it can read zstd) and run this again.")
        d = _zstd.ZstdDecompressor()
        raw = d.decompress(buf)
    else:
        die("Initrd compression '%s' is not supported by this script." % fmt)
    if not d.eof:
        die("The installer initrd's %s data is truncated." % fmt)
    return raw, len(buf) - len(d.unused_data)


def compress(fmt, raw):
    if fmt == "gzip":
        c = zlib.compressobj(9, zlib.DEFLATED, 31)
        return c.compress(raw) + c.flush()
    if fmt == "xz":                       # what the kernel's xz decoder accepts
        return lzma.compress(raw, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC32,
                             filters=[{"id": lzma.FILTER_LZMA2,
                                       "preset": 9 | lzma.PRESET_EXTREME,
                                       "dict_size": 32 << 20}])
    if fmt == "bzip2":
        return bz2.compress(raw, 9)
    if fmt == "zstd" and _zstd is not None:
        return _zstd.compress(raw, level=19)
    return None


def a4(n):
    return (n + 3) & ~3


def cpio_end(buf, i):
    """Offset just past the TRAILER!!! entry of the newc archive at buf[i:]."""
    while True:
        if buf[i:i + 5] != b"07070":
            die("Malformed cpio archive in the installer initrd.")
        namesize = int(buf[i + 94:i + 102], 16)
        filesize = int(buf[i + 54:i + 62], 16)
        name = buf[i + 110:i + 110 + namesize - 1]
        i = a4(a4(i + 110 + namesize) + filesize)
        if name == b"TRAILER!!!":
            return i


def cpio_edit(raw, edit):
    """Run edit(name, data) -> data on every file in the (possibly concatenated)
    newc archives in raw. Changed files are rewritten; everything else stays
    byte-for-byte the same. Returns the new raw."""
    out, i, last = [], 0, 0
    while i < len(raw):
        if raw[i] == 0:
            i += 1
            continue
        if raw[i:i + 5] != b"07070":
            break
        hdr = raw[i:i + 110]
        fields = [int(hdr[6 + 8 * k:14 + 8 * k], 16) for k in range(13)]
        namesize, filesize = fields[11], fields[6]
        name = raw[i + 110:i + 110 + namesize - 1]
        dstart = a4(i + 110 + namesize)
        nxt = a4(dstart + filesize)
        if filesize:
            data = raw[dstart:dstart + filesize]
            new = edit(name, data)
            if new != data:
                fields[6] = len(new)
                if hdr[:6] == b"070702":  # "crc" format: simple byte sum
                    fields[12] = sum(new) & 0xFFFFFFFF
                newhdr = hdr[:6] + b"".join(b"%08X" % v for v in fields)
                body = newhdr + raw[i + 110:dstart] + new
                body += b"\0" * (a4(len(body)) - len(body))
                out += [raw[last:i], body]
                last = nxt
        i = nxt
    out.append(raw[last:])
    return b"".join(out)


# ------------------------------------------------------------- the patch ----
# The installer looks for its medium with this line in TWO places:
# scripts/installer-hooks.sh.inc (installer_init) and scripts/init-premount/installer.
# Every copy is patched.
MEDIUM_OLD = b"blkid | grep MLR:`"


class Editor:
    def __init__(self, label, skip_display):
        self.new = (b"blkid | grep -E 'MLR:|LABEL=\"" + label.encode() + b"\"'` # "
                    + MARK_MEDIUM)
        self.skip_display = skip_display
        self.hooks_seen = False
        self.patched = []                 # names of files that carry the patch

    def __call__(self, name, text):
        if MEDIUM_OLD in text:
            text = text.replace(MEDIUM_OLD, self.new)
        if MARK_MEDIUM in text:
            self.patched.append(name.decode("utf-8", "replace"))
        if name.endswith(HOOKS_SUFFIX):
            self.hooks_seen = True
            if self.skip_display and MARK_DISPLAY not in text:
                text, n = re.subn(
                    rb"(?m)^.*EXTRA_INSTALLER_CONFIGURE_DEVICE_RESOLUTION.*!= *\"no\".*$",
                    b"if false ; then # " + MARK_DISPLAY + b" (no GPU in VM)", text)
                if n != 1:
                    die("The installer's display step was not found - cannot --skip-display.")
                text = re.sub(rb"(?m)^([ \t]*)stty cols \$cols_orig(.*)$",
                              rb'\1[ -z "$cols_orig" ] || stty cols $cols_orig\2', text)
                text = re.sub(rb"(?m)^([ \t]*)stty cols \$cols$",
                              rb'\1[ -z "$cols" ] || stty cols $cols', text)
        return text


def patch_initrd(initrd, ed, room):
    """Return a patched initrd no bigger than `room` bytes, or None if it
    already carries every patch."""
    segs, i = [], 0                       # [bytes, fmt, raw]
    while i < len(initrd):
        if initrd[i] == 0:
            j = i
            while j < len(initrd) and initrd[j] == 0:
                j += 1
            segs.append([initrd[i:j], None, None])
            i = j
        elif initrd[i:i + 5] == b"07070":
            j = cpio_end(initrd, i)
            segs.append([initrd[i:j], "uncompressed", initrd[i:j]])
            i = j
        else:
            fmt = detect(initrd[i:i + 8])
            if fmt is None:
                die("Unrecognised data inside the installer initrd.")
            raw, used = decompress_one(fmt, initrd[i:])
            segs.append([initrd[i:i + used], fmt, raw])
            i += used

    changed = []
    for k, s in enumerate(segs):
        if s[2] is not None:
            new_raw = cpio_edit(s[2], ed)
            if new_raw != s[2]:
                changed.append((k, new_raw))
    if not ed.hooks_seen:
        die("installer-hooks.sh.inc was not found in the installer initrd - is this a "
            "recovery ISO built with --deploy-iso?")
    if not ed.patched:
        die("The installer's medium detection (blkid | grep MLR:) was not found - "
            "unexpected installer version. Nothing was changed.")
    if not changed:
        return None                       # already fully patched

    for k, new_raw in changed:
        fmt = segs[k][1]
        if fmt == "uncompressed":
            segs[k][0] = new_raw
            continue
        inf("Recompressing the installer initrd (can take a minute or two) ...")
        rest = sum(len(t[0]) for n, t in enumerate(segs) if n != k)
        first = None                      # same format as the vendor used
        for f in [fmt] + [x for x in ("xz",) if x != fmt]:
            blob = compress(f, new_raw)
            if blob is None:
                continue
            first = first or blob
            if rest + len(blob) <= room:
                if f != fmt:
                    inf("Repacked as %s (was %s) so it fits in the same place." % (f, fmt))
                break
        else:
            blob = first                  # will not fit in place: keep the format
        segs[k][0] = blob
    out = b"".join(t[0] for t in segs)
    return out, len(out) <= room


def tree_bases(f, recs, ext):
    """Block offset of each directory tree that lists the initrd: 0 for the
    normal tree, N for a partition-relative tree (xorriso -partition_offset)."""
    return sorted({ext - struct.unpack_from("<I", read_at(f, r + 2, 4))[0] for r in recs})


def mbr_grow_plan(f, bases, new_end):
    """Moving the initrd past the end of the image means the MBR partition that
    holds the ISO filesystem must grow to cover it (the installer reads the
    medium through that partition, e.g. /dev/sda1). Returns [(offset, bytes)]."""
    mbr = read_at(f, 0, 512)
    if mbr[510:512] != b"\x55\xaa":
        return []                         # plain CD image: no partition table
    writes = []
    for k in range(4):
        e = 446 + 16 * k
        ptype = mbr[e + 4]
        start = struct.unpack_from("<I", mbr, e + 8)[0]
        if ptype == 0xEE:
            die("This ISO uses a GPT layout, which this script cannot extend. "
                "Build the stick with build-recovery-iso.sh on Linux/WSL instead.")
        if ptype not in (0, 0xEF) and start * 512 in [b * SECTOR for b in bases]:
            writes.append((e + 12, struct.pack("<I", new_end // 512 - start)))
    if not writes:
        die("Could not find the ISO's partition to extend. Build the stick with "
            "build-recovery-iso.sh on Linux/WSL instead.")
    return writes


# ------------------------------------------------------------------ main ----
def main():
    ap = argparse.ArgumentParser(description="Make Deploy work on a combined recovery ISO.")
    ap.add_argument("iso", help="rlx-recovery ISO built with --deploy-iso")
    ap.add_argument("--out", help="output ISO (name always gets 'customized')")
    ap.add_argument("--skip-display", action="store_true",
                    help="also skip the installer's display step (VM testing only)")
    a = ap.parse_args()

    src = a.iso
    if not os.path.isfile(src):
        die("File not found: %s" % src, 2)
    stem = os.path.splitext(src)[0]
    if a.out:
        out = a.out
    elif "customized" in os.path.basename(stem).lower():
        out = stem + "-new.iso"           # re-patching an older customized ISO
    else:
        out = stem + "-deploy-customized.iso"
    if "customized" not in os.path.basename(out).lower():
        out = os.path.splitext(out)[0] + "-deploy-customized.iso"
    if os.path.abspath(out) == os.path.abspath(src):
        die("--out must be a different file than the input.", 2)

    with open(src, "rb") as f:
        label, rext, rsize = iso_pvd(f)
        files = iso_root_files(f, rext, rsize)
        if label.startswith("MLR:"):
            die("This is a vendor installer ISO (label %s). It needs no patch: flash it "
                "as-is with Rufus in DD Image mode." % label, 2)
        for n in ("INITRD.IMG", "VMLINUZ", "IMAGE.CPIO.GZ"):
            if n not in files:
                die("/%s not found: this ISO has no Deploy option. Build it with "
                    "build-recovery-iso.sh --deploy-iso first." % n.lower(), 2)
        ext, size = files["INITRD.IMG"]
        initrd = read_at(f, ext * SECTOR, size)
    ok("Recovery ISO, label %s, Deploy payload present." % label)

    room = (size + SECTOR - 1) // SECTOR * SECTOR
    ed = Editor(label, a.skip_display)
    res = patch_initrd(initrd, ed, room)
    if res is None:
        ok("This ISO is already patched - nothing to do. Flash it in DD Image mode.")
        return
    new, fits = res

    iso_size = os.path.getsize(src)
    need = iso_size + len(new) + (64 << 20)
    free = shutil.disk_usage(os.path.dirname(os.path.abspath(out))).free
    if free < need:
        die("Not enough free space for the copy: need ~%d MB, have %d MB." %
            (need >> 20, free >> 20), 2)
    recs = find_size_records(src, size)
    if not recs:
        die("Could not locate the initrd's directory entries in the ISO.")

    # Where the patched initrd goes: its old place if it fits, else appended
    # at the end of the image (its directory entries are pointed there).
    if fits:
        new_ext = ext
        writes = []
    else:
        new_ext = (iso_size + SECTOR - 1) // SECTOR
        new_end = (new_ext * SECTOR + len(new) + SECTOR - 1) // SECTOR * SECTOR
        with open(src, "rb") as f:
            bases = tree_bases(f, recs, ext)
            writes = mbr_grow_plan(f, bases, new_end)
            for b in bases:               # volume size in every descriptor
                for s in range(16, 64):
                    vd = read_at(f, (b + s) * SECTOR, 8)
                    if vd[1:6] != b"CD001" or vd[0] == 255:
                        break
                    if vd[0] in (1, 2):
                        n = new_end // SECTOR - b
                        writes.append(((b + s) * SECTOR + 80,
                                       struct.pack("<I", n) + struct.pack(">I", n)))
        inf("The patched initrd is larger than the original slot; "
            "moving it to the end of the ISO.")

    with open(src, "rb") as f:            # tree offset of each directory entry
        rec_base = {r: ext - struct.unpack_from("<I", read_at(f, r + 2, 4))[0] for r in recs}

    inf("Writing %s ..." % os.path.basename(out))
    shutil.copyfile(src, out)
    try:
        with open(out, "r+b") as f:
            if fits:
                f.seek(ext * SECTOR)
                f.write(new + b"\0" * (room - len(new)))
            else:
                f.seek(new_ext * SECTOR)
                f.write(new + b"\0" * (new_end - new_ext * SECTOR - len(new)))
            for r, b in rec_base.items():
                rel = new_ext - b
                f.seek(r + 2)
                f.write(struct.pack("<I", rel) + struct.pack(">I", rel)
                        + struct.pack("<I", len(new)) + struct.pack(">I", len(new)))
            for off, data in writes:
                f.seek(off)
                f.write(data)
        # read it back through EVERY directory entry and check the patch is there
        with open(out, "rb") as f:
            _, rext2, rsize2 = iso_pvd(f)
            ext2, size2 = iso_root_files(f, rext2, rsize2)["INITRD.IMG"]
            for r, b in rec_base.items():
                e2 = struct.unpack_from("<I", read_at(f, r + 2, 4))[0]
                s2 = struct.unpack_from("<I", read_at(f, r + 10, 4))[0]
                if e2 + b != new_ext or s2 != len(new):
                    raise RuntimeError("directory entry check failed")
            back = read_at(f, ext2 * SECTOR, size2)
        if back != new or patch_initrd(back, Editor(label, a.skip_display), room) is not None:
            raise RuntimeError("verification failed")
    except BaseException as e:
        try:
            os.remove(out)
        except OSError:
            pass
        die("Writing the patched ISO failed (%s); the output was removed." % e)

    ok("Installer now also accepts the label %s in: %s" % (label, ", ".join(ed.patched)))
    inf("%d ISO directory entries updated." % len(recs))
    if a.skip_display:
        print("  [!!] --skip-display: FOR VM TESTING ONLY, not for a real instrument.")
    ok("Built %s" % out)
    print("\n  Flash it with Rufus -> 'DD Image mode' (or balenaEtcher).")
    print("  Do NOT change the volume label in Rufus.\n")


if __name__ == "__main__":
    main()
