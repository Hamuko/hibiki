"""
Command-line application for iTunes music syncing to file system locations
built using urwid, a console user interface library for Python.
"""


from math import floor
import threading
import time
import urwid
import hibiki


def exit_hibiki_cb(*args):
    """Exits the application loop neatly."""
    raise urwid.ExitMainLoop()


def generate_hotkeys(hotkeys):
    """Generates hotkey help text for footer from strings by displaying the
    first character of the string with different styling.
    """
    key_help = []
    for hotkey in hotkeys:
        text = urwid.Text([('hotkey', hotkey[0]), hotkey[1:]], align='right')
        key_help.append(('pack', text))
    return key_help


class HibikiCLI(object):
    """The main class for the command-line application."""

    PALETTE = [
        ('error', 'dark red,bold', 'default'),
        ('footer', 'white', 'dark gray'),
        ('header', 'black', 'white'),
        ('hotkey', 'dark red,bold', 'dark gray'),
        ('input_label', 'white', 'dark red'),
        ('pending', 'yellow', 'default'),
        ('prompt', 'black', 'light gray'),
        ('success', 'dark green', 'default'),
        ('track', 'default,bold', 'default')
    ]

    def __init__(self, hibiki_object):
        self.hibiki = hibiki_object

        self._footer_widget = None
        self.body = None
        self.clock_running = True
        self.loop = None
        self.setting_index = 0
        self.start_time = 0

        self._init_header()
        self._init_footer()
        self.open_settings()

    @property
    def footer_widget(self):
        """Returns the footer widget, which is either None or a widget wrapped
        with the attribute 'footer'.
        """
        return self._footer_widget

    @footer_widget.setter
    def footer_widget(self, value):
        """Sets the footer_widget wrapped with attribute 'footer'."""
        self._footer_widget = urwid.AttrWrap(value, 'footer')

    @property
    def frame(self):
        """Returns a frame with the header and footers correctly set."""
        return urwid.Frame(self.body,
                           header=self.header_widget,
                           footer=self.footer_widget)

    def _init_footer(self):
        """Initializes the footer bar used with Hibiki CLI with a blank Text widget.
        """
        self.footer_text = urwid.Text('')
        self.footer_widget = urwid.Padding(self.footer_text, left=1, right=1)

    def _init_header(self):
        """Initializes the header bar used with Hibiki CLI with the three header Text
        widgets: application title, activity title and clock.
        """
        self.application_title = urwid.Text('hibiki', align='left')
        self.clock = urwid.Text('00:00:00', align='right')
        self.title = urwid.Text('', align='center')
        widgets = [('fixed', 8, self.application_title),
                   self.title,
                   ('fixed', 8, self.clock)]
        header = urwid.Padding(urwid.Columns(widgets), left=1, right=1)
        self.header_widget = urwid.AttrWrap(header, 'header')

    def main(self):
        """Starts the application by initializing and running the main loop."""
        self.loop = urwid.MainLoop(self.frame, HibikiCLI.PALETTE)
        self.loop.run()

    def open_copy(self):
        """Initializes a new CopyScreen (inherits from urwid.ListBox) as the
        body, which starts performing the main copying.
        """
        self.hibiki.config.includes.save_to_file()
        self.hibiki.config.excludes.save_to_file()
        self.body = CopyScreen(self)
        self.update()
        self.start_clock()

    def open_selection(self):
        """Initializes a new SelectionPrompt (inherits from urwid.ListBox) as
        the body, which iterates through all the include and exclude options.
        """
        self.body = LoadingOverlay(self)
        self.update()
        update = threading.Thread(target=self.update_itunes)
        update.daemon = True
        update.start()

    def open_settings(self):
        """Initializes a new SettingsPrompt (inherits from urwid.Overlay) as
        the body, which contains the widgets and methods for the settings
        prompt.
        """
        self.title.set_text('SETTINGS')
        self.body = SettingsPrompt(self)

    def refresh_clock_cb(self, loop=None, data=None):
        """Updates the clock text in the header bar and sets the application
        loop to run itself again after one second, thus looping indefinitely
        until the application is terminated..
        """
        if self.clock_running:
            elapsed = floor(time.time() - self.start_time)
            self.clock.set_text('{:02d}:{:02d}:{:02d}'
                                .format(elapsed // 3600,
                                        elapsed % 3600 // 60,
                                        elapsed % 60))
            loop.set_alarm_in(1, self.refresh_clock_cb)

    def start_clock(self):
        """Initializes the start time and sets to refresh the clock in 1 second
        via the refresh_clock() method, which in return will set the loop to
        refresh itself every 1 second.
        """
        self.start_time = time.time()
        self.loop.set_alarm_in(1, self.refresh_clock_cb)

    def update(self):
        """Resets the main loop's widget to the object's frame attribute."""
        self.loop.widget = self.frame
        self.loop.draw_screen()

    def update_itunes(self):
        """Updates the iTunes instance and opens up the selection prompt after.
        Ran in a thread while the loading overlay runs in the main thread.
        """
        self.hibiki.update_itunes()
        self.body = SelectionPrompt(self)
        self.update()


