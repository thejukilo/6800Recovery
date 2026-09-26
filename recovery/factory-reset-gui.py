#!/usr/bin/env python3
# factory-reset-gui.py - graphical (GTK) Factory Reset screen for the recovery USB.
#
# Runs fullscreen under X on the SystemRescue recovery stick. White background,
# a logo top-right, plain wording, two choices (Start Factory Reset / Cancel),
# and a warning + confirm before anything happens. On confirm it arms the same
# /rlx-boot factory-reset flag the text menu writes; the instrument performs the
# reset on its next boot.
#
# It never runs the reset itself, and it REFUSES unless it finds an RLX system
# with an existing factory snapshot (snapshots/F). Env: RLX_LOGO=<png path>.

import os, re, subprocess, gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

LOGO = os.environ.get("RLX_LOGO", "/run/rlx/brand-logo.png")
DETECT_MNT = "/run/rlx-detect"
RW_MNT = "/run/rlx-rw"
FLAG_BODY = "ACTION=restore-snapshot\nSNAPSHOT_TYPE=factory\n"

CSS = b"""
window, .page { background:#ffffff; }
.h1 { font-size:26px; font-weight:700; color:#15191e; }
.h1.danger { color:#c62828; }
.sub { font-size:15px; color:#5b6672; }
.brand { font-size:12px; font-weight:700; color:#616c78; }
.warn { background:#fdecec; border:1px solid #f2c2c2; border-radius:8px; padding:14px; }
.warn .wh { color:#c62828; font-weight:700; font-size:15px; }
.warn .wt { color:#7a1f1f; font-size:14px; }
button { font-size:16px; font-weight:600; padding:14px 18px; border-radius:8px;
         border:1px solid #d9dfe6; background:#ffffff; color:#15191e; }
button.primary { background:#0b63b8; color:#ffffff; border-color:#0b63b8; }
button.danger  { background:#c62828; color:#ffffff; border-color:#c62828; }
.ok { color:#1c7a43; font-weight:700; }
"""


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


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


class App(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.fullscreen()
        self.set_default_size(1024, 768)
        prov = Gtk.CssProvider(); prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.dev = None
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.get_style_context().add_class("page")
        self.add(outer)

        # header row: brand line left, logo right
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
        self.stack.add_named(self._main(), "main")
        self.stack.add_named(self._warn(), "warn")
        self.stack.add_named(self._done(), "done")
        self.stack.add_named(self._cancel(), "cancel")
        self.stack.add_named(self._error(), "error")

        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self._key)

    def _col(self, spacing=14):
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing, valign=Gtk.Align.CENTER)
        return b

    def _label(self, text, cls, wrap=True, width=52):
        l = Gtk.Label(label=text, xalign=0);
        for c in cls.split(): l.get_style_context().add_class(c)
        l.set_line_wrap(wrap); l.set_max_width_chars(width)
        return l

    def _btn(self, text, cls, cb):
        b = Gtk.Button(label=text, halign=Gtk.Align.START)
        for c in cls.split(): b.get_style_context().add_class(c)
        b.connect("clicked", cb)
        return b

    def _main(self):
        b = self._col()
        b.pack_start(self._label("Factory Reset", "h1"), False, False, 0)
        b.pack_start(self._label(
            "This restores the instrument to its factory state. Use it only when "
            "instructed by GCS and the normal reset in the software isn't possible.",
            "sub"), False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=10)
        row.pack_start(self._btn("Start Factory Reset", "primary", self.on_start), False, False, 0)
        row.pack_start(self._btn("Cancel", "", self.on_cancel), False, False, 0)
        b.pack_start(row, False, False, 0)
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
        row.pack_start(self._btn("Go back", "", lambda *_: self.show("main")), False, False, 0)
        b.pack_start(row, False, False, 0)
        return b

    def _done(self):
        b = self._col()
        b.pack_start(self._label("Factory Reset armed", "h1"), False, False, 0)
        b.pack_start(self._label("The instrument is ready to reset. To start it:", "sub"), False, False, 0)
        b.pack_start(self._label("1.  Remove the USB stick now.", "sub ok", False), False, False, 0)
        b.pack_start(self._label("2.  Press Restart below.", "sub ok", False), False, False, 0)
        b.pack_start(self._label(
            "After it restarts, the instrument completes the reset on its own. This can "
            "take several minutes — do not power it off.", "sub"), False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=10)
        row.pack_start(self._btn("Restart now", "primary", self.on_reboot), False, False, 0)
        b.pack_start(row, False, False, 0)
        return b

    def _cancel(self):
        b = self._col()
        b.pack_start(self._label("Cancelled", "h1"), False, False, 0)
        b.pack_start(self._label(
            "Nothing was changed. You can remove the USB stick and restart the "
            "instrument normally.", "sub"), False, False, 0)
        b.pack_start(self._btn("Back to start", "", lambda *_: self.show("main")), False, False, 0)
        return b

    def _error(self):
        b = self._col()
        b.pack_start(self._label("Cannot start Factory Reset", "h1 danger"), False, False, 0)
        self.err_lbl = self._label("", "sub")
        b.pack_start(self.err_lbl, False, False, 0)
        b.pack_start(self._btn("Back to start", "", lambda *_: self.show("main")), False, False, 0)
        return b

    def show(self, name):
        self.stack.set_visible_child_name(name)

    def _fail(self, msg):
        self.err_lbl.set_text(msg); self.show("error")

    def on_start(self, *_):
        info = detect_rlx()
        if not info:
            return self._fail("No cobas 6800/8800 system disk was found on this instrument.")
        self.dev, ver, has_f = info
        if not has_f:
            return self._fail("No factory snapshot exists on this instrument, so a factory "
                              "reset cannot run. Contact GCS.")
        self.show("warn")

    def on_confirm(self, *_):
        ok, msg = arm(self.dev)
        self.show("done") if ok else self._fail(msg)

    def on_reboot(self, *_):
        subprocess.run(["sync"])
        if run(["systemctl", "reboot"]).returncode != 0:
            subprocess.Popen(["reboot", "-f"])

    def on_cancel(self, *_):
        self.show("cancel")

    def _key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.show("main")


if __name__ == "__main__":
    win = App(); win.show_all(); win.show("main"); Gtk.main()
