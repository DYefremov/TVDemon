## Launch
1. Download and install the [MSYS2](https://www.msys2.org/) platform as described [here](https://www.msys2.org/) up to point 4. 
2. Start **mingw64** shell.  
![mingw64](https://user-images.githubusercontent.com/7511379/161400639-898ceb10-7de8-4557-bde1-25fe32bdfb03.png)
3. Run command `pacman -Suy` After that, you may need to restart the terminal and re-run the update command. 
4. Install minimal required packages:  
   `pacman -S mingw-w64-x86_64-gtk4 mingw-w64-x86_64-libadwaita mingw-w64-x86_64-python3 mingw-w64-x86_64-python3-gobject mingw-w64-x86_64-python3-pip mingw-w64-x86_64-python3-requests`
5. Install GStreamer and plugins:
`pacman -S mingw-w64-x86_64-gstreamer mingw-w64-x86_64-gst-plugins-base mingw-w64-x86_64-gst-plugins-good mingw-w64-x86_64-gst-plugins-bad mingw-w64-x86_64-gtk4-media-gstreamer mingw-w64-x86_64-gst-plugins-rs`   
6. Download and unzip the archive with sources from preferred branch (e.g. [main](https://github.com/DYefremov/TVDemon/archive/refs/heads/main.zip)) in to folder where MSYS2 is installed. E.g: `c:\msys64\home\username\`
7. Run mingw64 shell. Go to the folder where the program was unpacked. E.g: `cd TVDemon`
And run: `./tvdemon.py`

## Building a package
To build a standalone package, we can use [PyInstaller](https://pyinstaller.readthedocs.io/en/stable/). 
1. Launch *mingw64* shell.
2. Install [UPX](https://upx.github.io/) (**optional**) via command `pacman -S upx`.
3. Install *PyInstaller* via pip:  `pip3 install pyinstaller`
4. Go to the folder where the program was unpacked. E.g: `c:\msys64\home\username\TVDemon`
5. Сopy and replace the files from the */build/win/* folder to the root .
6. Go to the folder with the program in the running terminal:  `cd TVDemon`
7. Give the following command: `pyinstaller.exe TVDemon.spec`
8. Wait until the operation end. In the *dist* folder you will find a ready-made build.

### Appearance
To change the look we can use third party [Gtk4 themes and Icon sets](https://www.gnome-look.org).   
To set the default theme:
1. Сreate a folder "`\etc\gtk-4.0\`" in the root of the finished build folder.
2. Create a _settings.ini_ file in this folder with the following content: 
  ```
  [Settings]
  gtk-icon-theme-name = Adwaita
  gtk-theme-name = Windows-10
  ```
In this case, we are using the default icon theme "Adwaita" and the [third party theme](https://github.com/B00merang-Project/Windows-10) "Windows-10".
Themes and icon sets should be located in the `share\themes` and `share\icons` folders respectively.  
You can find more info about changing the appearance of Gtk applications on the Web yourself. 
