"""
Submodule designed for parsing the iTunes Library.xml file for library,
playlist and track information.
"""


from datetime import datetime
from os.path import basename, join
from urllib.parse import unquote
from xml.etree import ElementTree
from .constants import TIME_FORMAT


def clean_path(path):
    """Turn the dirty path strings used in the XML file to clean and usable
    path strings.
    """
    return unquote(path.replace('file://localhost', ''))


class iTunesLibrary(object):
    """Class the represents a single iTunes Library specified by one iTunes
    Library.xml file.
    """

    def __init__(self, path):
        self.path = path

        tree = ElementTree.parse(path).getroot()[0]
        for key, value in zip(tree[::2], tree[1::2]):
            if key.text == 'Date':
                self.date = datetime.strptime(value.text, TIME_FORMAT)
            elif key.text == 'Application Version':
                self.application_version = float(value.text)
            elif key.text == 'Music Folder':
                self.music_folder = clean_path(value.text)
            elif key.text == 'Library Persistent ID':
                self.persistent_id = value.text
            elif key.text == 'Tracks':
                self._tracks = value
            elif key.text == 'Playlists':
                self._playlists = value

    @property
    def all_albums(self):
        """Returns an alphabetical list of strings containing all available
        albums in iTunes Library.
        """
        return self._get_all_track_info('album')

    @property
    def all_artists(self):
        """Returns an alphabetical list of strings containing all available
        artists in iTunes Library.
        """
        return self._get_all_track_info('artist')

    @property
    def all_genres(self):
        """Returns an alphabetical list of strings containing all available
        genres in iTunes Library.
        """
        return self._get_all_track_info('genre')

    @property
    def all_playlists(self):
        """Returns an alphabetical list of strings containing all available
        playlists in iTunes Library. Contains default iTunes playlists like
        "Music" and "Library".
        """
        playlists = set()
        for playlist in self.playlists:
            playlists.add(playlist.name)
        return sorted(list(playlists), key=lambda x: x.lower())

    @property
    def playlists(self):
        """Generator that returns iTunesPlaylist objects for each and every
        playlist in the library.
        """
        for data in self._playlists:
            yield iTunesPlaylist(data)

    @property
    def tracks(self):
        """Generator that returns iTunesTrack objects for each and every track
        in the library.
        """
        for data in self._tracks[1::2]:
            yield iTunesTrack(data, library=self)

    def track_by_persistent_id(self, persistent_id):
        """Returns track for persistent ID. If track is not found, None is returned.
        """
        for track in self.tracks:
            if track.persistent_id == persistent_id:
                return track
        return None

    def _get_all_track_info(self, name):
        items = set()
        for track in self.tracks:
            item = getattr(track, name)
            if item:
                items.add(item)
        return sorted(list(items), key=lambda x: x.lower())


class iTunesPlaylist(object):
    # pylint: disable=too-few-public-methods
    """Class that represents one playlist in the iTunes Library. The playlist
    can be a smart playlist, in which case the attribute `smart` returns True.
    """

    def __init__(self, data):
        self.master = False
        self.visible = True
        self.smart = False
        self.items = set()

        for key, value in zip(data[::2], data[1::2]):
            if key.text == 'Name':
                self.name = value.text
            elif key.text == 'Master':
                self.master = True
            elif key.text == 'Playlist ID':
                self.playlist_id = int(value.text)
            elif key.text == 'Playlist Persistent ID':
                self.persistent_id = value.text
            elif key.text == 'Visible':
                self.visible = False
            elif key.text == 'Smart Info':
                self.smart = True
            elif key.text == 'Playlist Items':
                self.items = value

    @property
    def tracks(self):
        """Generator that returns integers of the track IDs in the playlist."""
        for item in self.items:
            yield int(item[1].text)


