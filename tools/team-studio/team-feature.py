#!/usr/bin/env python3
"""Starter fitur lokal. Ubah template, label dan aturan sesuai rancangan tim.

Tidak memerlukan root. Tidak menghapus atau menimpa direktori yang sudah ada.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

# TODO TIM: ganti isi template dan jelaskan dua perubahan pada laporan.
README_TEMPLATE = '# Latihan {name}\n\nTulis tujuan, langkah percobaan dan hasil pengamatan.\n'
C_TEMPLATE = '#include <stdio.h>\nint main(void) {{ puts("Latihan {name}"); return 0; }}\n'
REQUIRED_TOOLS = ('python3', 'cc')


def workspace(name, dest):
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,39}', name):
        raise ValueError('Nama: 2 sampai 40 karakter huruf kecil, angka, atau hubung')
    if dest.is_symlink():
        raise ValueError('Folder tujuan tidak boleh berupa symlink')
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    # exist_ok=False menolak folder lama; tidak ada penghapusan data.
    target.mkdir(exist_ok=False)
    (target/'README.md').write_text(README_TEMPLATE.format(name=name), encoding='utf-8')
    (target/'main.c').write_text(C_TEMPLATE.format(name=name), encoding='utf-8')
    print(f'WORKSPACE={target.resolve()}')
    return target


def library(folder):
    if not folder.is_dir():
        raise ValueError('Folder materi belum tersedia')
    # Hanya direktori langsung; tidak memindai seluruh filesystem.
    files = sorted(p.name for p in folder.iterdir() if p.is_file() and not p.is_symlink())
    print(json.dumps({'folder':str(folder.resolve()), 'count':len(files), 'files':files}, indent=2))
    return files


def readiness():
    result = {name:shutil.which(name) is not None for name in REQUIRED_TOOLS}
    print(json.dumps(result, indent=2))
    return all(result.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('workspace')
    create.add_argument('name')
    create.add_argument('--dest', type=Path, default=Path.home()/'Workspaces')
    materials = sub.add_parser('library')
    materials.add_argument('folder', type=Path)
    sub.add_parser('readiness')
    args = parser.parse_args()
    try:
        if args.command == 'workspace':
            workspace(args.name, args.dest)
        elif args.command == 'library':
            library(args.folder)
        elif not readiness():
            return 1
    except (OSError, ValueError) as error:
        print(f'GAGAL: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
