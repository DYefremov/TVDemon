import os
import datetime
import distutils.util

EXE_NAME = 'tvdemon.py'
DIR_PATH = os.getcwd()
COMPILING_PLATFORM = distutils.util.get_platform()
PATH_EXE = [os.path.join(DIR_PATH, EXE_NAME)]
STRIP = True
BUILD_DATE = datetime.datetime.now().strftime("%y%m%d")

block_cipher = None

excludes = []

ui_files = [('usr/share/tvdemon', 'share/tvdemon'),
           ('usr/share/icons/hicolor/scalable/apps/tvdemon.svg',
            'share/icons/hicolor/scalable/apps')]

a = Analysis([EXE_NAME],
             pathex=PATH_EXE,
             binaries=None,
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
                "gstreamer": {
                    "exclude_plugins": ["opencv"],
                   },
                },
             },
             excludes=excludes,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure,
          a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='TVDemon',
          debug=False,
          strip=STRIP,
          upx=False,
          console=False)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=STRIP,
               upx=False,
               name='TVDemon')

app = BUNDLE(coll,
             name='TVDemon.app',
             icon='tvdemon.icns',
             bundle_identifier=None,
             info_plist={
                 'NSPrincipalClass': 'NSApplication',
                 'CFBundleName': 'TVDemon',
                 'CFBundleDisplayName': 'TVDemon',
                 'CFBundleGetInfoString': "IPTV Player",
                 'LSApplicationCategoryType': 'public.app-category.video',
                 'LSMinimumSystemVersion': '14.3.1',
                 'CFBundleShortVersionString': f"2.0.0.{BUILD_DATE} Alpha",
                 'NSHumanReadableCopyright': u"Copyright © 2024, Dmitriy Yefremov",
                 'NSRequiresAquaSystemAppearance': 'False',
                 'NSHighResolutionCapable': 'True'
             })
