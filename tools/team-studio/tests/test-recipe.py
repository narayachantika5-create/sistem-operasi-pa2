#!/usr/bin/env python3
"""Assembly/installation logic tests in temporary fixtures; not a VM acceptance."""
import base64
import importlib.util
import json
import tempfile
import unittest
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recipe',HERE/'recipe.py')
recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)


class RecipeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name)/'project';self.target=Path(self.temp.name)/'target'
  (self.root/'configs').mkdir(parents=True);(self.root/'branding').mkdir();self.target.mkdir()
  shutil.copytree(HERE,self.root/'tools/team-studio',ignore=shutil.ignore_patterns('__pycache__'))
  recipe.HERE=self.root/'tools/team-studio'
  cfg='OS_NAME="Aksara OS"\nOS_ID="aksara-os"\nOS_VERSION="0.2.0"\nBUILD_CHANNEL="development"\nBUILD_ID="aksara-dev1"\nCUSTOM_SERVICE="aksara-health.service"\nCUSTOM_SERVICE_HEALTH_PATTERN="AKSARA_READY"\nMONITOR_COMMAND="/usr/local/lib/aksara-os/team-health"\nBRANDING_WALLPAPER_PATH="/usr/share/backgrounds/aksara-os-wallpaper.png"\nBRANDING_LOGO_PATH="/usr/share/pixmaps/aksara-os.svg"\n'
  (self.root/'configs/project.env').write_text(cfg)
  with (self.root/'configs/project.env').open('a') as f:
   f.write('CUSTOM_FEATURE_COMMAND="/usr/local/lib/aksara-os/feature-self-test"\nSECURITY_PATHS="/etc/aksara-os /var/lib/aksara-os"\n')
  kit=HERE.parents[1]
  (self.root/'branding/team-style.json').write_text((kit/'branding/team-style.json.example').read_text())
  (self.root/'branding/desktop-profile.json').write_text((kit/'branding/desktop-profile.json.example').read_text())
  recipe.studio.build(self.root)
  # Valid tiny PNG for assembly fixtures, not a claimed wallpaper screenshot.
  png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aOXcAAAAASUVORK5CYII=')
  for n in ['logo.png','wallpaper.png']:(self.root/'build/team-preview'/n).write_bytes(png)

 def test_prepare_paths_and_profile(self):
  recipe.prepare(self.root);manifest,overlay=recipe.load_manifest(self.root)
  self.assertGreater(len(manifest['files']),25)
  for p in overlay.rglob('*.xml'):ET.parse(p)
  xml=ET.parse(overlay/'etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml')
  self.assertEqual(len(xml.findall("./property[@name='panels']/value")),2)
  unit=(overlay/'etc/systemd/system/aksara-health.service').read_text()
  self.assertIn('DynamicUser=yes',unit);self.assertIn('RemainAfterExit=yes',unit)

 def test_apply_fixture_repeat_and_backup(self):
  recipe.prepare(self.root)
  old=self.target/'etc/trpl-custom-os-release';old.parent.mkdir();old.write_text('OLD\n')
  backup=Path(self.temp.name)/'backup'
  self.assertGreater(recipe.install_manifest(self.root,self.target,backup),25)
  self.assertEqual((backup/'etc/trpl-custom-os-release').read_text(),'OLD\n')
  self.assertEqual(recipe.install_manifest(self.root,self.target,backup),0)

 def test_missing_export_fails_before_overlay(self):
  (self.root/'build/team-preview/logo.png').unlink()
  with self.assertRaises(ValueError):recipe.prepare(self.root)
  self.assertFalse((self.root/'build/team-overlay').exists())

 def test_manifest_source_change_and_private_target_rejected(self):
  recipe.prepare(self.root)
  overlay=self.root/'build/team-overlay';path=self.root/'build/team-overlay-manifest.json'
  m=json.loads(path.read_text());m['files'][0]['path']='etc/shadow';path.write_text(json.dumps(m))
  with self.assertRaises(ValueError):recipe.load_manifest(self.root)
  recipe.prepare(self.root)
  (overlay/'etc/trpl-custom-os-release').write_text('changed')
  with self.assertRaises(ValueError):recipe.load_manifest(self.root)

 def test_symlink_target_and_traversal_rejected(self):
  recipe.prepare(self.root)
  (self.target/'etc').symlink_to(self.root/'branding')
  with self.assertRaises(ValueError):recipe.install_manifest(self.root,self.target)
  with self.assertRaises(ValueError):recipe.safe_child(self.target,'../outside')

 def test_bad_profile_rejected(self):
  p=self.root/'branding/desktop-profile.json';data=json.loads(p.read_text())
  data['top_panel_size']=200;p.write_text(json.dumps(data))
  with self.assertRaises(ValueError):recipe.prepare(self.root)

 def test_stale_style_is_rejected(self):
  style=self.root/'branding/team-style.json';data=json.loads(style.read_text())
  data['mission']='Misi baru';style.write_text(json.dumps(data))
  with self.assertRaises(ValueError):recipe.prepare(self.root)


if __name__=='__main__':unittest.main()
