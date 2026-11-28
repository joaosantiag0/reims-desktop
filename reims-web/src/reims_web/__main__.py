#!/usr/bin/env python3
"""python -m reims_web -> reims-web CLI."""
from __future__ import annotations

import sys

from reims_web.server import main

if __name__ == "__main__":
    sys.exit(main())