class iTunesTrack(object):
    # pylint: disable=too-many-branches
    """Class that represents one individual track in the iTunes Library."""

    def __init__(self, data, library=None):
        self.library = library

        self.name = None
        self.artist = None
        self.album = None
        self.grouping = None
        self.album_artist = None
        self.composer = None
        self.genre = None
        self.disc_number = 0
        self.disc_count = 0
        self.track_number = 0
        self.track_count = 0
        self.year = None
        self.bpm = None
        self.gapless = False
        self.compilation = False
        self.comments = None
        self.skip_count = 0
        self.skip_date = None
        self.play_count = 0
        self.play_date = None
        self.rating = 0
        self.album_rating = 0
        self.release_date = None
        self.sort_album = None
        self.sort_album_artist = None
        self.sort_composer = None
        self.sort_artist = None
        self.sort_name = None
        self.explicit = False
        self.purchased = False

        self.get_data(data)

    def get_data(self, data):
        # pylint: disable=too-many-statements
        """Goes through all the values in the XML data and sets the properties
        accordingly.
        """
        for key, value in zip(data[::2], data[1::2]):
            if key.text == 'Track ID':
                self.track_id = int(value.text)
            elif key.text == 'Name':
                self.name = value.text
            elif key.text == 'Artist':
                self.artist = value.text
            elif key.text == 'Album Artist':
                self.album_artist = value.text
            elif key.text == 'Composer':
                self.composer = value.text
            elif key.text == 'Album':
                self.album = value.text
            elif key.text == 'Grouping':
                self.grouping = value.text
            elif key.text == 'Genre':
                self.genre = value.text
            elif key.text == 'Kind':
                self.kind = value.text
            elif key.text == 'Size':
                self.size = int(value.text)
            elif key.text == 'Total Time':
                self.time = int(value.text)
            elif key.text == 'Disc Number':
                self.disc_number = int(value.text)
            elif key.text == 'Disc Count':
                self.disc_count = int(value.text)
            elif key.text == 'Track Number':
                self.track_number = int(value.text)
            elif key.text == 'Track Count':
                self.track_count = int(value.text)
            elif key.text == 'Year':
                self.year = int(value.text)
            elif key.text == 'BPM':
                self.bpm = int(value.text)
            elif key.text == 'Date Modified':
                self.date_modified = datetime.strptime(value.text, TIME_FORMAT)
            elif key.text == 'Date Added':
                self.date_added = datetime.strptime(value.text, TIME_FORMAT)
            elif key.text == 'Bit Rate':
                self.bit_rate = int(value.text)
            elif key.text == 'Sample Rate':
                self.sample_rate = int(value.text)
            elif key.text == 'Part Of Gapless Album':
                self.gapless = True
            elif key.text == 'Compilation':
                self.compilation = True
            elif key.text == 'Comments':
                self.comments = value.text
            elif key.text == 'Skip Count':
                self.skip_count = int(value.text)
            elif key.text == 'Skip Date':
                self.skip_date = datetime.strptime(value.text, TIME_FORMAT)
            elif key.text == 'Play Count':
                self.play_count = int(value.text)
            elif key.text == 'Play Date UTC':
                self.play_date = datetime.strptime(value.text, TIME_FORMAT)
            elif key.text == 'Rating':
                self.rating = int(value.text) / 5
            elif key.text == 'Album Rating':
                self.album_rating = int(value.text) / 5
            elif key.text == 'Release Date':
                self.release_date = datetime.strptime(value.text, TIME_FORMAT)
            elif key.text == 'Sort Album':
                self.sort_album = value.text
            elif key.text == 'Sort Album Artist':
                self.sort_album_artist = value.text
            elif key.text == 'Sort Composer':
                self.sort_composer = value.text
            elif key.text == 'Sort Artist':
                self.sort_artist = value.text
            elif key.text == 'Sort Name':
                self.sort_name = value.text
            elif key.text == 'Persistent ID':
                self.persistent_id = value.text
            elif key.text == 'Explicit':
                self.explicit = True
            elif key.text == 'Purchased':
                self.purchased = True
            elif key.text == 'Location':
                self.location = clean_path(value.text)

    @property
    def filename(self):
        """Returns just the filename from the location information."""
        return basename(self.location)

    @property
    def path(self):
        """Returns the path to the track if the object has a reference to the
        master library object (which stores the path to the iTunes media
        folder). Returns None if no library reference exists.
        """
        if self.library:
            return join(self.library.music_folder, self.location)
        else:
            return None
