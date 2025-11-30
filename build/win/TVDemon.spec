# -*- mode: python ; coding: utf-8 -*-

EXE_NAME = 'tvdemon.py'
DIR_PATH = os.getcwd()
PATH_EXE = [os.path.join(DIR_PATH, EXE_NAME)]

block_cipher = None


excludes = ['youtube_dl',
            'tkinter']

ui_files = [('usr\\share\\tvdemon', 'share\\tvdemon'),
            ('usr\\share\\icons\\hicolor\\scalable\\apps\\tvdemon.svg',
            'share\\icons\\hicolor\\scalable\\apps'),
			('usr\\share\\locale', 'share\\locale')]


a = Analysis([EXE_NAME],
             pathex=PATH_EXE,
             binaries=[('C:\\msys64\\mingw64\\lib\\gio\\modules\\*', 'lib\\gio\\modules')],
             datas=ui_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             hooksconfig={
                "gi": {
                    "languages": ["en", "be", "de", "ru"],
                    "module-versions": {
                        "Gtk": "4.0"
                    },
                },

                "gstreamer": {
                    "exclude_plugins": ["videotestsrc",
                                        "videosignal",
                                        "spotify",
                                        "quinn",
                                        "monoscope",
                                        "goom2k1",
                                        "goom",
                                        "camerabin",
                                        "aws",
                                        "audiovisualizers",
                                        "audiotestsrc",
                                        "webrtc",
                                        "webrtcdsp",
                                        "webrtchttp",
                                        "rswebrtc",
                                        "webp",
                                        "rswebp",
                                        "rsvideofx"
                                        ],
                },
             },
             excludes=excludes,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='TVDemon',
          debug=False,
          bootloader_ignore_signals=False,
		  contents_directory='.',
          strip=False,
          upx=False,
          console=False,
          icon='tvdemon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='TVDemon')
