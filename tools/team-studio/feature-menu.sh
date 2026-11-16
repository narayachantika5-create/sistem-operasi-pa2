#!/usr/bin/env bash
# Antarmuka latihan. Ubah label dan pilih mode yang relevan untuk produk tim.
set -u
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
printf '\nFitur lokal tim\n1. Periksa prasyarat\n2. Buat workspace\n3. Baca koleksi materi\n'
read -r -p 'Pilihan: ' choice || exit 2
status=0
case "$choice" in
  1) python3 "${script_dir}/team-feature.py" readiness || status=$? ;;
  2)
    read -r -p 'Nama workspace: ' name || exit 2
    python3 "${script_dir}/team-feature.py" workspace "$name" || status=$?
    ;;
  3)
    read -r -p 'Path folder materi: ' folder || exit 2
    python3 "${script_dir}/team-feature.py" library "$folder" || status=$?
    ;;
  *) printf 'Pilihan tidak valid.\n' >&2; status=2 ;;
esac
printf '\nExit status fitur: %s\n' "$status"
read -r -p 'Tekan Enter untuk menutup. ' finish || true
exit "$status"
