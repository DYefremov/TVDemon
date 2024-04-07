## Project switched to **Gtk4** and [Libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/index.html).  
### *Under development...*

# TVDemon
### TVDemon based on [Hypnotix](https://github.com/linuxmint/hypnotix).  
This is an IPTV streaming application with support for live TV, movies and series.
![shadow](https://private-user-images.githubusercontent.com/7511379/320309005-5b83286b-3f08-4a63-bb1e-a0bbec64c8fe.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MTI1MTg5MjQsIm5iZiI6MTcxMjUxODYyNCwicGF0aCI6Ii83NTExMzc5LzMyMDMwOTAwNS01YjgzMjg2Yi0zZjA4LTRhNjMtYmIxZS1hMGJiZWM2NGM4ZmUucG5nP1gtQW16LUFsZ29yaXRobT1BV1M0LUhNQUMtU0hBMjU2JlgtQW16LUNyZWRlbnRpYWw9QUtJQVZDT0RZTFNBNTNQUUs0WkElMkYyMDI0MDQwNyUyRnVzLWVhc3QtMSUyRnMzJTJGYXdzNF9yZXF1ZXN0JlgtQW16LURhdGU9MjAyNDA0MDdUMTkzNzA0WiZYLUFtei1FeHBpcmVzPTMwMCZYLUFtei1TaWduYXR1cmU9MTI1NmE1NWUzMzVlNGFlZmY1ZDEyYTY1NDI2OGVkMmFiZGUwZDA2MmQ0NDQzZTJjNmJkNjM4MTdjZmFjYmVkMCZYLUFtei1TaWduZWRIZWFkZXJzPWhvc3QmYWN0b3JfaWQ9MCZrZXlfaWQ9MCZyZXBvX2lkPTAifQ.L8aQJrXXwwqDdIwsSn-IF0tuxSh_Bx_h3-5ngsM2gKw)
It can support multiple IPTV providers of the following types:

- M3U URL
- Xtream API
- Local M3U playlist

## Differences from [Hypnotix](https://github.com/linuxmint/hypnotix)
 * GUI redesign. Developed using Gtk4 and [Libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/).
 * [GStreamer](https://gstreamer.freedesktop.org/) as default media library.
 * Can be run without installation. 
 * Ability to run on *macOS* and *MS Windows* (via [MSYS2](https://www.msys2.org/) platform).

## Requirements
- Gtk4 >= 4.12
- [Libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) >= 1.4
- Python >= 3.11
- PyGObject (pygobject3)
- Requests (python3-request)
- [GStreamer](https://gstreamer.freedesktop.org/) with Gtk4 plugin (gst-plugin-gtk4).

## Installation and Launch
* ### Linux
  To start the program, in most cases it is enough to download the [archive](https://github.com/DYefremov/TVDemon/archive/refs/heads/main.zip),   
  unpack and run it by double-clicking on the *.desktop file in the root directory,  
  or launch from the console with the command:```./tvdemon.py```   
  Depending on your distro, you may need to install additional packages and libraries.

To create a Debian package, you can use the *build-deb.sh* file from the *build* directory.  

* ### macOS (experimental)  
To run the program on macOS, you need to install [Homebrew](https://brew.sh/).  
Then install the required components via terminal:  
`brew install python3 gtk+4 libadwaita pygobject3 adwaita-icon-theme python-requests gstreamer`

Launch is similar to Linux.


* ### MS Windows (experimental) 
  Windows users can also run (build) this program.  
One way is the [MSYS2](https://www.msys2.org/) platform. You can use [this](https://github.com/DYefremov/TVDemon/blob/main/build/win/BUILD.md) quick guide.  

## TV Channels and media content

TVDemon does not provide content or TV channels, it is a player application which streams from IPTV providers.

By default, TVDemon is configured with one IPTV provider called Free-TV: https://github.com/Free-TV/IPTV.

### Issues relating to TV channels and media content should be addressed directly to the relevant provider.

Note: Feel free to remove Free-TV from TVDemon if you don't use it, or add any other provider you may have access to or local M3U playlists.  

## License

- Code: GPLv3
- Flags: https://github.com/linuxmint/flags
- Icons on the landing page: CC BY-ND 2.0