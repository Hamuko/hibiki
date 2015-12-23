"""
Hibiki is a module used for syncing iTunes tracks to file system directories
with user-defined rules, similar to the iPod sync functionality provided by
iTunes.
"""

from .exceptions import BadDestinationError, InvalidConfigError
from .core import Hibiki
from .config import HibikiConfig
from .itunes import iTunesLibrary, iTunesPlaylist, iTunesTrack
