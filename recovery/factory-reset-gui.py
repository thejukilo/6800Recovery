#!/usr/bin/env python3
# factory-reset-gui.py - cobas 6800 recovery screen (GTK) for the recovery USB.
#
# Runs fullscreen under X on the SystemRescue recovery stick. White background,
# logo top-right, plain wording.
#
#   1. Sign in with a Roche ID + Roche (FSR) token. The token is checked by the
#      instrument's OWN login module (pam_fsr, the same check as a service login
#      on the instrument), run in a throw-away copy of the instrument's system:
#      from the instrument disk, or, if the disk has no usable system, from the
#      image on this stick. Nothing is written to the instrument for this.
#   2. Choose: Factory Reset, or Deploy <image>.
#   3. Factory Reset arms the same /rlx-boot flag the text menu writes; the
#      instrument performs the reset on its next boot. It REFUSES unless it
#      finds an RLX system with an existing factory snapshot (snapshots/F).
#   4. Deploy first checks the SHA-256 of image.cpio.gz on the stick against
#      APPROVED_IMAGES, then asks for confirmation, then starts the vendor
#      installer (kexec) which erases the disk and installs the image.
#
# `factory-reset-gui.py --cli-login` runs only the sign-in on the terminal
# (exit 0 when signed in); the text menu uses it.
# Env: RLX_LOGO=<png>, RLX_FACTORY_VERSION=<version shown if not detected>.

import getpass, hashlib, json, os, re, shutil, socket, subprocess, sys, threading, time, zlib

LOGO = os.environ.get("RLX_LOGO", "/run/rlx/brand-logo.png")
DETECT_MNT = "/run/rlx-detect"
RW_MNT = "/run/rlx-rw"
AUTH = "/run/rlx-auth"                  # sign-in work area (RAM only)
MEDIA_MNT = "/run/rlx-media"
FLAG_BODY = "ACTION=restore-snapshot\nSNAPSHOT_TYPE=factory\n"
# Version the factory snapshot restores to, shown on the menu. Read from the
# snapshot when we can find it there; otherwise this value (env override).
FACTORY_VERSION = os.environ.get("RLX_FACTORY_VERSION", "2.0.0.1251623")
# Images that may be deployed: SHA-256 of image.cpio.gz -> name shown.
APPROVED_IMAGES = {
    "8ef0089784ce1e88990d83263db5875cda5a35d3181294e90fe99b76f16ca3b5":
        "cobas 6800: 2.0.3.3330507",
}
EFI_SETUP_MODE = "/sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c"

# pam_fsr logs in the system user "fsr" and asks for "Roche ID:" and "Token:".
PAM_CONF = "auth required pam_fsr.so -c :\n"
FSR_CHECK = r'''
import ctypes, json, sys
class Msg(ctypes.Structure):
    _fields_ = [("msg_style", ctypes.c_int), ("msg", ctypes.c_char_p)]
class Resp(ctypes.Structure):
    _fields_ = [("resp", ctypes.c_void_p), ("resp_retcode", ctypes.c_int)]
CONV = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.POINTER(Msg)),
                        ctypes.POINTER(ctypes.POINTER(Resp)), ctypes.c_void_p)
class Conv(ctypes.Structure):
    _fields_ = [("conv", CONV), ("appdata_ptr", ctypes.c_void_p)]
req = json.load(sys.stdin)
pam = ctypes.CDLL("libpam.so.0"); libc = ctypes.CDLL("libc.so.6")
libc.calloc.restype = ctypes.c_void_p
libc.strdup.restype = ctypes.c_void_p; libc.strdup.argtypes = [ctypes.c_char_p]
pam.pam_strerror.restype = ctypes.c_char_p
msgs = []
def conv(n, mp, rp, _):
    arr = libc.calloc(n, ctypes.sizeof(Resp))
    if not arr:
        return 5
    rs = ctypes.cast(arr, ctypes.POINTER(Resp))
    for i in range(n):
        m = mp[i].contents
        t = (m.msg or b"").decode("utf-8", "replace")
        if m.msg_style in (1, 2):
            low = t.lower()
            ans = req["rocheid"] if ("roche id" in low or "user" in low or "login" in low) \
                else req["token"] if ("token" in low or m.msg_style == 1) else ""
            rs[i].resp = libc.strdup(ans.encode())
        elif t.strip():
            msgs.append(t.strip())
    rp[0] = rs
    return 0
cb = CONV(conv); c = Conv(cb, None); h = ctypes.c_void_p()
rc = pam.pam_start_confdir(b"rlx-recovery", b"fsr", ctypes.byref(c),
                           req["confdir"].encode(), ctypes.byref(h))
if rc == 0:
    rc = pam.pam_authenticate(h, 0)
    err = pam.pam_strerror(h, rc).decode()
    pam.pam_end(h, rc)
else:
    err = "pam_start failed (%d)" % rc
print(json.dumps({"ok": rc == 0, "rc": rc, "error": err, "messages": msgs}))
'''


def run(cmd, **kw):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kw)


