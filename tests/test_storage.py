import tempfile
import unittest
from pathlib import Path

import pandas as pd

from utils.storage import write as storage_write, read as storage_read, glob_latest


class TestStorage(unittest.TestCase):
    def test_write_creates_parent_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_dir = Path(tmp) / "subdir" / "nested"
            target_file = target_dir / "testfile"
            df = pd.DataFrame({"x": [1, 2, 3]})

            output_path = storage_write(df, target_file)

            self.assertTrue(output_path.exists())
            self.assertIn(output_path.suffix, {".parquet", ".gz"})

    def test_read_roundtrip_parquet(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "roundtrip"
            df = pd.DataFrame({"x": [1, 2, 3]})
            output_path = storage_write(df, target)

            restored = storage_read(output_path)
            pd.testing.assert_frame_equal(df, restored.drop(columns=[], errors="ignore"))

    def test_glob_latest_prefers_newest(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "file1.parquet").write_text("dummy")
            (base / "file2.parquet").write_text("dummy")

            latest = glob_latest(base, "file")
            self.assertTrue(str(latest).endswith("file2.parquet"))

    def test_read_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            text_path = Path(tmp) / "bad.ext"
            text_path.write_text("bad")
            with self.assertRaises(ValueError):
                storage_read(text_path)


if __name__ == "__main__":
    unittest.main()