class CopyScreen(urwid.ListBox):
    """Main screen of the application. It generates an empty listbox and
    populates it with info about the copying process as the run() method
    processes in its own thread. The listbox has disabled movement and will
    always focus on the last added line.
    """

    def __init__(self, parent):
        self.parent = parent

        self.current_text = None
        self.errors = 0
        self.item_count = 0
        self.processed = 0
        self.quit = False

        self._init_footer()

        self.body = urwid.SimpleListWalker([])
        super().__init__(self.body)

        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def _init_footer(self):
        """Initializes the footer with the help text and status bar and then
        sets it as the footer in the parent object.
        """
        self.status_text = urwid.Text('')
        self.update_statusbar()
        key_help = generate_hotkeys(['quit'])
        widgets = [self.status_text] + key_help
        footer = urwid.Padding(urwid.Columns(widgets, dividechars=2),
                               left=1, right=1)
        self.parent.footer_widget = footer

    def add_text(self, text):
        """Adds text to the widget and moves focus. The text for the urwid.Text
        widget is received by inputting data tuple to the formatter function.
        """
        try:
            focus = self.focus_position
        except IndexError:
            focus = -1
        self.current_text = urwid.Text(text, wrap='clip')
        self.body.append(self.current_text)
        self.body.set_focus(focus + 1)

    def after_copy(self, track):
        """Callback method after a track is copied. Changes the line to say
        that the item was copied and updates the status bar.
        """
        self.current_text.set_text(self.format_track(track, 1))
        self.processed += 1
        self.update_statusbar()

    def after_delete(self, data):
        """Callback method after a track is deleted. Adds an information line
        for the deleted track.
        """
        if isinstance(data, hibiki.iTunesTrack):
            text = self.format_track(data, 2)
        else:
            text = self.format_text(data, 2)
        self.add_text(text)

    def before_copy(self, track):
        """Callback method before a track is copied. Adds a line to the listbox
        and focuses it.
        """
        text = self.format_track(track, 0)
        self.add_text(text)

    def error(self, data, error):
        """Callback method after an error occurs. Adds an error line and
        updates the statusbar.
        """
        text = ''
        if isinstance(error, OSError):
            if error.args[0] == 2:
                text = '(file not found) '
            elif error.args[0] == 28:
                text = '(insufficient space) '
        if isinstance(data, hibiki.iTunesTrack):
            data_text = self.format_track(data, 2)
        else:
            data_text = self.format_text(data, 2)
        self.current_text.set_text([text, data_text])
        self.errors += 1
        self.update_statusbar()

    def exit(self):
        """Cleanly exits the process."""
        self.quit = True
        self.thread.join()
        exit_hibiki_cb()

    def format_text(self, text, state):
        """Returns text markup for the widget based on string and state provided.
        """
        prefix = ''
        state_text = ('default', ' > ')
        if state == -1:
            prefix = 'err'
            state_text = ('error', ' < ')
        elif state == 2:
            prefix = 'del'
            state_text = ('error', ' > ')
        width = max(3, len(str(self.item_count)))
        return ['{prefix:>{width}}'.format(prefix=prefix, width=width),
                state_text, text]

    def format_track(self, track, state):
        """Returns text markup for the widget based on the track info and state
        provided.
        """
        prefix = str(self.processed + 1)
        if state == -1:
            prefix = 'err'
            state_text = ('error', ' < ')
        elif state == 0:
            state_text = ('pending', ' < ')
        elif state == 1:
            state_text = ('success', ' > ')
        elif state == 2:
            prefix = 'del'
            state_text = ('error', ' > ')
        width = max(3, len(str(self.item_count)))
        return ['{prefix:>{width}}'.format(prefix=prefix, width=width),
                state_text, ('track', track.name), ' by ',
                ('track', track.artist)]

    def keypress(self, size, key):
        """Overrides the default keypress() method in urwid.ListBox to capture
        the custom keypresses. Does not call the super().keypress() method in
        order to disable moving in the listbox.
        """
        if key == 'q':
            exit_hibiki_cb()

    def run(self):
        """Main logic of the command-line application. It generates a list of
        the items to be synced and then starts the copying process, attaching
        the after_copy and before_copy methods as callbacks.
        """
        self.parent.title.set_text('PREPARING COPY')
        self.parent.hibiki.generate_sync_list(
            delete_callback=self.after_delete,
            error_callback=self.error
        )
        self.parent.title.set_text('COPYING')
        self.item_count = len(self.parent.hibiki.tracks)
        self.parent.hibiki.copy_tracks(before_callback=self.before_copy,
                                       after_callback=self.after_copy,
                                       error_callback=self.error,
                                       end_signal=self.quit)
        self.parent.title.set_text('FINISHED')
        self.parent.clock_running = False

    def update_statusbar(self):
        """Sets the status bar text to the current number of processed items
        and total item count."""
        if self.errors > 0:
            text = ('{s.processed}/{s.item_count} copied, {s.errors} errors'
                    .format(s=self))
        else:
            text = ('{s.processed}/{s.item_count} copied'
                    .format(s=self))
        self.status_text.set_text(text)


