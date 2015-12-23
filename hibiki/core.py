"""
Provides the main Hibiki class used for the music synchronization.
"""

import json
import os
import os.path
import random
import shutil
from .config import HibikiConfig
from .itunes import iTunesLibrary


class Hibiki(object):
    """Main class used for the music syncing."""

    def __init__(self, config=None):
        self._subfolder = 0
        self.itunes = None
        self.tracks = set()

        if config:
            self.config = config
            self.config.parent = self
            self.update_itunes()
        else:
            self.config = HibikiConfig(parent=self)

    @property
    def library_data(self):
        """Returns the JSON data written in the library file."""
        with open(self.config.library_path, 'r') as file:
            try:
                return json.load(file)
            except ValueError:
                return {}

    @library_data.setter
    def library_data(self, value):
        with open(self.config.library_path, 'w') as file:
            json.dump(value, file, separators=(',', ':'))

    @property
    def target_directory(self):
        """Returns the target directory for file copy operations. If
        config.use_subfolders is set to False, always returns the destination
        folder. Else it returns the first folder that has less than the maximum
        allowed amount of files. The last non-full folder is saved in
        _subfolder so that full directories don't get checked again.
        Filenames starting with '.' are ignored.
        """
        if self.config.use_subfolders:
            while True:
                directory = os.path.join(self.config.destination,
                                         str(self._subfolder))
                if os.path.isdir(directory):
                    file_count = 0
                    for file in os.listdir(directory):
                        if file[0] != '.':
                            file_count += 1
                    if file_count < self.config.max_file_count:
                        return directory
                    else:
                        self._subfolder += 1
                else:
                    os.makedirs(directory)
                    return directory
        else:
            return self.config.destination

    def _copy_file(self, track):
        """Performs the file copy operation."""
        destination_path = os.path.join(self.target_directory, track.filename)
        with open(track.path, 'rb') as fin:
            with open(destination_path, 'wb') as fout:
                shutil.copyfileobj(fin, fout)
        return destination_path

    def _clean_sync_list(self, delete_callback=None, error_callback=None):
        """Removes all the tracks not present in the sync list from destination
        and removes tracks from the sync list if already present on the
        destination.
        """
        library = self.library_data
        for track in library.copy():
            if track in self.tracks:
                self.tracks.remove(track)
            else:
                path = os.path.join(self.config.destination, library[track])
                try:
                    os.remove(path)
                except FileNotFoundError as error:
                    if error_callback:
                        error_callback(path, error)
                    continue
                if delete_callback:
                    data = self.itunes.track_by_persistent_id(track)
                    if not data:
                        data = library[track]
                    delete_callback(data)
                del library[track]
        self.library_data = library

    def _mark_file(self, track, destination):
        """Writes the file persistant ID and path into to library file."""
        data = self.library_data
        data[track.persistent_id] = os.path.relpath(destination,
                                                    self.config.destination)
        self.library_data = data

    def calculate_space(self):
        """Calculates the available space if all the tracks in the library were
        to be removed.
        """
        available = self.space_available()
        library = self.library_data
        for track in library.copy():
            path = self.full_library_path(library[track])
            try:
                stat = os.stat(path)
            except FileNotFoundError:
                del library[track]
            else:
                available += stat.st_size
        self.library_data = library
        return available

    def copy_tracks(self, after_callback=None, before_callback=None,
                    error_callback=None, end_signal=None):
        """Goes through the tracks in the iTunes library and copies the tracks
        onto the destination. before_callback and after_callback are called
        with the track object if they are set before and after the copy process
        respectively. The copying process will last until the track list has
        been exhausted or the end_signal is True.
        """
        track_iterator = self.itunes.tracks
        if not end_signal:
            end_signal = False
        while not end_signal:
            try:
                track = next(track_iterator)
            except StopIteration:
                return
            if track.persistent_id in self.tracks:
                if before_callback:
                    before_callback(track)
                try:
                    destination = self._copy_file(track)
                except OSError as error:
                    os.remove(destination)
                    if error_callback:
                        error_callback(track, error)
                        continue
                self._mark_file(track, destination)
                if after_callback:
                    after_callback(track)

    def full_library_path(self, track):
        """Returns the full path for the relative library paths."""
        return os.path.join(self.config.destination, track)

    def generate_sync_list(self, delete_callback=None, error_callback=None):
        """Generates a set of the items to be synced using the iTunes
        persistent IDs and the available space on the target destination if all
        the current tracks were to be deleted. Adds random items to the sync
        list if config.random_fill returns True.
        """
        space = self.calculate_space()
        self.config.excludes.get_playlist_tracks()
        self.config.includes.get_playlist_tracks()

        for track in self.itunes.tracks:
            if self.config.excludes.is_filtered(track):
                continue
            if self.config.includes.is_filtered(track):
                if space >= track.size:
                    space -= track.size
                    self.tracks.add(track.persistent_id)

        if self.config.random_fill:
            random.seed()
            music = list(self.itunes.tracks)
            while len(music) > 0:
                track = random.sample(music, 1)[0]
                if not self.config.excludes.is_filtered(track):
                    if track.persistent_id not in self.tracks:
                        if space >= track.size:
                            space -= track.size
                            self.tracks.add(track.persistent_id)
                music.remove(track)

        self._clean_sync_list(delete_callback=delete_callback,
                              error_callback=error_callback)

    def space_available(self, reserve=5):
        """Returns the number of available bytes on the target destination.
        Reserves 5 MB of free space by default on the drive just in case.
        """
        drive_stats = os.statvfs(self.config.destination)
        space = drive_stats.f_bavail * drive_stats.f_frsize
        return space - (reserve * 1024 * 1024)

    def update_itunes(self):
        """Sets the self.itunes instance to a new iTunesLibrary object found in
        the path defined by the self.config object.
        """
        self.itunes = iTunesLibrary(self.config.itunes_path)
