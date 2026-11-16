#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('feature', Path(__file__).resolve().parents[1]/'team-feature.py')
feature = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feature)


class FeatureChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_workspace_outputs_and_no_overwrite(self):
        folder = feature.workspace('latihan-01', self.root/'work')
        self.assertIn('latihan-01', (folder/'README.md').read_text())
        self.assertIn('int main', (folder/'main.c').read_text())
        (folder/'keep.txt').write_text('tetap')
        with self.assertRaises(FileExistsError): feature.workspace('latihan-01', self.root/'work')
        self.assertEqual((folder/'keep.txt').read_text(), 'tetap')

    def test_rejects_invalid_names(self):
        for name in ('../folder', 'A', '', 'nama ruang', 'x;touch sentinel'):
            with self.assertRaises(ValueError): feature.workspace(name, self.root/'work')
        self.assertFalse((self.root/'work').exists())

    def test_library_and_missing_folder(self):
        (self.root/'materi.txt').write_text('contoh')
        (self.root/'link').symlink_to(self.root/'materi.txt')
        self.assertEqual(feature.library(self.root), ['materi.txt'])
        with self.assertRaises(ValueError): feature.library(self.root/'missing')


if __name__ == '__main__':
    unittest.main()
