#!/usr/bin/env python3
"""
Unit tests for logo processing and background extraction in Reims Desktop.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from PIL import Image

from scripts.process_logos import remove_white_background


class TestLogoProcessing(unittest.TestCase):
    def setUp(self) -> None:
        # Create a synthetic 100x100 test image with white background and a centered dark square
        self.img = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
        for y in range(25, 75):
            for x in range(25, 75):
                self.img.putpixel((x, y), (30, 30, 40, 255))

    def test_remove_white_background_transparent(self) -> None:
        result = remove_white_background(self.img, bg_color=None)
        self.assertEqual(result.size, (100, 100))
        self.assertEqual(result.mode, "RGBA")

        # Corner should be fully transparent (alpha = 0)
        corner_pixel = result.getpixel((0, 0))
        self.assertEqual(corner_pixel[3], 0)

        # Center should remain intact with full opacity
        center_pixel = result.getpixel((50, 50))
        self.assertEqual(center_pixel, (30, 30, 40, 255))

    def test_remove_white_background_black(self) -> None:
        result = remove_white_background(self.img, bg_color=(0, 0, 0, 255))
        self.assertEqual(result.size, (100, 100))

        # Corner should now be black (0, 0, 0, 255)
        corner_pixel = result.getpixel((0, 0))
        self.assertEqual(corner_pixel, (0, 0, 0, 255))

        # Center should remain intact
        center_pixel = result.getpixel((50, 50))
        self.assertEqual(center_pixel, (30, 30, 40, 255))

    def test_remove_white_background_plymouth(self) -> None:
        plymouth_color = (18, 20, 24, 255)
        result = remove_white_background(self.img, bg_color=plymouth_color)

        corner_pixel = result.getpixel((0, 0))
        self.assertEqual(corner_pixel, plymouth_color)

        center_pixel = result.getpixel((50, 50))
        self.assertEqual(center_pixel, (30, 30, 40, 255))


if __name__ == "__main__":
    unittest.main()
