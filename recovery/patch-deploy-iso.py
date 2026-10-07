#!/usr/bin/env python3
"""patch-deploy-iso.py - update an existing combined recovery ISO, no Linux needed.

Runs on WINDOWS (or Linux/macOS) with plain Python 3.

It writes a COPY of an rlx-recovery ISO (built with --deploy-iso) with:

1. Deploy fixed. The vendor cobas installer only accepts a medium whose label
   starts with "MLR:" (`blkid | grep MLR:`, in installer-hooks.sh.inc AND
   scripts/init-premount/installer). This stick must keep SystemRescue's label
   (e.g. RESCUE1302), so without the fix the installer reports "could not find
   install medium" or tries a network install. Every copy of that check is
   patched to also accept this ISO's own label.
2. The current boot menu: one entry that opens the recovery screen (Deploy
   is no longer in the boot menu), with GRUB's header / "press e to edit" help
   / countdown hidden.
3. The current recovery screen and text menu (factory-reset-gui.py and
   factory-reset-menu.sh from this folder): Roche ID + token sign-in, then
   Factory Reset or Deploy, with Deploy only for an approved image SHA-256.
It also reports whether the image on the stick is approved.

The kernel, the disk image and the volume label are untouched. Each changed
file goes back in its original place in the ISO, or, if it grew too big, at the
end of the ISO (the ISO's partition is extended to cover it). Safe to run again
on its own output or on an ISO from an older version of this script.

    py patch-deploy-iso.py rlx-recovery.iso
    py patch-deploy-iso.py rlx-recovery.iso --out D:\\stick.iso
    py patch-deploy-iso.py rlx-recovery.iso --skip-display   (VM testing only)

The output name always contains "customized". Flash it with Rufus in
"DD Image mode" (or balenaEtcher) and do NOT change the label in Rufus.

If the installer initrd is zstd-compressed you need Python 3.14 or newer
(python.org); older versions can only read gzip/xz/bzip2 initrds.
"""

import argparse, bz2, hashlib, lzma, os, re, shutil, struct, sys, zlib

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


def iso_dir(f, extent, size):
    """{NAME: (extent, size, is_dir)} for one directory."""
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
                                  struct.unpack_from("<I", rec, 10)[0],
                                  bool(rec[25] & 2))
        i += ln
    return out


def iso_lookup(f, path):
    """(extent, size) of /a/b/c in the primary tree, or None."""
    _, ext, size = iso_pvd(f)
    for part in path.strip("/").upper().split("/"):
        hit = iso_dir(f, ext, size).get(part)
        if hit is None:
            return None
        ext, size, _ = hit
    return ext, size


def find_records(path, targets):
    """For each (extent, size) in targets: offsets of every directory record
    that describes that file - in the ISO 9660/Rock Ridge tree, the Joliet tree
    and any partition-relative tree xorriso added. A record matches when its
    both-endian size equals the file's and its extent equals the file's minus a
    small tree offset."""
    pats = {struct.pack("<I", s) + struct.pack(">I", s): (e, s) for e, s in targets}
    hits = {t: [] for t in targets}
    chunk, keep = 64 << 20, 512
    with open(path, "rb") as f:
        base, prev = 0, b""
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            data = prev + buf
            start = base - len(prev)
            last = len(buf) < chunk
            for pat, (ext, size) in pats.items():
                j = data.find(pat)
                while j != -1:
                    rec_off = start + j - 10
                    # a record cut off at the chunk end is seen again next chunk
                    whole = last or j - 10 + 255 <= len(data)
                    if j >= 10 and whole and rec_off not in hits[(ext, size)]:
                        rec = data[j - 10:j - 10 + 255]
                        e_rec = struct.unpack_from("<I", rec, 2)[0]
                        if (len(rec) >= 34 and 34 <= rec[0] <= 255
                                and rec[2:6] == rec[6:10][::-1]
                                and 33 + rec[32] <= rec[0]
                                and not rec[25] & 2
                                and 0 <= ext - e_rec < 4096):
                            hits[(ext, size)].append(rec_off)
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


