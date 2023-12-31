#!/usr/bin/python
from __future__ import print_function
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Keybinder', '3.0')

from gi.repository import Gtk, GdkPixbuf, Wnck, Keybinder, Gdk, GdkX11
import re
try:
    import ConfigParser
except ImportError:
    import configparser
import os
import signal

class FuzzyMatcher():

    def __init__(self):
        self.pattern = ''

    def setPattern(self, pattern):
        self.pattern = re.compile('.*?'.join(map(re.escape, list(pattern))))

    def score(self, string):
        match = self.pattern.search(string)
        if match is None:
            return 0
        else:
            return 100.0 * (1.0/(1 + match.start()) + 1.2/(match.end() - match.start() + 1))


class WindowList():

    def __init__(self, ignored_windows, always_show_windows, ignored_window_types):
        self.windowList = []
        self.previousWindow = None
        self.fuzzyMatcher = FuzzyMatcher()
        self.ignored_windows = ignored_windows
        self.always_show_windows = always_show_windows
        self.ignored_window_types = ignored_window_types

    def refresh(self):
        # Clear existing
        self.windowList = []

        # Get the screen and force update
        screen = Wnck.Screen.get_default()
        screen.force_update()

        # Get previous active window
        self.previousWindow = screen.get_active_window()

        # Get a list of windows
        window_list = screen.get_windows()
        for i in window_list:
            # Filter out extraneous windows
            name = i.get_name()
            window_type = i.get_window_type()
            class_group = i.get_class_group_name()

            if self.isWindowAlwaysShown(name):
                pass
            else:
                if window_type in self.ignored_window_types:
                    continue

                if self.isWindowIgnored(name):
                    continue

            self.windowList.append({
                'name': name,
                'icon': i.get_icon(),
                'class_group': class_group,
                'window': i, 'rank': 0
            })

    def getLatest(self):
        self.refresh()
        return self.windowList

    def get(self):
        return self.windowList

    def getHighestRanked(self):
        if (len(self.windowList)):
            return self.windowList[0]

        return None

    def rank(self, text):
        self.fuzzyMatcher.setPattern(text.lower())
        for i in self.windowList:
            score = self.fuzzyMatcher.score(i['name'].lower())
            if i['class_group']:
                score += self.fuzzyMatcher.score(i['class_group'].lower())
            i['rank'] = score

        self.windowList.sort(key=lambda x: x['rank'], reverse=True)

    def getPreviousWindow(self):
        return self.previousWindow

    def isWindowIgnored(self, window_title):
        for pattern in self.ignored_windows:
            if pattern.search(window_title) is not None:
                return True

        return False

    def isWindowAlwaysShown(self, window_title):
        for pattern in self.always_show_windows:
            if pattern.search(window_title) is not None:
                return True

        return False


class FuzzyWindow(Gtk.Window):

    def __init__(self, config):
        Gtk.Window.__init__(self, title='Fuzzy Windows')

        # Window is initially hidden
        self.hidden = True

        # Set up the vbox
        self.vbox = Gtk.Box(spacing=10)
        self.vbox.set_orientation(Gtk.Orientation.VERTICAL)
        self.add(self.vbox)

        # Set up the box to enter an app name
        self.enteredName = Gtk.Entry()
        self.vbox.pack_start(self.enteredName, True, True, 0)

        # Create a store for data
        self.appListStore = Gtk.ListStore(str, GdkPixbuf.Pixbuf)
        # Create a view for the data
        self.appListView = Gtk.TreeView(self.appListStore)
        self.appListView.set_headers_visible(False)

        # Create the necessary columns
        columnIcon = Gtk.TreeViewColumn("Icon")
        cellIcon = Gtk.CellRendererPixbuf()
        columnIcon.pack_start(cellIcon, False)
        columnIcon.add_attribute(cellIcon, "pixbuf", 1)
        self.appListView.append_column(columnIcon)

        columnAppName = Gtk.TreeViewColumn("App Name")
        cellAppName = Gtk.CellRendererText()
        columnAppName.pack_start(cellAppName, False)
        columnAppName.add_attribute(cellAppName, "text", 0)
        self.appListView.append_column(columnAppName)

        # Add the list box to the window
        scrolledWindow = Gtk.ScrolledWindow()
        scrolledWindow.set_size_request(
            config.width,
            config.height
        )
        scrolledWindow.add(self.appListView)
        self.vbox.pack_start(scrolledWindow, True, True, 0)

        # Initialize window list
        self.windowList = WindowList(
            config.ignored_windows,
            config.always_show_windows,
            config.ignored_window_types
        )

        # Register events
        self.enteredName.connect("changed", self.enteredNameChanged)
        self.connect("key-press-event", self.keypress)
        self.appListView.connect("row-activated", self.presentManual)

        # Populate initially
        self.populate(self.windowList.getLatest())

    def populate(self, items):
        self.appListStore.clear()
        for i in items:
            self.appListStore.append([i['name'], i['icon']])

    def enteredNameChanged(self, entry):
        text = entry.get_text()
        if text:
            self.windowList.rank(text)
            self.populate(self.windowList.get())

    def presentWindow(self, window):
        workspace = window.get_workspace()
        if workspace is not None:
            workspace.activate(self.getXTime())

        window.activate(self.getXTime())

    def presentHighestRanked(self):
        highestRanked = self.windowList.getHighestRanked()
        if highestRanked is not None:
            self.presentWindow(highestRanked['window'])

    def presentManual(self, view, path, column):
        indices = path.get_indices()
        if len(indices) < 1:
            return

        index = indices[0]
        windows = self.windowList.get()
        if index < len(windows):
            self.toggle()
            self.presentWindow(windows[index]['window'])

    def keypress(self, widget, event):
        selected = self.appListView.get_selection().get_selected()
        if event.keyval == Gdk.KEY_Escape:
            self.toggle()
        elif event.keyval == Gdk.KEY_Return and selected[1] is None:
            self.toggle()
            self.presentHighestRanked()

    def toggle(self):
        if self.hidden:
            # Set state
            self.hidden = False
            self.show_all()

            # Clear out the text field
            self.enteredName.set_text('')
            self.enteredName.grab_focus()

            # Populate windows
            self.windowList.refresh()
            self.populate(self.windowList.get())

            # Show our window with focus
            self.stick()

            time = self.getXTime()

            self.get_window().show()
            self.get_window().focus(time)
        else:
            self.hidden = True
            self.get_window().hide()

    def hotkey(self, key, data):
        self.toggle()

    def getXTime(self):
        try:
            time = GdkX11.x11_get_server_time(self.get_window())
        except:
            time = 0

        return time


