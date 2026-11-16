#!/usr/bin/env python3
"""Pusat kendali lokal contoh. Sesuaikan pilihan dan tujuan produk tim."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INFO = json.loads((HERE/'ui.json').read_text())


def dialog(*args):
    return subprocess.run(['zenity', *args], capture_output=True, text=True)


def show_result(result):
    text = result.stdout + result.stderr + f'\nExit status: {result.returncode}'
    subprocess.run(['zenity', '--text-info', '--title=Hasil fitur tim',
                    '--width=760', '--height=460'], input=text, text=True)


def main():
    choice = dialog('--list', '--title='+INFO['name'], '--text='+INFO['mission'],
                    '--width=680', '--height=380', '--column=Kode', '--column=Tindakan',
                    'workspace', 'Buat workspace latihan', 'library', 'Lihat materi lokal',
                    'health', 'Periksa kondisi sistem', 'guide', 'Buka panduan produk')
    if choice.returncode != 0:
        return 0
    action = choice.stdout.strip()
    if action == 'guide':
        return subprocess.run(['xdg-open', INFO['welcome']]).returncode
    if action == 'health':
        result = subprocess.run([str(HERE/'team-health')], capture_output=True, text=True)
    elif action == 'workspace':
        value = dialog('--entry', '--title=Workspace baru', '--text=Nama huruf kecil tanpa spasi')
        if value.returncode != 0:
            return 0
        result = subprocess.run([sys.executable, str(HERE/'team-feature.py'),
                                 'workspace', value.stdout.strip()], capture_output=True, text=True)
    elif action == 'library':
        value = dialog('--file-selection', '--directory', '--title=Pilih folder materi')
        if value.returncode != 0:
            return 0
        result = subprocess.run([sys.executable, str(HERE/'team-feature.py'),
                                 'library', value.stdout.strip()], capture_output=True, text=True)
    else:
        return 2
    show_result(result)
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
