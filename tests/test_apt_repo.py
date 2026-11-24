from __future__ import annotations

import gzip
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.generate_apt_repo import extract_control_info, generate_apt_repo


class TestAptRepoGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.dist_dir = cls.repo_root / "dist"

    def test_generate_apt_repo(self):
        deb_files = list(self.dist_dir.glob("*.deb"))
        self.assertGreater(len(deb_files), 0, "No .deb packages found in dist/")

        # Test control extraction on first deb
        fields, size, sha256, md5 = extract_control_info(deb_files[0])
        self.assertIn("Package", fields)
        self.assertIn("Version", fields)
        self.assertGreater(size, 0)
        self.assertEqual(len(sha256), 64)
        self.assertEqual(len(md5), 32)

        # Test full repository generation
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "repo"
            generate_apt_repo(self.dist_dir, out_dir, suite="noble", component="main")

            # Check index.html
            index_file = out_dir / "index.html"
            self.assertTrue(index_file.exists())
            self.assertIn("Reims Desktop", index_file.read_text(encoding="utf-8"))

            # Check pool
            pool_dir = out_dir / "pool" / "main"
            self.assertTrue(pool_dir.exists())
            self.assertEqual(len(list(pool_dir.glob("*.deb"))), len(deb_files))

            # Check dists
            dists_dir = out_dir / "dists" / "noble"
            self.assertTrue((dists_dir / "Release").exists())
            release_text = (dists_dir / "Release").read_text(encoding="utf-8")
            self.assertIn("Codename: noble", release_text)
            self.assertIn("SHA256:", release_text)

            # Check Packages and Packages.gz
            for arch in ["binary-amd64", "binary-all"]:
                arch_dir = dists_dir / "main" / arch
                pkg_file = arch_dir / "Packages"
                pkg_gz = arch_dir / "Packages.gz"
                self.assertTrue(pkg_file.exists())
                self.assertTrue(pkg_gz.exists())

                pkg_content = pkg_file.read_text(encoding="utf-8")
                self.assertIn("Package:", pkg_content)
                self.assertIn("Filename: pool/main/", pkg_content)

                # Check gzip decompression
                with gzip.open(pkg_gz, "rt", encoding="utf-8") as gz:
                    decompressed = gz.read()
                    self.assertEqual(decompressed, pkg_content)


if __name__ == "__main__":
    unittest.main()