# ------------------------------------------------------------ instrument ----
def detect_rlx():
    """Return (device, version, has_factory) for the first RLX btrfs, or None."""
    devs = run(["blkid", "-t", "TYPE=btrfs", "-o", "device"]).stdout.split()
    os.makedirs(DETECT_MNT, exist_ok=True)
    for dev in devs:
        run(["umount", DETECT_MNT])
        if run(["mount", "-o", "ro,subvolid=5", dev, DETECT_MNT]).returncode != 0:
            continue
        try:
            if os.path.isdir(f"{DETECT_MNT}/root/etc") and os.path.exists(f"{DETECT_MNT}/opt/roche"):
                ver = "unknown"
                pi = f"{DETECT_MNT}/opt/roche/etc/projectinfo"
                if os.path.isfile(pi):
                    ver = open(pi).read().strip()
                lst = run(["btrfs", "subvolume", "list", DETECT_MNT]).stdout
                has_f = bool(re.search(r"snapshots/F", lst))
                return dev, ver, has_f
        finally:
            run(["umount", DETECT_MNT])
    return None


def factory_version():
    """Best effort: the version inside the factory snapshot (snapshots/F),
    else FACTORY_VERSION. Read-only."""
    devs = run(["blkid", "-t", "TYPE=btrfs", "-o", "device"]).stdout.split()
    os.makedirs(DETECT_MNT, exist_ok=True)
    for dev in devs:
        run(["umount", DETECT_MNT])
        if run(["mount", "-o", "ro,subvolid=5", dev, DETECT_MNT]).returncode != 0:
            continue
        try:
            for rel in ("snapshots/F/opt/roche/etc/projectinfo",
                        "snapshots/F/roche/etc/projectinfo",
                        "snapshots/F/opt/etc/projectinfo"):
                path = f"{DETECT_MNT}/{rel}"
                if os.path.isfile(path):
                    m = re.search(r"\d+(?:\.\d+){2,}", open(path).read())
                    if m:
                        return m.group(0)
        finally:
            run(["umount", DETECT_MNT])
    return FACTORY_VERSION


def arm(dev):
    os.makedirs(RW_MNT, exist_ok=True)
    run(["umount", RW_MNT])
    if run(["mount", "-o", "rw,subvolid=5", dev, RW_MNT]).returncode != 0:
        return False, "Could not open the instrument disk for writing."
    try:
        if not os.path.isdir(f"{RW_MNT}/root"):
            return False, "Unexpected disk layout (no 'root' subvolume)."
        with open(f"{RW_MNT}/root/rlx-boot", "w") as f:
            f.write(FLAG_BODY)
        subprocess.run(["sync"])
        return True, ""
    finally:
        run(["umount", RW_MNT])


# ---------------------------------------------------------- stick (media) ----
def find_media():
    """Directory of this USB stick holding the Deploy files, or None."""
    for d in ("/run/archiso/bootmnt", MEDIA_MNT):
        if os.path.isfile(f"{d}/image.cpio.gz") and os.path.isfile(f"{d}/vmlinuz"):
            return d
    os.makedirs(MEDIA_MNT, exist_ok=True)
    for dev in run(["blkid", "-t", "TYPE=iso9660", "-o", "device"]).stdout.split():
        run(["umount", MEDIA_MNT])
        if run(["mount", "-o", "ro", dev, MEDIA_MNT]).returncode == 0:
            if os.path.isfile(f"{MEDIA_MNT}/image.cpio.gz"):
                return MEDIA_MNT
            run(["umount", MEDIA_MNT])
    return None


def deploy_title():
    names = sorted(set(APPROVED_IMAGES.values()))
    return names[0] if len(names) == 1 else "image"


def sha256_file(path, progress=None):
    total, done, h = os.path.getsize(path), 0, hashlib.sha256()
    last = 0.0
    with open(path, "rb") as f:
        while True:
            b = f.read(8 << 20)
            if not b:
                break
            h.update(b)
            done += len(b)
            if progress and time.time() - last > 0.2:
                last = time.time()
                progress(done / total)
    return h.hexdigest()


def setup_mode():
    """True/False when the firmware reports Secure Boot Setup Mode, else None."""
    try:
        return open(EFI_SETUP_MODE, "rb").read()[-1] == 1
    except OSError:
        return None


def start_installer(media):
    """Load the vendor installer (kernel + initrd from the stick) and jump into
    it. Returns an error text; on success it does not return."""
    kexec = shutil.which("kexec")
    if not kexec:
        return "The 'kexec' tool is missing on this recovery stick."
    args = [f"{media}/vmlinuz", f"--initrd={media}/initrd.img", "--append=quiet"]
    r = run([kexec, "-l"] + args)
    if r.returncode != 0:
        r = run([kexec, "-s", "-l"] + args)
        if r.returncode != 0:
            return "Could not load the installer: " + (r.stderr.strip() or "kexec failed")
    subprocess.run(["sync"])
    if run(["systemctl", "kexec"]).returncode != 0:
        run([kexec, "-e"])
    return "The installer did not start."


# ------------------------------------------------------------- sign in -------
class AuthError(Exception):
    pass


