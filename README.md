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
 * Some code changes and improvements.

## Requirements

- libmpv >= 0.34.1
- python3-imdbpy (for Older Mint and Debian releases get it from https://packages.ubuntu.com/focal/all/python3-imdbpy/download)

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