class LoadingOverlay(urwid.Overlay):
    """Simple loading bar with animated dots to avoid frozen interface."""

    def __init__(self, parent):
        self.parent = parent
        self.dots = 0
        super().__init__(self.body(), urwid.SolidFill(),
                         align='center', width=14,
                         valign='middle', height=3)
        self.parent.loop.set_alarm_in(0.5, self.update_cb)

    def body(self):
        """Generates the body for the overlay."""
        self.text = urwid.Text('LOADING')
        body = urwid.ListBox([urwid.Divider(), self.text])
        padded = urwid.Padding(body, left=2, right=2)
        return urwid.AttrMap(padded, 'prompt')

    def update_cb(self, loop=None, data=None):
        """Animates the dots, going from 0 to 3 dots and then back, updating
        every 0.5 seconds.
        """
        if self.dots < 3:
            self.dots += 1
        else:
            self.dots = 0
        self.text.set_text('LOADING{}'.format(self.dots * '.'))
        loop.set_alarm_in(0.5, self.update_cb)


class SelectionOption(object):
    """Class used with SelectionPrompt to provide data and methods for the
    particular screens.
    """

    def __init__(self, title=None, items=None, add_method=None, source=None):
        self.add_method = add_method
        self.items = items
        self.title = title
        self.source = source

    def add(self, value):
        """Alias for the add_method."""
        self.add_method(value)