AUTH_LIB_RE = re.compile(
    r"^(libc|libm|libpam|libaudit|libcap-ng|libcap|libfsrverify|libcrypto|libssl|"
    r"libxml2|libstdc\+\+|libgcc_s|libicu\w*|libz|liblzma|libzstd|libffi|libexpat|"
    r"libpthread|libdl|librt|libutil|libbz2|libmd|libuuid|libnsl|libcrypt|"
    r"libresolv|libnss_files|libtinfo)\.so")
AUTH_ETC = {"etc/passwd", "etc/group", "etc/fsr-authentication.keys", "etc/fsrverify.conf",
            "etc/ld.so.cache", "etc/nsswitch.conf", "var/fsrkeyrevocation.dat"}
PY_SKIP = ("/test/", "/tests/", "/idlelib/", "/tkinter/", "/turtledemo/", "/lib2to3/",
           "/ensurepip/", "/site-packages/", "/dist-packages/", "/__pycache__/")
SYS_TOP = ("etc", "usr", "var", "bin", "sbin", "lib", "lib64")


def _auth_wanted(rel):
    if rel in AUTH_ETC or rel in ("bin", "sbin", "lib", "lib64"):
        return True
    if rel.startswith(("usr/bin/python3", "usr/lib64/", "lib64/")):
        return True
    if rel.startswith("usr/lib/python3"):
        return not any(s in "/" + rel + "/" for s in PY_SKIP)
    for base in ("usr/lib/x86_64-linux-gnu/", "lib/x86_64-linux-gnu/"):
        if rel.startswith(base):
            rest = rel[len(base):]
            if rest.startswith("security/"):
                return bool(re.match(r"security/pam_(fsr|deny|permit)\.so", rest))
            return "/" not in rest and bool(AUTH_LIB_RE.match(rest))
    return False


class _GzReader:
    """Sequential reader over a (multi-member) .gz file; hashes the raw bytes."""

    def __init__(self, path, progress=None):
        self.f = open(path, "rb")
        self.total = os.path.getsize(path)
        self.done = 0
        self.sha = hashlib.sha256()
        self.d = zlib.decompressobj(31)
        self.buf = bytearray()
        self.eof = False
        self.progress, self.last = progress, 0.0

    def _fill(self):
        while not self.eof:
            raw = self.f.read(4 << 20)
            if not raw:
                self.eof = True
                return
            self.sha.update(raw)
            self.done += len(raw)
            if self.progress and time.time() - self.last > 0.2:
                self.last = time.time()
                self.progress(self.done / self.total)
            while raw:
                out = self.d.decompress(raw)
                self.buf += out
                if self.d.eof:            # next gzip member, if any
                    raw = self.d.unused_data
                    self.d = zlib.decompressobj(31)
                else:
                    raw = b""
            if self.buf:
                return

    def read(self, n):
        while len(self.buf) < n and not self.eof:
            self._fill()
        out = bytes(self.buf[:n])
        del self.buf[:n]
        return out

    def skip(self, n):
        while n > 0:
            if not self.buf:
                self._fill()
                if not self.buf:
                    return
            k = min(n, len(self.buf))
            del self.buf[:k]
            n -= k

    def finish(self):
        """Hash the rest of the file (so the image checksum is complete)."""
        while True:
            raw = self.f.read(8 << 20)
            if not raw:
                break
            self.sha.update(raw)
            self.done += len(raw)
            if self.progress and time.time() - self.last > 0.2:
                self.last = time.time()
                self.progress(self.done / self.total)
        self.f.close()
        return self.sha.hexdigest()


def extract_auth_files(image, dest, progress=None):
    """Pull the instrument's login check (pam_fsr, keys, Python, libraries) out
    of the Deploy image into dest. Returns the image's SHA-256 (computed on the
    way). Raises AuthError."""
    r = _GzReader(image, progress)
    pending_links = []
    try:
        while True:
            hdr = r.read(110)
            if len(hdr) < 110:
                break
            if hdr[:6] not in (b"070701", b"070702"):
                raise AuthError("The image on this stick is not in the expected format.")
            fld = [int(hdr[6 + 8 * k:14 + 8 * k], 16) for k in range(13)]
            mode, filesize, namesize = fld[1], fld[6], fld[11]
            name = r.read(namesize)[:-1].decode("utf-8", "replace")
            r.skip((-(110 + namesize)) % 4)
            if name == "TRAILER!!!":
                break
            rel = name.lstrip("./").lstrip("/")
            parts = rel.split("/")
            if len(parts) > 1 and parts[0] in ("root", "rootfs") and parts[1] in SYS_TOP:
                rel = "/".join(parts[1:])   # image keeps the system under root/
            if not _auth_wanted(rel):
                r.skip(filesize + (-filesize) % 4)
                continue
            data = r.read(filesize)
            r.skip((-filesize) % 4)
            path = os.path.join(dest, rel)
            ftype = mode & 0o170000
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if ftype == 0o040000:
                os.makedirs(path, exist_ok=True)
            elif ftype == 0o120000:
                pending_links.append((data.decode("utf-8", "replace"), path))
            elif ftype == 0o100000:
                with open(path, "wb") as f:
                    f.write(data)
                os.chmod(path, mode & 0o7777)
        sha = r.finish()
    except (OSError, zlib.error, ValueError) as e:
        raise AuthError("Could not read the image on this stick (%s)." % e)
    for target, path in pending_links:
        if not os.path.lexists(path):
            os.symlink(target, path)
    py = os.path.join(dest, "usr/bin/python3")
    if not os.path.lexists(py):
        cands = sorted(f for f in os.listdir(os.path.dirname(py))
                       if re.match(r"python3\.\d+$", f)) if os.path.isdir(os.path.dirname(py)) else []
        if cands:
            os.symlink(cands[-1], py)
    for need in ("usr/bin/python3", "etc/fsr-authentication.keys"):
        if not os.path.exists(os.path.join(dest, need)):
            raise AuthError("The image on this stick has no usable sign-in (%s missing)." % need)
    return sha


