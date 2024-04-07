#!/usr/bin/env python3
import sys

if __name__ == "__main__":
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        import os
        import ssl
        from multiprocessing import freeze_support
        from usr.lib.tvdemon.app.main import run_app

        os.environ["PYTHONUTF8"] = "1"
        ssl._create_default_https_context = ssl._create_unverified_context

        freeze_support()
        run_app()
