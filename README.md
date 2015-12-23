hibiki
======

Believe in Justice and Hold a Determination to Sync.

## Description

Hibiki is a Python module and command-line application designed to replicate the iPod syncing features found in iTunes except for external storage drives. It can for example be used to copy tracks by certain artists onto a USB flash drive for playback in the car. You can either use the included command-line application or write a Python script with the module.

You can select artists, albums, genres and playlists to be included or excluded in the sync. You can also set hibiki to fill the remaining space with random tracks.

## Dependencies

The Hibiki module only uses includes from the standard library. The command-line interface requires [**urwid**](http://urwid.org) to run.

## Support

**Only Python 3 is supported.** Any attempt to run it with Python 2 will most likely fail.

The application has mostly been developed to be ran on OS X, as it uses iTunes which is only supported on OS X and Windows and the software hasn't been designed with non-POSIX systems in mind. That is not to say it will definitely not work, but it might not work. The software has not been tested with iTunes versions newer than 11. However, they should work as long as the `iTunes Library.xml` format stays relatively the same.

Note: if you are on version 12.2 or greater, iTunes will no longer automatically generate the required `iTunes Library.xml` for you. See this [Apple help topic](https://support.apple.com/en-us/HT201610) for more details.

## Command-line application

### Usage

The command-line application can be ran simply with `python CLI.py`. It will ask the user to input the target directory and attempts to load the config from there if saved. Then it will ask for the sync rules via a checkbox interface. After that, the copying operation starts.

The current operation can be read in the header bar. Status and hotkeys can be found on the footer bar.

### Settings

| Setting name                 | Description                                                       |
| ---------------------------- | ----------------------------------------------------------------- |
| DESTINATION PATH             | Path to the destination directory.                                |
| iTunes Library.xml PATH      | Path to the iTunes Library.xml file.                              |
| USE RANDOM FILL              | Check if the remaining space should be filled with random files.  |
| USE SUBFOLDERS               | Check if the files should be sorted into numbered subdirectories. |
| MAX FILE COUNT PER SUBFOLDER | Maximum number of files in a subdirectory.                        |

Settings are saved in `.hibiki/config` in the destination as JSON data.

### Tips

It may be useful to create a `.metadata_never_index` file in the root directory of your external storage device to prevent OS X from creating Spotlight index files onto it.

## License

See [LICENSE](LICENSE).