def _mounts_under(path):
    out = []
    for line in open("/proc/mounts"):
        mp = line.split()[1].replace("\\040", " ")
        if mp == path or mp.startswith(path + "/"):
            out.append(mp)
    return sorted(out, key=len, reverse=True)


def cleanup_auth():
    for mp in _mounts_under(AUTH):
        run(["umount", "-l", mp])


def prepare_auth_root(progress=None):
    """Mount a throw-away (RAM-backed) copy of an installed cobas system that
    has the token check. Returns (root, source, image_sha or None)."""
    cleanup_auth()
    for d in ("top", "rw", "img", "root"):
        os.makedirs(f"{AUTH}/{d}", exist_ok=True)
    lower, source, sha = None, None, None
    info = detect_rlx()
    if info and run(["mount", "-o", "ro,subvolid=5", info[0], f"{AUTH}/top"]).returncode == 0:
        cand = f"{AUTH}/top/root"
        if (os.path.exists(f"{cand}/etc/fsr-authentication.keys")
                and os.path.exists(f"{cand}/usr/bin/python3")):
            lower, source = cand, "instrument"
    if lower is None:
        media = find_media()
        if not media:
            raise AuthError("No cobas 6800/8800 system was found on this instrument, and "
                            "this stick has no image to check the token with.")
        if run(["mount", "-t", "tmpfs", "-o", "size=75%", "rlx-auth", f"{AUTH}/img"]).returncode:
            raise AuthError("Could not prepare the sign-in (no memory).")
        sha = extract_auth_files(f"{media}/image.cpio.gz", f"{AUTH}/img", progress)
        root, source = f"{AUTH}/img", "image"
    else:
        # writes (e.g. the token library's own files) go to RAM, never to the disk
        run(["mount", "-t", "tmpfs", "rlx-auth", f"{AUTH}/rw"])
        os.makedirs(f"{AUTH}/rw/upper", exist_ok=True)
        os.makedirs(f"{AUTH}/rw/work", exist_ok=True)
        root = f"{AUTH}/root"
        if run(["mount", "-t", "overlay", "overlay", "-o",
                f"lowerdir={lower},upperdir={AUTH}/rw/upper,workdir={AUTH}/rw/work",
                root]).returncode != 0:
            root = lower                     # read-only fallback
            run(["mount", "-t", "tmpfs", "rlx-auth", f"{root}/tmp"])
    for d in ("dev", "proc", "tmp"):
        os.makedirs(f"{root}/{d}", exist_ok=True)
    run(["mount", "-t", "tmpfs", "rlx-dev", f"{root}/dev"])
    for name, mj, mn in (("null", 1, 3), ("zero", 1, 5), ("random", 1, 8), ("urandom", 1, 9)):
        try:
            os.mknod(f"{root}/dev/{name}", 0o20666, os.makedev(mj, mn))
        except OSError:
            pass
    run(["mount", "-t", "proc", "proc", f"{root}/proc"])
    return root, source, sha


class _LogCatcher:
    """Receives the login module's syslog messages (via <root>/dev/log) so we
    can tell the user WHY a token was rejected."""

    def __init__(self, path):
        self.lines = []
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            os.unlink(path)
        except OSError:
            pass
        self.s.bind(path)
        os.chmod(path, 0o666)
        self.s.settimeout(0.3)
        self.stop = False
        self.t = threading.Thread(target=self._loop, daemon=True)
        self.t.start()

    def _loop(self):
        while not self.stop:
            try:
                self.lines.append(self.s.recv(8192).decode("utf-8", "replace"))
            except socket.timeout:
                continue
            except OSError:
                break

    def close(self):
        time.sleep(0.3)
        self.stop = True
        self.t.join(1)
        self.s.close()

    def reason(self):
        for line in reversed(self.lines):
            m = re.search(r"Reason:\s*(.+)$", line)
            if m and m.group(1).strip():
                return m.group(1).strip()
        return ""


