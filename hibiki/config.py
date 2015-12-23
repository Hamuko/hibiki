"""
Provides a configuration class for the Hibiki module.
"""

import os.path
import json
from .constants import DEFAULT_CONFIG_FILE_PATH, DEFAULT_LIBRARY_FILE_PATH


class HibikiConfig(object):
    """Stores the configuration data used for synchronization."""

    def __init__(self, destination=None, parent=None):
        self._destination = None
        self._library_path = None

        self.destination = destination
        self.parent = parent

        self.excludes = HibikiConfigFilters(self, filename='excludes')
        self.includes = HibikiConfigFilters(self, filename='includes')
        self.itunes_path = None
        self.max_file_count = 0
        self.random_fill = False
        self.use_subfolders = False

    @property
    def config_exists(self):
        """Returns if config file is saved."""
        return os.path.isfile(self.config_path)

    @property
    def config_folder(self):
        """Returns the path to the directory where Hibiki files are saved."""
        return os.path.join(self.destination, '.hibiki')

    @property
    def config_path(self):
        """Returns the path where the destination config file is saved."""
        return os.path.join(self.destination, DEFAULT_CONFIG_FILE_PATH)

    @property
    def destination(self):
        """Returns the destination drive for the config."""
        return self._destination

    @property
    def library_path(self):
        """Returns the path to the library file. Generates a blank file if it
        doesn't exist before.
        """
        if not self._library_path:
            self._library_path = os.path.join(self.destination,
                                              DEFAULT_LIBRARY_FILE_PATH)
            if not os.path.isfile(self._library_path):
                open(self._library_path, 'a').close()
        return self._library_path

    @destination.setter
    def destination(self, value):
        """Sets the destination drive. Throws an exception if the destination
        is not a directory or None.
        """
        if value is not None and not os.path.isdir(value):
            from .exceptions import BadDestinationError
            raise BadDestinationError(message='Destination not a directory')
        self._destination = value

    def load_config_file(self, path=None):
        """Loads the configuration from a MessagePack file. If the optional
        path argument is not given, the default configuration path is used.
        Raises InvalidConfigError if the file cannot be read as a MessagePack
        file.
        """
        if not path:
            path = self.config_path
        if not os.path.exists(path):
            from .exceptions import InvalidConfigError
            raise InvalidConfigError(message='Config file does not exist')
        with open(path, 'r') as file:
            try:
                data = json.load(file)
            except ValueError:
                from .exceptions import InvalidConfigError
                raise InvalidConfigError(message='Config cannot be read')
            else:
                self.itunes_path = data.get('itunes_path',
                                            self.itunes_path)
                self.max_file_count = data.get('max_file_count',
                                               self.max_file_count)
                self.random_fill = data.get('random_fill',
                                            self.random_fill)
                self.use_subfolders = data.get('use_subfolders',
                                               self.use_subfolders)

    def save_config_file(self, path=None):
        """Saves the configuration as a MessagePack file. If the optional path
        argument is not given, the default configuration path is used.
        """
        if not path:
            path = self.config_path
        if not os.path.exists(self.config_folder):
            os.mkdir(self.config_folder)
        data = {}
        data['itunes_path'] = self.itunes_path
        data['max_file_count'] = self.max_file_count
        data['random_fill'] = self.random_fill
        data['use_subfolders'] = self.use_subfolders
        with open(path, 'w') as file:
            json.dump(data, file, separators=(',', ':'))


class HibikiConfigFilters(object):
    """Stores lists of strings that correspond to album, artist, genre or
    playlist names.
    """

    def __init__(self, config, filename=None):
        self.config = config
        self.filename = filename

        self.albums = set()
        self.artists = set()
        self.genres = set()
        self.playlists = set()
        self.tracks = set()

    def add_album(self, name):
        """Adds an item to the album list."""
        self.albums.add(name)

    def add_artist(self, name):
        """Adds an item to the artist list."""
        self.artists.add(name)

    def add_genre(self, name):
        """Adds an item to the genre list."""
        self.genres.add(name)

    def add_playlist(self, name):
        """Adds an item to the playlist list."""
        self.playlists.add(name)

    def clear(self):
        """Resets all of the attributes to their initial states."""
        self.albums = set()
        self.artists = set()
        self.genres = set()
        self.playlists = set()
        self.tracks = set()

    def get_playlist_tracks(self):
        """Gets the iTunes track IDs from the playlists defined in
        self.playlists and saves them in the object.
        """
        for playlist in self.config.parent.itunes.playlists:
            if playlist.name in self.playlists:
                for track in playlist.tracks:
                    self.tracks.add(track)

    def is_filtered(self, track):
        """Returns True if the specified track is caught by any of the filters.
        """
        if track.album in self.albums:
            return True
        if track.artist in self.artists:
            return True
        if track.genre in self.genres:
            return True
        if track.track_id in self.tracks:
            return True
        return False

    def load_from_file(self, path=None):
        """Loads the filter rules from file and saves them into the object. If
        the path is not specified, the parent config's config_folder and the
        object's filename attributes are used jointly as the path.
        """
        if not path:
            path = os.path.join(self.config.config_folder, self.filename)
        with open(path, 'r') as file:
            try:
                data = json.load(file)
            except ValueError:
                from .exceptions import InvalidConfigError
                raise InvalidConfigError(message='Filter file cannot be read')
            else:
                for group in ['albums', 'artists', 'genres', 'playlists']:
                    items = data.get(group, [])
                    setattr(self, group, set(items))

    def save_to_file(self, path=None):
        """Saves the result from self.serialize() to file. If the path is not
        specified, the parent config's config_folder and the object's filename
        attributes are used jointly as the path.
        """
        if not path:
            path = os.path.join(self.config.config_folder, self.filename)
        with open(path, 'w') as file:
            json.dump(self.serialize(), file, separators=(',', ':'))

    def serialize(self):
        """Converts the attributes into a dictionary which can be in turn saved
        as a configuration file.
        """
        output = {}
        for group in ['albums', 'artists', 'genres', 'playlists']:
            items = getattr(self, group)
            if len(items) > 0:
                output[group] = list(items)
        return output
