#!/usr/bin/env python3
"""Local generator checks, not Linux VM or ISO acceptance tests."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

MODULE = Path(__file__).resolve().parents[1] / 'studio.py'
spec = importlib.util.spec_from_file_location('studio', MODULE)
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


class StudioChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'configs').mkdir()
        (self.root/'branding').mkdir()
        self.config = ('OS_NAME="Aksara OS"\nOS_ID="aksara-os"\nOS_VERSION="0.2.0"\n'
                       'BUILD_CHANNEL="development"\nBUILD_ID="aksara-os-0.2.0-dev1"\n')
        (self.root/'configs/project.env').write_text(self.config)
        self.style = dict(team='Aksara', mark='AX', audience='mahasiswa', mission='Belajar lokal',
                          background='#0E1830', foreground='#F3F6FC', accent='#78DCC7',
                          pattern='orbit', actions=['Materi', 'Latihan', 'Bantuan'])
        self.save_style()

    def save_style(self):
        (self.root/'branding/team-style.json').write_text(json.dumps(self.style))

    def test_consistent_assets_and_repeat(self):
        studio.build(self.root)
        out = self.root/'build/team-preview'
        before = {p.name:p.read_bytes() for p in out.iterdir()}
        studio.build(self.root)
        self.assertEqual(before, {p.name:p.read_bytes() for p in out.iterdir()})
        for filename in ['welcome.html', 'banner.txt', 'wallpaper.svg', 'trpl-custom-os-release']:
            self.assertIn('Aksara OS', (out/filename).read_text())
        ElementTree.parse(out/'wallpaper.svg')
        ElementTree.parse(out/'logo.svg')
        self.assertIn('OS_NAME=Aksara OS\n', (out/'trpl-custom-os-release').read_text())

    def test_patterns_and_text_escaping(self):
        self.style['mission'] = '<script>alert(1)</script> & belajar'
        for pattern in ['orbit', 'grid', 'ribbon']:
            self.style['pattern'] = pattern
            self.save_style()
            studio.build(self.root)
            out = self.root/'build/team-preview'
            self.assertNotIn('<script>', (out/'welcome.html').read_text())
            ElementTree.parse(out/'wallpaper.svg')

    def test_accepts_full_starter_config(self):
        # Regresi 3 Nov 2026: project.env lengkap dari starter (regex hostname berakhiran $) harus diterima.
        full = self.config + ('EXPECTED_HOSTNAME_PATTERN="^aksara-os-[a-z0-9-]+$"\n'
                              'EXPECTED_USER="student"\nSECURITY_PATHS="/etc/aksara-os /var/lib/aksara-os"\n')
        (self.root/'configs/project.env').write_text(full)
        studio.build(self.root)
        self.assertTrue((self.root/'build/team-preview/welcome.html').exists())

    def test_rejects_shell_duplicate_and_missing(self):
        for text in [self.config+'OS_ID="lain"\n', self.config.replace('Aksara OS', '$(touch sentinel)'),
                     self.config.replace('Aksara OS', 'Aksara`id`'), self.config.replace('Aksara OS', 'Aksara; rm'),
                     self.config.replace('OS_NAME="Aksara OS"\n','')]:
            (self.root/'configs/project.env').write_text(text)
            with self.assertRaises(ValueError): studio.build(self.root)
        self.assertFalse((self.root/'sentinel').exists())

    def test_rejects_invalid_style(self):
        for key, val in [('background', 'red'), ('pattern', 'unknown'), ('mark', '<ax>'),
                         ('foreground', '#0E1830'), ('actions', ['one'])]:
            changed = dict(self.style)
            changed[key] = val
            (self.root/'branding/team-style.json').write_text(json.dumps(changed))
            with self.assertRaises(ValueError): studio.build(self.root)

    def test_rejects_output_symlink(self):
        (self.root/'build').mkdir()
        (self.root/'build/team-preview').symlink_to(self.root/'branding')
        with self.assertRaises(ValueError): studio.build(self.root)


if __name__ == '__main__':
    unittest.main()