def friendly(reason):
    low = reason.lower()
    if "expired" in low:
        return "This token has expired. Request a new token."
    if "revo" in low:
        return "This token can no longer be used (its key was revoked)."
    if "signature" in low or "incorrect" in low or "invalid" in low:
        return "The Roche ID or token is not correct."
    if "not supported" in low or "token type" in low:
        return "This kind of token cannot be used here. Use your service (FSR) token."
    return "Sign-in failed."


def verify_token(rocheid, token, progress=None):
    """Check a Roche ID + token with the instrument's own login (pam_fsr).
    Returns (ok, message, image_sha or None)."""
    rocheid, token = rocheid.strip(), token.strip()
    if not rocheid or not token:
        return False, "Enter your Roche ID and token.", None
    try:
        root, source, sha = prepare_auth_root(progress)
    except AuthError as e:
        cleanup_auth()
        return False, str(e), None
    log = None
    try:
        os.makedirs(f"{root}/tmp/rlx-pam", exist_ok=True)
        with open(f"{root}/tmp/rlx-pam/rlx-recovery", "w") as f:
            f.write(PAM_CONF)
        with open(f"{root}/tmp/rlx-fsr-check.py", "w") as f:
            f.write(FSR_CHECK)
        log = _LogCatcher(f"{root}/dev/log")
        # "rsr/name" is also accepted: try it as typed, then without the prefix
        ids = [rocheid] + ([rocheid.split("/", 1)[1]] if "/" in rocheid else [])
        res = {}
        for rid in ids:
            try:
                p = run(["chroot", root, "/usr/bin/python3", "-I", "-S", "/tmp/rlx-fsr-check.py"],
                        input=json.dumps({"rocheid": rid, "token": token,
                                          "confdir": "/tmp/rlx-pam"}), timeout=60)
                res = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else \
                    {"ok": False, "error": (p.stderr.strip().splitlines() or ["no answer"])[-1]}
            except (subprocess.TimeoutExpired, ValueError) as e:
                res = {"ok": False, "error": str(e)}
            if res.get("ok"):
                return True, rid, sha
        log.close()
        reason = log.reason() or "; ".join(res.get("messages") or []) or res.get("error", "")
        msg = friendly(reason)
        if reason:
            msg += "\n(" + reason + ")"
        return False, msg, sha
    finally:
        if log and not log.stop:
            log.close()
        cleanup_auth()


def cli_login():
    """Terminal sign-in for the text menu. Exit code 0 when signed in."""
    print("\n  cobas 6800 Recovery - sign in with your Roche ID and token.\n")
    for _ in range(3):
        try:
            rid = input("  Roche ID: ")
            tok = getpass.getpass("  Token: ")
        except (EOFError, KeyboardInterrupt):
            return 1
        print("  Checking ...")
        ok, msg, _ = verify_token(rid, tok)
        if ok:
            print("  Signed in as %s.\n" % msg)
            return 0
        print("  " + msg.replace("\n", "\n  ") + "\n")
    return 1


# ------------------------------------------------------------------- GUI -----
CSS = b"""
window, .page { background:#ffffff; }
.h1 { font-size:26px; font-weight:700; color:#15191e; }
.h1.danger { color:#c62828; }
.h1.good { color:#1c7a43; }
.sub { font-size:15px; color:#5b6672; }
.brand { font-size:12px; font-weight:700; color:#616c78; }
.field { font-size:13px; font-weight:700; color:#15191e; }
.mono { font-family:monospace; font-size:14px; color:#15191e; }
.err { color:#c62828; font-size:14px; }
.warn { background:#fdecec; border:1px solid #f2c2c2; border-radius:8px; padding:14px; }
.warn .wh { color:#c62828; font-weight:700; font-size:15px; }
.warn .wt { color:#7a1f1f; font-size:14px; }
entry { font-size:16px; padding:10px; min-width:420px; }
button { font-size:16px; font-weight:600; padding:14px 18px; border-radius:8px;
         border:1px solid #d9dfe6; background:#ffffff; color:#15191e; }
button.primary { background:#0b63b8; color:#ffffff; border-color:#0b63b8; }
button.danger  { background:#c62828; color:#ffffff; border-color:#c62828; }
button.choice { padding:18px 22px; min-width:560px; }
button.choice .ct { font-size:18px; font-weight:700; color:#15191e; }
button.choice .cs { font-size:14px; font-weight:400; color:#5b6672; }
button.link { border:none; background:transparent; color:#0b63b8; padding:6px 0; }
.ok { color:#1c7a43; font-weight:700; }
progressbar trough { min-height:14px; border-radius:7px; }
progressbar progress { min-height:14px; border-radius:7px; background:#0b63b8; }
"""


