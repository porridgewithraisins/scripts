#!/usr/bin/env python3

import gi
import subprocess
import json
import os

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GObject, Gdk, Pango

DATA_FILE = os.path.expanduser("~/.local/share/workspace_tags.json")


class WorkspaceTagger(Gtk.Window):
    def __init__(self):
        super().__init__(title="Workspace Tags")

        self.set_default_size(820, 640)
        self.set_border_width(12)

        self.keep_open = False
        self.auto_refresh_enabled = False
        self.skip_close_confirm = False

        self.search_text = ""

        self.pinned_windows = set()

        self.metadata = self.load_metadata()

        self.connect("focus-out-event", self.on_focus_out)
        self.connect("key-press-event", self.on_key_press)

        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12
        )

        self.add(outer)

        topbar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        outer.pack_start(topbar, False, False, 0)

        refresh_btn = Gtk.Button(label="Refresh")

        refresh_btn.connect("clicked", self.refresh)

        topbar.pack_start(refresh_btn, False, False, 0)

        self.auto_btn = Gtk.ToggleButton(label="Auto Refresh")

        self.auto_btn.connect(
            "toggled",
            self.on_auto_refresh_toggled
        )

        topbar.pack_start(self.auto_btn, False, False, 0)

        self.keep_btn = Gtk.ToggleButton(label="Keep Open")

        self.keep_btn.connect(
            "toggled",
            self.on_keep_toggled
        )

        topbar.pack_start(self.keep_btn, False, False, 0)

        self.search_entry = Gtk.SearchEntry()

        self.search_entry.set_placeholder_text(
            "Start typing to search..."
        )

        self.search_entry.connect(
            "search-changed",
            self.on_search_changed
        )

        self.search_entry.connect(
            "activate",
            self.on_search_activate
        )

        outer.pack_start(
            self.search_entry,
            False,
            False,
            0
        )

        self.scrolled = Gtk.ScrolledWindow()

        self.scrolled.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )

        outer.pack_start(
            self.scrolled,
            True,
            True,
            0
        )

        self.workspace_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14
        )

        self.scrolled.add(self.workspace_box)

        self.refresh()

        GObject.timeout_add(2000, self.auto_refresh)

    def load_metadata(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    return json.load(f)

            except Exception:
                return {}

        return {}

    def save_metadata(self):
        os.makedirs(
            os.path.dirname(DATA_FILE),
            exist_ok=True
        )

        with open(DATA_FILE, "w") as f:
            json.dump(
                self.metadata,
                f,
                indent=2
            )

    def get_workspaces(self):
        try:
            output = subprocess.check_output(
                ["wmctrl", "-lxp"],
                text=True
            )

        except Exception as e:
            print("wmctrl error:", e)
            return {}

        workspaces = {}

        for line in output.splitlines():
            parts = line.split(None, 5)

            if len(parts) < 6:
                continue

            window_id = parts[0]
            workspace_id = parts[1]

            wm_class = parts[3]
            title = parts[5]

            if workspace_id == "-1":
                continue

            workspaces.setdefault(
                workspace_id,
                []
            ).append(
                {
                    "id": window_id,
                    "title": title,
                    "class": wm_class,
                }
            )

        return workspaces

    def switch_workspace(self, ws_id):
        subprocess.call(
            ["wmctrl", "-s", str(ws_id)]
        )

    def bring_window(self, window_id):
        subprocess.call(
            ["wmctrl", "-i", "-R", window_id]
        )

    def close_window(self, window_id):
        if not self.skip_close_confirm:
            dialog = Gtk.Dialog(
                title="Close Window?",
                transient_for=self,
                flags=0
            )

            dialog.add_button(
                "Cancel",
                Gtk.ResponseType.CANCEL
            )

            dialog.add_button(
                "Close",
                Gtk.ResponseType.OK
            )

            content = dialog.get_content_area()

            label = Gtk.Label(
                label="Close this window?"
            )

            label.set_margin_top(10)
            label.set_margin_bottom(10)

            checkbox = Gtk.CheckButton(
                label="Don't ask again this session"
            )

            content.add(label)
            content.add(checkbox)

            dialog.show_all()

            response = dialog.run()

            if checkbox.get_active():
                self.skip_close_confirm = True

            dialog.destroy()

            if response != Gtk.ResponseType.OK:
                return

        subprocess.call(
            ["wmctrl", "-ic", window_id]
        )

    def refresh(self, *_args):
        for child in self.workspace_box.get_children():
            self.workspace_box.remove(child)

        workspaces = self.get_workspaces()

        search = self.search_text.lower()

        for ws_id in sorted(
            workspaces.keys(),
            key=int
        ):
            frame = Gtk.Frame()

            outer_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=10,
                margin=12
            )

            frame.add(outer_box)

            header = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=8
            )

            title = Gtk.Label()

            title.set_markup(
                f"<b>Workspace {ws_id}</b>"
            )

            title.set_xalign(0)

            header.pack_start(
                title,
                True,
                True,
                0
            )

            switch_btn = Gtk.Button()

            switch_icon = Gtk.Image.new_from_icon_name(
                "go-jump-symbolic",
                Gtk.IconSize.BUTTON
            )

            switch_btn.add(switch_icon)

            switch_btn.set_tooltip_text(
                "Switch to workspace"
            )

            switch_btn.connect(
                "clicked",
                self.on_workspace_switch,
                ws_id
            )

            header.pack_start(
                switch_btn,
                False,
                False,
                0
            )

            outer_box.pack_start(
                header,
                False,
                False,
                0
            )

            windows_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=6
            )

            visible_count = 0

            for window in workspaces[ws_id]:
                title_lower = window["title"].lower()

                pinned = (
                    window["id"]
                    in self.pinned_windows
                )

                if search:
                    if (
                        search not in title_lower
                        and not pinned
                    ):
                        continue

                visible_count += 1

                row = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL,
                    spacing=8
                )

                wm_class = window["class"]

                candidates = [
                    c.strip()
                    for c in wm_class.split(".")
                ]

                icon_name = None

                theme = Gtk.IconTheme.get_default()

                for candidate in candidates:
                    if theme.has_icon(candidate):
                        icon_name = candidate
                        break

                if icon_name is None:
                    for candidate in candidates:
                        if theme.has_icon(candidate.lower()):
                            icon_name = candidate.lower()
                            break

                if icon_name is None:
                    icon_name = "application-x-executable"

                icon = Gtk.Image.new_from_icon_name(
                    icon_name,
                    Gtk.IconSize.MENU
                )

                label = Gtk.Label()

                label.set_text(window["title"])

                label.set_tooltip_text(
                    window["title"]
                )

                label.set_xalign(0)

                label.set_yalign(0.5)

                label.set_selectable(True)

                label.set_hexpand(True)

                label.set_halign(Gtk.Align.FILL)

                label.set_single_line_mode(True)

                label.set_ellipsize(
                    Pango.EllipsizeMode.END
                )

                pin_btn = Gtk.ToggleButton()

                pin_icon = Gtk.Image.new_from_icon_name(
                    "starred-symbolic",
                    Gtk.IconSize.MENU
                )

                pin_btn.add(pin_icon)

                pin_btn.set_active(pinned)

                pin_btn.set_tooltip_text(
                    "Pin window"
                )

                pin_btn.connect(
                    "toggled",
                    self.on_pin_toggled,
                    window["id"]
                )

                bring_btn = Gtk.Button()

                bring_icon = Gtk.Image.new_from_icon_name(
                    "go-next-symbolic",
                    Gtk.IconSize.MENU
                )

                bring_btn.add(bring_icon)

                bring_btn.set_tooltip_text(
                    "Bring window here"
                )

                bring_btn.connect(
                    "clicked",
                    self.on_bring_clicked,
                    window["id"]
                )

                close_btn = Gtk.Button()

                close_icon = Gtk.Image.new_from_icon_name(
                    "window-close-symbolic",
                    Gtk.IconSize.MENU
                )

                close_btn.add(close_icon)

                close_btn.set_tooltip_text(
                    "Close window"
                )

                close_btn.connect(
                    "clicked",
                    self.on_close_clicked,
                    window["id"]
                )

                row.pack_start(
                    icon,
                    False,
                    False,
                    0
                )

                row.pack_start(
                    label,
                    True,
                    True,
                    0
                )

                row.pack_start(
                    pin_btn,
                    False,
                    False,
                    0
                )

                row.pack_start(
                    bring_btn,
                    False,
                    False,
                    0
                )

                row.pack_start(
                    close_btn,
                    False,
                    False,
                    0
                )

                windows_box.pack_start(
                    row,
                    False,
                    False,
                    0
                )

            if visible_count == 0:
                continue

            outer_box.pack_start(
                windows_box,
                False,
                False,
                0
            )

            metadata_entry = Gtk.Entry()

            metadata_entry.set_placeholder_text(
                "Metadata / notes"
            )

            metadata_entry.set_text(
                self.metadata.get(ws_id, "")
            )

            metadata_entry.connect(
                "changed",
                self.on_metadata_changed,
                ws_id
            )

            outer_box.pack_start(
                metadata_entry,
                False,
                False,
                0
            )

            self.workspace_box.pack_start(
                frame,
                False,
                False,
                0
            )

        self.show_all()

    def on_focus_out(self, *_args):
        if not self.keep_open:
            Gtk.main_quit()

    def auto_refresh(self):
        if self.auto_refresh_enabled:
            self.refresh()

        return True

    def on_workspace_switch(
        self,
        _button,
        ws_id
    ):
        self.switch_workspace(ws_id)

        if not self.keep_open:
            Gtk.main_quit()

    def on_bring_clicked(
        self,
        _button,
        window_id
    ):
        self.bring_window(window_id)

    def on_close_clicked(
        self,
        _button,
        window_id
    ):
        self.close_window(window_id)

    def on_metadata_changed(
        self,
        entry,
        ws_id
    ):
        self.metadata[ws_id] = entry.get_text()

        self.save_metadata()

    def on_keep_toggled(self, button):
        self.keep_open = button.get_active()

    def on_auto_refresh_toggled(
        self,
        button
    ):
        self.auto_refresh_enabled = (
            button.get_active()
        )

    def on_pin_toggled(
        self,
        button,
        window_id
    ):
        if button.get_active():
            self.pinned_windows.add(window_id)
        else:
            self.pinned_windows.discard(window_id)

    def on_search_changed(self, entry):
        self.search_text = entry.get_text()

        self.refresh()

    def on_search_activate(self, entry):
        search = (
            entry.get_text()
            .strip()
            .lower()
        )

        if not search:
            return

        workspaces = self.get_workspaces()

        for ws_id in sorted(
            workspaces.keys(),
            key=int
        ):
            for window in workspaces[ws_id]:
                title = (
                    window["title"]
                    .lower()
                )

                if search in title:
                    subprocess.call(
                        [
                            "wmctrl",
                            "-ia",
                            window["id"],
                        ]
                    )

                    if not self.keep_open:
                        Gtk.main_quit()

                    return

    def on_key_press(
        self,
        _widget,
        event
    ):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

        key = Gdk.keyval_name(
            event.keyval
        )

        if not key:
            return False

        ctrl = (
            event.state
            & Gdk.ModifierType.CONTROL_MASK
        )

        if ctrl:
            return False

        if len(key) == 1 and key.isprintable():
            self.search_entry.grab_focus()

            current = self.search_entry.get_text()

            self.search_entry.set_text(
                current + key
            )

            self.search_entry.set_position(-1)

            return True

        return False


def main():
    win = WorkspaceTagger()

    win.connect(
        "destroy",
        Gtk.main_quit
    )

    win.show_all()

    Gtk.main()


if __name__ == "__main__":
    main()