def mbr_grow_plan(f, bases, new_end):
    """Moving the initrd past the end of the image means the MBR partition that
    holds the ISO filesystem must grow to cover it (the installer reads the
    medium through that partition, e.g. /dev/sda1). Returns [(offset, bytes)]."""
    mbr = read_at(f, 0, 512)
    if mbr[510:512] != b"\x55\xaa":
        return []                         # plain CD image: no partition table
    writes, table = [], []
    for k in range(4):
        e = 446 + 16 * k
        ptype = mbr[e + 4]
        start, count = struct.unpack_from("<II", mbr, e + 8)
        table.append("%d: type %#04x start %d sectors %d" % (k + 1, ptype, start, count))
        if ptype == 0xEE:
            die("This ISO uses a GPT layout, which this script cannot extend. "
                "Build the stick with build-recovery-iso.sh on Linux/WSL instead.")
        # The ISO partition starts where one of the directory trees starts. Its
        # type may be 0x00: isohybrid images (SystemRescue, Arch) mark it so, and
        # Linux still uses it (e.g. /dev/sda1). Never the EFI partition.
        if count and ptype != 0xEF and start * 512 in [b * SECTOR for b in bases]:
            writes.append((e + 12, struct.pack("<I", new_end // 512 - start)))
    if not writes:
        die("Could not find the ISO's partition to extend (tree offsets %s; "
            "partitions %s). Build the stick with build-recovery-iso.sh on "
            "Linux/WSL instead." % (bases, "; ".join(table)))
    return writes


# ------------------------------------------------------- boot menu (GRUB) ----
MARK_GRUB = "# RLX: GRUB help text hidden"


def _drop_block(cfg, start):
    """Remove the brace block starting at index `start` (and its line)."""
    i = cfg.index("{", start)
    depth = 0
    for j in range(i, len(cfg)):
        if cfg[j] == "{":
            depth += 1
        elif cfg[j] == "}":
            depth -= 1
            if depth == 0:
                end = cfg.find("\n", j)
                return cfg[:start] + cfg[(end + 1 if end != -1 else len(cfg)):]
    return cfg


def grub_edit(cfg, label):
    """Bring an older grubsrcd.cfg to the current boot menu: one entry that
    opens the recovery screen (Deploy now lives there, behind the sign-in),
    and GRUB's header / "press e to edit" help / countdown hidden."""
    m = re.search(r"(?m)^submenu 'Deploy [^']*' \{", cfg)
    if m:
        cfg = _drop_block(cfg, m.start())
        cfg = re.sub(r"(?m)^(\s*set timeout=)30\s*$", r"\g<1>2", cfg)
    cfg = re.sub(r"(?m)^menuentry 'Start Factory Reset' \{",
                 "menuentry '%s' {" % label.replace("'", ""), cfg)
    # The logo picture: GRUB shows it at 1024x768, which the instrument's
    # 1920x1080 panel scales or stretches out of shape. Plain white instead (the
    # logo is on the recovery screen).
    white = "background_image" in cfg or "color_normal=white/white" in cfg
    if "background_image" in cfg:
        cfg = re.sub(r"(?m)^[ \t]*insmod png[ \t]*\n", "", cfg)
        cfg = re.sub(r"(?m)^[ \t]*background_image[^\n]*\n", "", cfg)
        cfg = re.sub(r"set color_normal=\S+", "set color_normal=white/white", cfg, count=1)
    if MARK_GRUB not in cfg and "export color_normal" not in cfg:
        # GRUB draws its header, the "press e to edit" help and the countdown in
        # color_normal; make that the background colour.
        hide = "" if white else "\t\tset color_normal=black/black\n"
        cfg, n = re.subn(r"(?m)^(\s*terminal_output gfxterm\s*\n(?:.*\n)*?)(\s*fi\s*\n)",
                         lambda x: x.group(1) + hide + "\t\texport color_normal "
                         "menu_color_normal menu_color_highlight  " + MARK_GRUB + "\n"
                         + x.group(2), cfg, count=1)
        if n != 1:
            inf("Boot menu layout not recognised; GRUB help text left as is.")
    return cfg


def approved_images(gui_path):
    """{sha256: name} from APPROVED_IMAGES in factory-reset-gui.py."""
    try:
        txt = open(gui_path, encoding="utf-8").read()
    except OSError:
        return {}
    block = re.search(r"APPROVED_IMAGES\s*=\s*\{(.*?)\n\}", txt, re.S)
    return dict(re.findall(r'"([0-9a-f]{64})"\s*:\s*\n?\s*"([^"]*)"', block.group(1))) if block else {}


# ------------------------------------------------------------------ main ----
def main():
    ap = argparse.ArgumentParser(description="Update a combined recovery ISO (Deploy fix, "
                                 "boot menu, Factory Reset screen).")
    ap.add_argument("iso", help="rlx-recovery ISO built with --deploy-iso")
    ap.add_argument("--out", help="output ISO (name always gets 'customized')")
    ap.add_argument("--label", default="cobas 6800 Recovery",
                    help='boot-menu entry text (default: "cobas 6800 Recovery")')
    ap.add_argument("--logo", help="replace the recovery-screen logo with this PNG "
                    "(at least ~100px tall)")
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
        out = stem + "-new.iso"           # updating an older customized ISO
    else:
        out = stem + "-deploy-customized.iso"
    if "customized" not in os.path.basename(out).lower():
        out = os.path.splitext(out)[0] + "-deploy-customized.iso"
    if os.path.abspath(out) == os.path.abspath(src):
        die("--out must be a different file than the input.", 2)

    # Every change is (ISO path, extent, size, new bytes, description).
    changes = []
    with open(src, "rb") as f:
        label, _, _ = iso_pvd(f)
        if label.startswith("MLR:"):
            die("This is a vendor installer ISO (label %s). It needs no patch: flash it "
                "as-is with Rufus in DD Image mode." % label, 2)
        for n in ("/initrd.img", "/vmlinuz", "/image.cpio.gz"):
            if iso_lookup(f, n) is None:
                die("%s not found: this ISO has no Deploy option. Build it with "
                    "build-recovery-iso.sh --deploy-iso first." % n, 2)
        ok("Recovery ISO, label %s, Deploy payload present." % label)

        # 1. installer initrd: accept this stick's label
        ext, size = iso_lookup(f, "/initrd.img")
        ed = Editor(label, a.skip_display)
        res = patch_initrd(read_at(f, ext * SECTOR, size), ed,
                           (size + SECTOR - 1) // SECTOR * SECTOR)
        if res is None:
            ok("Installer already accepts this stick.")
        else:
            changes.append(("/initrd.img", ext, size, res[0],
                            "installer accepts label %s (%s)" % (label, ", ".join(ed.patched))))

        # 2. boot menu wording + hidden GRUB help
        hit = iso_lookup(f, "/boot/grub/grubsrcd.cfg")
        if hit:
            cfg = read_at(f, hit[0] * SECTOR, hit[1])
            new = grub_edit(cfg.decode("utf-8"), a.label).encode("utf-8")
            if new != cfg:
                changes.append(("/boot/grub/grubsrcd.cfg", hit[0], hit[1], new,
                                "boot menu: one entry '%s'; Deploy moved behind the "
                                "sign-in" % a.label))
        else:
            inf("No branded boot menu in this ISO; menu left as is.")

        # 3. recovery screen (sign-in, Factory Reset, Deploy) and text menu,
        #    both taken from this folder
        here = os.path.dirname(os.path.abspath(__file__))
        for name, what in (("factory-reset-gui.py", "recovery screen (sign-in, Factory "
                            "Reset, Deploy) updated"),
                           ("factory-reset-menu.sh", "text menu updated (sign-in required)")):
            path = os.path.join(here, name)
            hit = iso_lookup(f, "/autorun/" + name)
            if not os.path.isfile(path):
                die("%s is missing next to this script; download the whole recovery "
                    "folder again." % name, 2)
            if hit:
                new = open(path, "rb").read().replace(b"\r\n", b"\n")
                if new != read_at(f, hit[0] * SECTOR, hit[1]):
                    changes.append(("/autorun/" + name, hit[0], hit[1], new, what))

        # 4. recovery-screen logo: report its size; optionally replace it
        hit = iso_lookup(f, "/autorun/brand-logo.png")
        if hit:
            head = read_at(f, hit[0] * SECTOR, 24)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = struct.unpack(">II", head[16:24])
                inf("Logo on the stick: %dx%d px%s." % (w, h, " (small: may look soft)"
                                                         if h < 92 else ""))
        if a.logo:
            data = open(a.logo, "rb").read()
            if data[:8] != b"\x89PNG\r\n\x1a\n":
                die("--logo must be a PNG file.", 2)
            w, h = struct.unpack(">II", data[16:24])
            if not hit:
                die("This ISO has no logo to replace (it was built without --logo).", 2)
            if h < 92:
                print("  [!!] The new logo is only %dpx tall; it may look soft." % h)
            changes.append(("/autorun/brand-logo.png", hit[0], hit[1], data,
                            "logo replaced (%dx%d px)" % (w, h)))

        # 5. is the image on the stick an approved one?
        approved = approved_images(os.path.join(here, "factory-reset-gui.py"))
        ext, size = iso_lookup(f, "/image.cpio.gz")
        inf("Checking the image SHA-256 (reads %d MB) ..." % (size >> 20))
        h = hashlib.sha256()
        f.seek(ext * SECTOR)
        left = size
        while left:
            b = f.read(min(left, 8 << 20))
            if not b:
                break
            h.update(b)
            left -= len(b)
        img_sha = h.hexdigest()
        if img_sha in approved:
            ok("Image %s is approved (%s)." % (img_sha, approved[img_sha]))
        else:
            print("  [!!] Image %s is NOT in APPROVED_IMAGES (factory-reset-gui.py): "
                  "the stick will refuse to deploy it." % img_sha)

    if not changes:
        ok("This ISO is already up to date - nothing to do. Flash it in DD Image mode.")
        return

    iso_size = os.path.getsize(src)
    need = iso_size + sum(len(c[3]) for c in changes) + (64 << 20)
    free = shutil.disk_usage(os.path.dirname(os.path.abspath(out))).free
    if free < need:
        die("Not enough free space for the copy: need ~%d MB, have %d MB." %
            (need >> 20, free >> 20), 2)

    # Plan where each file goes: its old place if it fits, else the image end.
    recs = find_records(src, [(c[1], c[2]) for c in changes])
    end = (iso_size + SECTOR - 1) // SECTOR
    plan, writes = [], []                 # plan: (path, rec_base, new_ext, data, room)
    with open(src, "rb") as f:
        for path, ext, size, data, _ in changes:
            if not recs[(ext, size)]:
                die("Could not locate the directory entries of %s in the ISO." % path)
            rec_base = {r: ext - struct.unpack_from("<I", read_at(f, r + 2, 4))[0]
                        for r in recs[(ext, size)]}
            room = (size + SECTOR - 1) // SECTOR * SECTOR
            if len(data) <= room:
                plan.append((path, rec_base, ext, data, room))
            else:
                room = (len(data) + SECTOR - 1) // SECTOR * SECTOR
                plan.append((path, rec_base, end, data, room))
                inf("%s grew; moving it to the end of the ISO." % path)
                end += room // SECTOR
        if end * SECTOR > iso_size:       # something was appended
            bases = sorted({b for _, rb, _, _, _ in plan for b in rb.values()})
            writes = mbr_grow_plan(f, bases, end * SECTOR)
            for b in bases:               # volume size in every descriptor
                for s in range(16, 64):
                    vd = read_at(f, (b + s) * SECTOR, 8)
                    if vd[1:6] != b"CD001" or vd[0] == 255:
                        break
                    if vd[0] in (1, 2):
                        n = end - b
                        writes.append(((b + s) * SECTOR + 80,
                                       struct.pack("<I", n) + struct.pack(">I", n)))

    inf("Writing %s ..." % os.path.basename(out))
    shutil.copyfile(src, out)
    try:
        with open(out, "r+b") as f:
            for path, rec_base, new_ext, data, room in plan:
                f.seek(new_ext * SECTOR)
                f.write(data + b"\0" * (room - len(data)))
                for r, b in rec_base.items():
                    f.seek(r + 2)
                    f.write(struct.pack("<I", new_ext - b) + struct.pack(">I", new_ext - b)
                            + struct.pack("<I", len(data)) + struct.pack(">I", len(data)))
            for off, data in writes:
                f.seek(off)
                f.write(data)
        # read every changed file back through every one of its directory entries
        with open(out, "rb") as f:
            for path, rec_base, new_ext, data, _ in plan:
                for r, b in rec_base.items():
                    e2 = struct.unpack_from("<I", read_at(f, r + 2, 4))[0]
                    s2 = struct.unpack_from("<I", read_at(f, r + 10, 4))[0]
                    if e2 + b != new_ext or s2 != len(data):
                        raise RuntimeError("directory entry check failed for " + path)
                hit = iso_lookup(f, path)
                if hit is None or read_at(f, hit[0] * SECTOR, hit[1]) != data:
                    raise RuntimeError("read-back failed for " + path)
            back = read_at(f, *(lambda h: (h[0] * SECTOR, h[1]))(iso_lookup(f, "/initrd.img")))
        if patch_initrd(back, Editor(label, a.skip_display), len(back) + SECTOR) is not None:
            raise RuntimeError("installer patch verification failed")
    except BaseException as e:
        try:
            os.remove(out)
        except OSError:
            pass
        die("Writing the updated ISO failed (%s); the output was removed." % e)

    for c in changes:
        ok(c[4])
    if a.skip_display:
        print("  [!!] --skip-display: FOR VM TESTING ONLY, not for a real instrument.")
    ok("Built %s" % out)
    print("\n  Flash it with Rufus -> 'DD Image mode' (or balenaEtcher).")
    print("  Do NOT change the volume label in Rufus.\n")


if __name__ == "__main__":
    main()