def gui_main():
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

    def ui(fn, *a):
        GLib.idle_add(lambda: (fn(*a), False)[1])

    class App(Gtk.Window):
        def __init__(self):
            super().__init__()
            # There is no window manager under startx, so fullscreen() alone is
            # ignored: size the window to the monitor ourselves.
            self.set_decorated(False)
            disp = Gdk.Display.get_default()
            mon = disp.get_primary_monitor() or disp.get_monitor(0)
            g = mon.get_geometry()
            self.move(g.x, g.y)
            self.set_default_size(g.width, g.height)
            self.resize(g.width, g.height)
            self.fullscreen()
            prov = Gtk.CssProvider()
            prov.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

            self.user = None
            self.dev = None
            self.media = None
            self.image_sha = None
            self.factory_ver = FACTORY_VERSION
            self._pulsing = False
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            outer.get_style_context().add_class("page")
            self.add(outer)

            head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, margin=28)
            brand = Gtk.Label(label="cobas 6800 / 8800", xalign=0)
            brand.get_style_context().add_class("brand")
            head.pack_start(brand, True, True, 0)
            if os.path.isfile(LOGO):
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(LOGO, -1, 46, True)
                    head.pack_end(Gtk.Image.new_from_pixbuf(pb), False, False, 0)
                except Exception:
                    pass
            outer.pack_start(head, False, False, 0)

            self.stack = Gtk.Stack(margin=48, vhomogeneous=False)
            outer.pack_start(self.stack, True, True, 0)
            for name, page in (("login", self._login()), ("busy", self._busy()),
                               ("menu", self._menu()), ("warn", self._warn()),
                               ("done", self._done()), ("imgok", self._imgok()),
                               ("imgbad", self._imgbad()), ("dconfirm", self._dconfirm()),
                               ("error", self._error())):
                self.stack.add_named(page, name)
            self.connect("destroy", Gtk.main_quit)

        # ---- widgets
        def _col(self, spacing=14):
            return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing,
                           valign=Gtk.Align.CENTER)

        def _label(self, text, cls, wrap=True, width=60):
            lb = Gtk.Label(label=text, xalign=0)
            for c in cls.split():
                lb.get_style_context().add_class(c)
            lb.set_line_wrap(wrap)
            lb.set_max_width_chars(width)
            return lb

        def _btn(self, text, cls, cb):
            b = Gtk.Button(label=text, halign=Gtk.Align.START)
            for c in cls.split():
                b.get_style_context().add_class(c)
            b.connect("clicked", cb)
            return b

        def _choice(self, title, sub, cb):
            b = Gtk.Button(halign=Gtk.Align.START)
            b.get_style_context().add_class("choice")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            t = self._label(title, "ct", False)
            s = self._label(sub, "cs")
            box.pack_start(t, False, False, 0)
            box.pack_start(s, False, False, 0)
            b.add(box)
            b.connect("clicked", cb)
            return b, t, s

        # ---- pages
        def _login(self):
            b = self._col(10)
            b.pack_start(self._label("Sign in", "h1"), False, False, 0)
            b.pack_start(self._label("Sign in with your Roche ID and token to use the "
                                     "recovery tools.", "sub"), False, False, 6)
            b.pack_start(self._label("Roche ID", "field", False), False, False, 0)
            self.e_id = Gtk.Entry(halign=Gtk.Align.START)
            b.pack_start(self.e_id, False, False, 0)
            b.pack_start(self._label("Token", "field", False), False, False, 4)
            self.e_tok = Gtk.Entry(halign=Gtk.Align.START, visibility=False)
            b.pack_start(self.e_tok, False, False, 0)
            show = Gtk.CheckButton(label="Show token")
            show.connect("toggled", lambda w: self.e_tok.set_visibility(w.get_active()))
            b.pack_start(show, False, False, 0)
            self.login_err = self._label("", "err")
            b.pack_start(self.login_err, False, False, 0)
            self.e_id.connect("activate", lambda *_: self.e_tok.grab_focus())
            self.e_tok.connect("activate", self.on_signin)
            b.pack_start(self._btn("Sign in", "primary", self.on_signin), False, False, 8)
            return b

        def _busy(self):
            b = self._col()
            self.busy_title = self._label("", "h1")
            self.busy_sub = self._label("", "sub")
            self.bar = Gtk.ProgressBar(show_text=False)
            self.bar.set_size_request(560, -1)
            self.bar.set_halign(Gtk.Align.START)
            b.pack_start(self.busy_title, False, False, 0)
            b.pack_start(self.busy_sub, False, False, 0)
            b.pack_start(self.bar, False, False, 8)
            return b

        def _menu(self):
            b = self._col()
            b.pack_start(self._label("Choose an action", "h1"), False, False, 0)
            self.who = self._label("", "sub")
            b.pack_start(self.who, False, False, 0)
            self.c_reset, _, self.c_reset_sub = self._choice(
                "Factory Reset", "", self.on_start)
            self.c_deploy, self.c_deploy_t, self.c_deploy_sub = self._choice(
                "Deploy %s image" % deploy_title(),
                "Erases the whole instrument and installs this image.", self.on_deploy)
            b.pack_start(self.c_reset, False, False, 6)
            b.pack_start(self.c_deploy, False, False, 0)
            b.pack_start(self._btn("Sign out", "link", self.on_signout), False, False, 6)
            return b

        def _warn(self):
            b = self._col()
            b.pack_start(self._label("Confirm Factory Reset", "h1 danger"), False, False, 0)
            w = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            w.get_style_context().add_class("warn")
            w.pack_start(self._label("This cannot be undone", "wh", False), False, False, 0)
            w.pack_start(self._label(
                "The instrument will restart and return to its factory state. Current "
                "settings, calibrations and data will be removed. Make sure a backup "
                "exists if needed.", "wt"), False, False, 0)
            b.pack_start(w, False, False, 0)
            row = Gtk.Box(spacing=12, margin_top=10)
            row.pack_start(self._btn("Yes, reset now", "danger", self.on_confirm), False, False, 0)
            row.pack_start(self._btn("Go back", "", lambda *_: self.show("menu")), False, False, 0)
            b.pack_start(row, False, False, 0)
            return b

        def _done(self):
            b = self._col()
            b.pack_start(self._label("Factory Reset armed", "h1"), False, False, 0)
            b.pack_start(self._label("The instrument is ready to reset. To start it:", "sub"),
                         False, False, 0)
            b.pack_start(self._label("1.  Remove the USB stick now.", "sub ok", False), False, False, 0)
            b.pack_start(self._label("2.  Press Restart below.", "sub ok", False), False, False, 0)
            b.pack_start(self._label(
                "After it restarts, the instrument completes the reset on its own. This can "
                "take several minutes — do not power it off.", "sub"), False, False, 0)
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=10)
            row.pack_start(self._btn("Restart now", "primary", self.on_reboot), False, False, 0)
            b.pack_start(row, False, False, 0)
            return b

        def _imgok(self):
            b = self._col()
            b.pack_start(self._label("✓  Image verified", "h1 good"), False, False, 0)
            self.ok_name = self._label("", "sub")
            b.pack_start(self.ok_name, False, False, 0)
            b.pack_start(self._label("SHA-256", "field", False), False, False, 6)
            self.ok_sha = self._label("", "mono", True, 40)
            self.ok_sha.set_selectable(True)
            b.pack_start(self.ok_sha, False, False, 0)
            self.ok_note = self._label("", "err")
            b.pack_start(self.ok_note, False, False, 0)
            row = Gtk.Box(spacing=12, margin_top=10)
            self.ok_continue = self._btn("Continue", "primary",
                                         lambda *_: self.show("dconfirm"))
            row.pack_start(self.ok_continue, False, False, 0)
            row.pack_start(self._btn("Go back", "", lambda *_: self.show("menu")), False, False, 0)
            b.pack_start(row, False, False, 0)
            return b

        def _imgbad(self):
            b = self._col()
            b.pack_start(self._label("✗  This image is not approved", "h1 danger"), False, False, 0)
            b.pack_start(self._label(
                "The image on this USB stick does not match an approved cobas image, so it "
                "cannot be deployed. Use another stick or contact GCS.", "sub"), False, False, 0)
            b.pack_start(self._label("SHA-256 of the image on this stick", "field", False),
                         False, False, 6)
            self.bad_sha = self._label("", "mono", True, 40)
            self.bad_sha.set_selectable(True)
            b.pack_start(self.bad_sha, False, False, 0)
            b.pack_start(self._btn("Go back", "", lambda *_: self.show("menu")), False, False, 10)
            return b

        def _dconfirm(self):
            b = self._col()
            self.dc_title = self._label("", "h1 danger")
            b.pack_start(self.dc_title, False, False, 0)
            w = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            w.get_style_context().add_class("warn")
            w.pack_start(self._label("This erases the whole instrument", "wh", False), False, False, 0)
            self.dc_text = self._label("", "wt")
            w.pack_start(self.dc_text, False, False, 0)
            b.pack_start(w, False, False, 0)
            row = Gtk.Box(spacing=12, margin_top=10)
            row.pack_start(self._btn("Yes, erase and install", "danger", self.on_deploy_go),
                           False, False, 0)
            row.pack_start(self._btn("Go back", "", lambda *_: self.show("menu")), False, False, 0)
            b.pack_start(row, False, False, 0)
            return b

        def _error(self):
            b = self._col()
            self.err_title = self._label("", "h1 danger")
            b.pack_start(self.err_title, False, False, 0)
            self.err_lbl = self._label("", "sub")
            b.pack_start(self.err_lbl, False, False, 0)
            self.err_back = "menu"
            b.pack_start(self._btn("Back", "", lambda *_: self.show(self.err_back)), False, False, 8)
            return b

        # ---- helpers
        def show(self, name):
            self.stack.set_visible_child_name(name)

        def fail(self, title, msg, back="menu"):
            self.err_title.set_text(title)
            self.err_lbl.set_text(msg)
            self.err_back = back
            self.show("error")

        def busy(self, title, sub, frac=None):
            self.busy_title.set_text(title)
            self.busy_sub.set_text(sub)
            if frac is None:
                self.bar.pulse()
            else:
                self.bar.set_fraction(frac)
            self.show("busy")

        def _pulse(self):
            if self.stack.get_visible_child_name() != "busy" or not self._pulsing:
                return False
            self.bar.pulse()
            return True

        def start_pulse(self):
            self._pulsing = True
            GLib.timeout_add(120, self._pulse)

        # ---- sign in
        def on_signin(self, *_):
            rid, tok = self.e_id.get_text(), self.e_tok.get_text()
            self.login_err.set_text("")
            self.busy("Checking your token", "This takes a few seconds.")
            self.start_pulse()

            def prog(f):
                self._pulsing = False
                ui(self.busy, "Checking your token",
                   "Preparing the sign-in from the image on this stick (first time only, "
                   "about a minute) ...", f)

            def work():
                ok, msg, sha = verify_token(rid, tok, prog)
                self._pulsing = False
                if sha:
                    self.image_sha = sha
                ui(self.after_signin, ok, msg)
            threading.Thread(target=work, daemon=True).start()

        def after_signin(self, ok, msg):
            self.e_tok.set_text("")
            if not ok:
                self.login_err.set_text(msg)
                self.show("login")
                self.e_tok.grab_focus()
                return
            self.user = msg
            self.who.set_text("Signed in as %s." % self.user)
            self.refresh_menu()

        def refresh_menu(self):
            self.busy("Looking at the instrument", "One moment ...")
            self.start_pulse()

            def work():
                info = detect_rlx()
                ver = factory_version() if info and info[2] else None
                media = find_media()
                self._pulsing = False
                ui(self._fill_menu, info, ver, media)
            threading.Thread(target=work, daemon=True).start()

        def _fill_menu(self, info, ver, media):
            self.media = media
            if not info:
                self.dev = None
                self.c_reset.set_sensitive(False)
                self.c_reset_sub.set_text("Not available: no cobas 6800/8800 system was found "
                                          "on this instrument.")
            elif not info[2]:
                self.dev = None
                self.c_reset.set_sensitive(False)
                self.c_reset_sub.set_text("Not available: this instrument has no factory "
                                          "snapshot. Contact GCS.")
            else:
                self.dev = info[0]
                self.factory_ver = ver or FACTORY_VERSION
                self.c_reset.set_sensitive(True)
                self.c_reset_sub.set_text("Restores the instrument back to its original "
                                          "state (%s)." % self.factory_ver)
            self.c_deploy.set_visible(bool(media))
            self.show("menu")

        def on_signout(self, *_):
            self.user = None
            self.e_id.set_text("")
            self.e_tok.set_text("")
            self.show("login")
            self.e_id.grab_focus()

        # ---- factory reset
        def on_start(self, *_):
            if self.dev:
                self.show("warn")

        def on_confirm(self, *_):
            ok, msg = arm(self.dev)
            self.show("done") if ok else self.fail("Cannot start Factory Reset", msg)

        def on_reboot(self, *_):
            subprocess.run(["sync"])
            if run(["systemctl", "reboot"]).returncode != 0:
                subprocess.Popen(["reboot", "-f"])

        # ---- deploy
        def on_deploy(self, *_):
            if not self.media:
                return
            if self.image_sha:            # already computed during sign-in
                return self.after_hash(self.image_sha)
            self.busy("Checking the image", "Reading the image on the USB stick ...", 0)

            def prog(f):
                ui(self.busy, "Checking the image",
                   "Reading the image on the USB stick ... %d%%" % (f * 100), f)

            def work():
                try:
                    sha = sha256_file(f"{self.media}/image.cpio.gz", prog)
                except OSError as e:
                    return ui(self.fail, "Cannot read the image", str(e))
                self.image_sha = sha
                ui(self.after_hash, sha)
            threading.Thread(target=work, daemon=True).start()

        def after_hash(self, sha):
            name = APPROVED_IMAGES.get(sha)
            if not name:
                self.bad_sha.set_text(sha)
                return self.show("imgbad")
            self.ok_name.set_text("%s — matches the approved image." % name)
            self.ok_sha.set_text(sha)
            sm = setup_mode()
            if sm is False:
                self.ok_note.set_text(
                    "Secure Boot is not in Setup Mode, so the installer will refuse to run. "
                    "Restart, open the BIOS, choose Security → Reset To Setup Mode, and "
                    "start again.")
                self.ok_continue.set_sensitive(False)
            else:
                self.ok_note.set_text("")
                self.ok_continue.set_sensitive(True)
            self.dc_title.set_text("Deploy %s" % name)
            self.dc_text.set_text(
                "All software, settings, calibrations and data on this instrument are erased "
                "and %s is installed. Make sure a backup exists if needed. Leave the USB "
                "stick in until the installer says it is done." % name)
            self.show("imgok")

        def on_deploy_go(self, *_):
            self.busy("Starting the installer", "The installer screen appears in a moment.")
            self.start_pulse()

            def work():
                cleanup_auth()
                err = start_installer(self.media)
                self._pulsing = False
                ui(self.fail, "Cannot start the installer", err)
            threading.Thread(target=work, daemon=True).start()

    win = App()
    win.show_all()
    win.show("login")
    win.e_id.grab_focus()
    Gtk.main()


if __name__ == "__main__":
    if "--cli-login" in sys.argv[1:]:
        sys.exit(cli_login())
    gui_main()
