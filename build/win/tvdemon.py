#!/usr/bin/env python3
import os
import sys

if __name__ == "__main__":
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        import pyi_splash
        from multiprocessing import freeze_support

        os.environ["GIO_EXTRA_MODULES"] = os.path.join(sys._MEIPASS, "lib", "gio", "modules")
        freeze_support()

        from usr.lib.tvdemon.app.main import run_app

        pyi_splash.close()
        run_app()
