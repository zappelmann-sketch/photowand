"""Einstiegspunkt der Photowand-Anwendung."""

import sys
import os

# Sicherstellen, dass das Paket im Pfad ist
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from photowand.app import PhotowandApp


def main():
    app = PhotowandApp()
    app.mainloop()


if __name__ == "__main__":
    main()