class SelectionPrompt(urwid.ListBox):
    """Class used to display and save the include/exclude settings in Hibiki CLI.
    """

    def __init__(self, parent):
        self.parent = parent

        self.index = 0
        self.item_count = 0
        self.options = []
        self.selected = 0

        self._init_footer()
        self._init_options()

        self.body = urwid.SimpleFocusListWalker([])
        super().__init__(self.body)
        self.generate_checkboxes()

    @property
    def checkboxes(self):
        """Generates all the checkboxes present in the widget by returning the
        original_widget attributes from the self.body AttrMaps.
        """
        for wrap in self.body:
            yield wrap.original_widget

    def _init_footer(self):
        """Initializes the footer with the help texts and status bar and then
        sets it as the footer in the parent object.
        """
        self.status_text = urwid.Text('')
        key_help = generate_hotkeys(['skip', 'continue', 'reset', 'quit'])
        widgets = [self.status_text] + key_help
        footer = urwid.Padding(urwid.Columns(widgets, dividechars=2),
                               left=1, right=1)
        self.parent.footer_widget = footer

    def _init_options(self):
        """Initializes the option screen data and attempts to load the includes
        and excludes from file.
        """
        try:
            self.parent.hibiki.config.includes.load_from_file()
        except (FileNotFoundError, hibiki.exceptions.InvalidConfigError):
            pass
        try:
            self.parent.hibiki.config.excludes.load_from_file()
        except (FileNotFoundError, hibiki.exceptions.InvalidConfigError):
            pass
        options = [['INCLUDE ARTISTS',
                    self.parent.hibiki.itunes.all_artists,
                    self.parent.hibiki.config.includes.add_artist,
                    self.parent.hibiki.config.includes.artists],
                   ['INCLUDE ALBUMS',
                    self.parent.hibiki.itunes.all_albums,
                    self.parent.hibiki.config.includes.add_album,
                    self.parent.hibiki.config.includes.albums],
                   ['INCLUDE GENRES',
                    self.parent.hibiki.itunes.all_genres,
                    self.parent.hibiki.config.includes.add_genre,
                    self.parent.hibiki.config.includes.genres],
                   ['INCLUDE PLAYLISTS',
                    self.parent.hibiki.itunes.all_playlists,
                    self.parent.hibiki.config.includes.add_playlist,
                    self.parent.hibiki.config.includes.playlists],
                   ['EXCLUDE ARTISTS',
                    self.parent.hibiki.itunes.all_artists,
                    self.parent.hibiki.config.excludes.add_artist,
                    self.parent.hibiki.config.excludes.artists],
                   ['EXCLUDE ALBUMS',
                    self.parent.hibiki.itunes.all_albums,
                    self.parent.hibiki.config.excludes.add_album,
                    self.parent.hibiki.config.excludes.albums],
                   ['EXCLUDE GENRES',
                    self.parent.hibiki.itunes.all_genres,
                    self.parent.hibiki.config.excludes.add_genre,
                    self.parent.hibiki.config.excludes.genres],
                   ['EXCLUDE PLAYLISTS',
                    self.parent.hibiki.itunes.all_playlists,
                    self.parent.hibiki.config.excludes.add_playlist,
                    self.parent.hibiki.config.excludes.playlists]]
        for kwargs in options:
            option = SelectionOption(*kwargs)
            self.options.append(option)

    def generate_checkboxes(self):
        """Generates a list of checkboxes based on the self.options and
        self.index. If the self.index is out of range, the open_copy() method
        is called from parent to continue application execution.
        """
        try:
            options = self.options[self.index]
        except IndexError:
            self.parent.open_copy()
            return
        self.item_count = len(options.items)
        self.parent.title.set_text(options.title)
        self.body.clear()
        for choice in options.items:
            box = urwid.CheckBox(choice)
            if choice in options.source:
                self.selected += 1
                box.set_state(True)
            urwid.connect_signal(box, 'change', self.update_statusbar_cb)
            self.body.append(urwid.AttrMap(box, None, focus_map='reversed'))
        options.source.clear()
        self.update_statusbar_cb()

    def keypress(self, size, key):
        """Overrides the default keypress() method in urwid.ListBox to capture
        the custom keypresses. If the pressed key is not one of the custom
        keys, the original keypress function is called instead.
        """
        if key == 'c':
            self.save()
        elif key == 'q':
            exit_hibiki_cb()
        elif key == 'r':
            self.reset_list()
        elif key == 's':
            self.skip()
        else:
            super().keypress(size, key)

    def reset_list(self):
        """Iterates through the checkboxes and sets all of the states to False.
        """
        for checkbox in self.checkboxes:
            checkbox.set_state(False)

    def save(self):
        """Saves the include/exclude settings after user decides to continue
        from one list.
        """
        for checkbox in self.checkboxes:
            if checkbox.state:
                self.options[self.index].add(checkbox.get_label())
        self.index += 1
        self.selected = 0
        self.generate_checkboxes()

    def skip(self):
        """Skips all the remaining option screens. Performs the save method as
        the include/exclude lists are cleared in the generate_checkboxes method
        and only get a value again during the save method.
        """
        while True:
            try:
                self.save()
            except IndexError:
                break

    def update_statusbar_cb(self, widget=None, state=None):
        """Updates the number of selected items in the footer."""
        if state is True:
            self.selected += 1
        elif state is False:
            self.selected -= 1
        self.status_text.set_text('{s.selected}/{s.item_count} items selected'
                                  .format(s=self))


