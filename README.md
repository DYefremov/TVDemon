# TVDemon

### TVDemon based on [Hypnotix](https://github.com/linuxmint/hypnotix).  
This is an IPTV streaming application with support for live TV, movies and series.

![shadow](https://user-images.githubusercontent.com/7511379/208684877-6d901320-9859-4381-8220-f9209f40e51b.png)

It can support multiple IPTV providers of the following types:

- M3U URL
- Xtream API
- Local M3U playlist

## Differences from [Hypnotix](https://github.com/linuxmint/hypnotix)
 * Some GUI changes.
 * Functionality improvement.
 * Removed use of [xapp](https://github.com/linuxmint/xapp) and **GSettings**.
 * Can be run without installation.
 * Ability to run in MS Windows (via [MSYS2](https://www.msys2.org/) platform).

## Requirements
- libmpv >= 0.34.1
- [IMDbPy](https://pypi.org/project/IMDbPY/) (python3-imdbpy)

## Installation and Launch
* ### Linux
  To start the program, in most cases it is enough to download the [archive](https://github.com/DYefremov/TVDemon/archive/refs/heads/main.zip),   
  unpack and run it by double-clicking on the *.desktop file in the root directory,  
  or launch from the console with the command:```./tvdemon```   
  Depending on your distro, you may need to install additional packages and libraries.

To create a Debian package, you can use the *build-deb.sh* file from the *build* directory.

* ### MS Windows (experimental) 
  Windows users can also run (build) this program.  
One way is the [MSYS2](https://www.msys2.org/) platform. You can use [this](https://github.com/DYefremov/TVDemon/blob/main/build/win/BUILD.md) quick guide.  

## TV Channels and media content

TVDemon does not provide content or TV channels, it is a player application which streams from IPTV providers.

By default, TVDemon is configured with one IPTV provider called Free-TV: https://github.com/Free-TV/IPTV.

### Issues relating to TV channels and media content should be addressed directly to the relevant provider.

Note: Feel free to remove Free-TV from TVDemon if you don't use it, or add any other provider you may have access to or local M3U playlists.

## Wayland compatibility

If you're using Wayland go the TVDemon preferences and add the following to the list of MPV options:

`vo=x11`

Run TVDemon with:

`GDK_BACKEND=x11 tvdemon`

## License

- Code: GPLv3
- Flags: https://github.com/linuxmint/flags
- Icons on the landing page: CC BY-ND 2.0