class Config:

    def __init__(self):
        try:
            self.config = ConfigParser.ConfigParser()
        except NameError:
            self.config = configparser.ConfigParser()
        self.config.read([
            os.path.expanduser('~/.config/fuzzy-windows.conf'),
            os.path.expanduser('~/.config/.fuzzy-windows'),
            os.path.expanduser('~/fuzzy-windows.conf'),
            os.path.expanduser('~/.fuzzy-windows')
        ])

        self.loadOptions()

    def loadOptions(self):
        self.hotkey = self.getOption('hotkey', '<Ctrl>space')
        self.ignored_windows = self.prepareIgnoredWindows(
            self.getOption('ignored_windows', [])
        )
        self.always_show_windows = self.prepareAlwaysShowWindows(
            self.getOption('always_show_windows', [])
        )
        self.width = int(self.getOption('width', 700))
        self.height = int(self.getOption('height', 200))
        self.ignored_window_types = self.getIgnoredWindowTypes()

    def getOption(self, option_name, default_value):
        if self.config.has_option('DEFAULT', option_name):
            return self.config.get('DEFAULT', option_name)
        else:
            return default_value

    def prepareIgnoredWindows(self, ignored_windows):
        return self.splitAndCompileWindowRegexes(ignored_windows)

    def prepareAlwaysShowWindows(self, always_show_windows):
        return self.splitAndCompileWindowRegexes(always_show_windows)

    def splitAndCompileWindowRegexes(self, windows):
        # Turn window str into a list
        if type(windows) is str:
            windows = filter(None, windows.split("\n"))

        # Now, turn each of the window names into a regex pattern
        for i in range(0, len(windows)):
            windows[i] = re.compile(windows[i])

        return windows

    def getIgnoredWindowTypes(self):
        window_types = {
            'normal': {'window_type': Wnck.WindowType.NORMAL},
            'desktop': {'window_type': Wnck.WindowType.DESKTOP},
            'dock': {'window_type': Wnck.WindowType.DOCK},
            'dialog': {'window_type': Wnck.WindowType.DIALOG},
            'toolbar': {'window_type': Wnck.WindowType.TOOLBAR},
            'menu': {'window_type': Wnck.WindowType.MENU},
            'utility': {'window_type': Wnck.WindowType.UTILITY},
            'splashscreen': {'window_type': Wnck.WindowType.SPLASHSCREEN},
        }

        ignored_window_types = []

        for window_type in window_types:
            should_show = bool(int(self.getOption('show_windows_' + window_type, True)))
            if not should_show:
                ignored_window_types.append(window_types[window_type]['window_type'])

        return ignored_window_types

# Catch SIGINT signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Load the configuration with defaults
config = Config()

# Create the window and set attributes
win = FuzzyWindow(config)
win.connect("delete-event", Gtk.main_quit)
win.set_position(Gtk.WindowPosition.CENTER)
win.set_keep_above(True)
win.set_skip_taskbar_hint(True)
win.set_decorated(False)

# Set the hotkey
Keybinder.init()
if not Keybinder.bind(config.hotkey, win.hotkey, None):
    print("Could not bind the hotkey:", config.hotkey)
    exit()

# The main loop
Gtk.main()