class SettingsPrompt(urwid.Overlay):
    """Overlay for the initial settings for Hibiki CLI."""

    def __init__(self, parent):
        self.parent = parent
        self.config = parent.hibiki.config

        self.cancel_button = None
        self.destination = None
        self.itunes_path = None
        self.max_file_count = None
        self.random_fill = None
        self.reset_button = None
        self.save_button = None
        self.use_subfolders = None

        super().__init__(self.body(), urwid.SolidFill(),
                         align='center', width=('relative', 90),
                         valign='middle', height=9)

    def body(self):
        """Initializes the body by pulling a list containing return values from
        all the prompt methods and generates a ListBox with the right padding
        and corrent palette options from the widget list.
        """
        items = [urwid.Divider(),
                 self.destination_prompt(),
                 self.itunes_path_prompt(),
                 self.random_fill_prompt(),
                 self.use_subfolders_prompt(),
                 self.max_file_count_prompt(),
                 urwid.Divider(),
                 self.button_row()]
        listing = urwid.ListBox(urwid.SimpleFocusListWalker(items))
        options = urwid.Padding(listing, right=2, left=2)
        return urwid.AttrMap(options, 'prompt')

    def button_row(self):
        """Generates SAVE, RESET and EXIT buttons, connects the click signals
        to appropriate methods and returns them in a GridFlow.
        """
        self.save_button = urwid.Button('SAVE')
        urwid.connect_signal(self.save_button, 'click', self.save_config_cb)
        self.reset_button = urwid.Button('RESET')
        urwid.connect_signal(self.reset_button, 'click',
                             self.reset_configuration)
        self.cancel_button = urwid.Button('EXIT')
        urwid.connect_signal(self.cancel_button, 'click', exit_hibiki_cb)
        return urwid.GridFlow([self.reset_button,
                               self.save_button,
                               self.cancel_button], 9, 2, 1, 'center')

    def destination_prompt(self):
        """Generates a destination prompt and connects it to self.get_config_cb().
        """
        label = urwid.Text(('input_label', ' DESTINATION PATH '))
        self.destination = urwid.Edit(caption=' ', edit_text='')
        urwid.connect_signal(self.destination, 'change', self.get_config_cb)
        return urwid.Columns([('pack', label), self.destination])

    def get_config_cb(self, widget=None, new_text=None):
        """Attempts to load the configuration for all the other elements from
        the destination prompt. Resets the other elements if the input is a bad
        directory or no config file is found.
        """
        try:
            self.config.destination = new_text
        except hibiki.exceptions.BadDestinationError:
            self.reset_configuration(reset_destination=False)
            return
        try:
            self.config.load_config_file()
        except hibiki.exceptions.InvalidConfigError:
            self.reset_configuration(reset_destination=False)
        else:
            self.itunes_path.set_edit_text(self.config.itunes_path)
            self.use_subfolders.set_state(self.config.use_subfolders)
            self.random_fill.set_state(self.config.random_fill)
            self.max_file_count.set_edit_text(str(self.config.max_file_count))

    def itunes_path_prompt(self):
        """Generates an iTunes Library.xml path prompt."""
        label = urwid.Text(('input_label', ' iTunes Library.xml PATH '))
        self.itunes_path = urwid.Edit(caption=' ', edit_text='')
        return urwid.Columns([('pack', label), self.itunes_path])

    def max_file_count_prompt(self):
        """Generates a max file count prompt that only accepts integers."""
        label = urwid.Text(('input_label', ' MAX FILE COUNT PER SUBFODLER '))
        self.max_file_count = urwid.IntEdit()
        return urwid.Columns([('pack', label), self.max_file_count],
                             dividechars=1)

    def random_fill_prompt(self):
        """Generates a random fill checkbox."""
        label = urwid.Text(('input_label', ' USE RANDOM FILL '))
        self.random_fill = urwid.CheckBox('')
        return urwid.Columns([('pack', label), self.random_fill],
                             dividechars=1)

    def reset_configuration(self, reset_destination=True):
        """Resets the configuration. Optionally reset_destination can be set to
        false to keep it from reseting, which is useful for the
        get_config_cb() method.
        """
        if reset_destination:
            self.destination.set_edit_text('')
        self.itunes_path.set_edit_text('')
        self.use_subfolders.set_state(False)
        self.random_fill.set_state(False)
        self.max_file_count.set_edit_text('')

    def save_config_cb(self, *args):
        """Copies the values from the prompts and saves the configuration file.
        """
        self.config.destination = self.destination.edit_text
        self.config.itunes_path = self.itunes_path.edit_text
        self.config.max_file_count = self.max_file_count.value()
        self.config.random_fill = self.random_fill.get_state()
        self.config.use_subfolders = self.use_subfolders.get_state()
        self.config.save_config_file()
        self.parent.open_selection()

    def use_subfolders_prompt(self):
        """Generates a use subfolders checkbox."""
        label = urwid.Text(('input_label', ' USE SUBFOLDERS '))
        self.use_subfolders = urwid.CheckBox('')
        return urwid.Columns([('pack', label), self.use_subfolders],
                             dividechars=1)


def main():
    """Initializes a Hibiki object and starts executing the CLI object."""
    main_hibiki = hibiki.Hibiki()
    HibikiCLI(main_hibiki).main()


if __name__ == "__main__":
    main()
