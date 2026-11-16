#!/usr/bin/env python3
"""Set wallpaper once in the user's graphical session, never as root."""
import json
import os
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
INFO = json.loads((HERE/'ui.json').read_text())
if os.geteuid() == 0:
    raise SystemExit('Jalankan dalam sesi XFCE pengguna biasa')
state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))/INFO['id']
marker = state/('profile-'+INFO['profile_revision'])
if not marker.exists():
    props = []
    for attempt in range(20):
        result = subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-l'],
                                capture_output=True, text=True)
        props = [p for p in result.stdout.splitlines() if p.endswith('/last-image')]
        if props:
            break
        time.sleep(.5)
    if not props:
        raise SystemExit('Belum menemukan properti wallpaper. Periksa sesi/monitor lalu coba ulang.')
    for prop in props:
        subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-p', prop,
                        '-s', INFO['wallpaper']], check=True)
    state.mkdir(parents=True, exist_ok=True)
    marker.write_text('Default wallpaper diterapkan pada sesi pengguna\n')
welcome_marker = state/('welcome-'+INFO['build'])
if INFO['first_login_welcome'] and not welcome_marker.exists():
    result = subprocess.run(['xdg-open', INFO['welcome']])
    if result.returncode == 0:
        state.mkdir(parents=True, exist_ok=True)
        welcome_marker.write_text('Halaman sambutan diminta melalui xdg-open\n')
