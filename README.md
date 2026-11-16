# Kit kustomisasi tim

Kit ini merupakan tambahan untuk starter resmi kelas. Gunakan repository kelompok yang sudah digunakan pada PA0. Tidak perlu memulai repository baru. `configs/project.env` tetap satu-satunya sumber nama, ID, versi, channel, dan build produk. Style tim berada pada JSON agar tidak menjadi kode shell.

Salin folder `tools/team-studio` ke `tools/team-studio` pada starter. Salin `branding/team-style.json.example` ke `branding/team-style.json`, lalu sesuaikan identitas tim. Jangan menimpa `configs/project.env` yang sudah diisi. Jika belum ada, buat dari contoh starter dan isi identitas resmi kelompok.

```bash
# Dari root repository kelompok, setelah folder kit disalin.
python3 tools/team-studio/studio.py check --root .
python3 tools/team-studio/studio.py build --root .
# Ubuntu desktop VM; pada macOS buka HTML/SVG melalui Finder.
xdg-open build/team-preview/welcome.html
```

Generator hanya menulis berkas di `build/team-preview`. Generator tidak memasang paket atau mengubah `/etc`, boot, desktop, maupun service. Hasilnya adalah wallpaper SVG 1920 × 1080, logo SVG, halaman sambutan dan panduan HTML luring, banner teks, identitas tambahan OS, launcher desktop, serta checksum. Label menu pada HTML membuka bagian panduan, bukan menjalankan aplikasi Linux. Launcher untuk sistem baru bekerja setelah HTML dan logo dipasang di jalur final. Isi panduan masih TODO dan wajib ditulis kelompok.

## Yang dimodifikasi mahasiswa

1. Isi `team`, `mark`, `audience`, dan `mission` dengan keputusan kelompok.
2. Ubah palet dan satu dari pola `orbit`, `grid`, `ribbon`.
3. Susun tiga label tindakan sesuai alur pengguna. Jangan menyalin skenario contoh tanpa penyesuaian.
4. Baca fungsi `wallpaper`, `logo`, dan `welcome`. Modifikasi minimal dua unsur struktur, misalnya bentuk logo dan susunan halaman. Tulis diff serta alasan.
5. Lengkapi isi panduan dalam fungsi `welcome` bagian `guide=True`.
6. Pada PA2, terapkan hasil pada XFCE dan integrasikan satu fitur produk yang benar-benar bekerja.

Program C PA0 tetap digunakan untuk mempelajari hubungan source, konfigurasi, ASCII dan SVG. Kit ini memperluas aset untuk produk akhir. Jika memakai generator Python sebagai jalur produksi, catat keputusan itu pada arsitektur; jangan menilai tampilan dari dua generator yang berbeda sebagai satu hasil yang sama.

Folder `examples` menyediakan empat preset style untuk membandingkan arah visual. Baca atau salin salah satu sebagai titik awal setelah menyimpan style tim. Ubah pengguna, tujuan, label tindakan, logo, dan layout sesuai keputusan tim. Memilih preset tidak mengganti OS_NAME atau OS_ID; identitas produk tetap diedit pada configs/project.env. Setiap preset hanya contoh, bukan hasil akhir kelompok.

## Pembagian pengujian

`tests/test-studio.py` memeriksa parser, penolakan input tidak valid, escaping teks, konsistensi keluaran dan pengulangan generator. Pengujian ini dapat dilakukan pada macOS/Linux tanpa root. Pengujian XFCE, LightDM, Plymouth, systemd, UFW, Cubic dan ISO tetap dilakukan pada VM Ubuntu kelas. Lihat modul PA1 sampai PA4 untuk penerapannya.

```bash
python3 tools/team-studio/tests/test-studio.py
python3 tools/team-studio/tests/test-feature.py
python3 tools/team-studio/tests/test-recipe.py
```

## Resep lengkap dan profil desktop

Salin juga `branding/desktop-profile.json.example` ke branding pada repository, lalu buat file aktif `branding/desktop-profile.json`. Ikuti kontrak jalur pada Praktik terpandu PA1 T03, termasuk MONITOR_COMMAND, CUSTOM_FEATURE_COMMAND, logo, dan SECURITY_PATHS.

Setelah studio build dan ekspor PNG melalui Inkscape:

```bash
python3 tools/team-studio/recipe.py prepare --root .
python3 tools/team-studio/recipe.py plan --root .
python3 tools/team-studio/recipe.py apply --root . --dry-run
```

prepare menyusun `build/team-overlay` dan `build/team-overlay-manifest.json`. Target mencakup dua panel XFCE, theme/font/icon/terminal, pusat kendali Zenity, program fitur, service monitoring least privilege, autostart sesi pengguna, logo/wallpaper, LightDM, serta source tema Plymouth. File `SOURCE-INPUTS.json` dan checksum manifest membantu menolak bahan yang tertinggal dari konfigurasi/source aktif.

Terapkan hanya pada target yang sesuai langkah modul:

```bash
# VM Ubuntu yang mempunyai snapshot nyata dan source telah ditinjau.
sudo python3 tools/team-studio/recipe.py apply --root . \
  --mode vm --confirm-snapshot pa2-sebelum-apply
# Pada Terminal Cubic yang terdeteksi sebagai chroot.
python3 tools/team-studio/recipe.py apply --root . --mode image
```

Apply menyalin file yang tercantum dalam manifest. Operasi ini tidak memasang paket, menjalankan firewall, memulai service, menghapus GNOME, atau membangun initramfs. Langkah operasi tersebut dijelaskan terpisah di PA2 dan PA4 agar konteks runtime dan filesystem image tidak tercampur. Backup file berada di /var/backups/OS_ID/timestamp; snapshot tetap diperlukan untuk pemulihan sistem.

Default skel baru diterima akun yang dibuat setelah pemasangan. Script sesi mengatur wallpaper pada properti monitor yang ditemukan dan menggunakan marker versi agar tidak selalu menimpa pilihan pengguna. `team-center.py`, `team-session.py`, serta `team-health.sh` pada templates disertakan sebagai source pembelajaran. Baca dan modifikasi sebelum menerapkan.

Hasil tes recipe pada direktori sementara bukan bukti panel, greeter, splash, service, atau ISO telah bekerja. Bukti runtime diambil pada VM Ubuntu target.

## Starter fitur yang dapat dimodifikasi

`tools/team-studio/team-feature.py` menyediakan tiga percobaan lokal. Pilih satu sebagai dasar fitur produk, lalu sesuaikan source dan pengujiannya. Wrapper `feature-menu.sh` disiapkan untuk mencoba input pengguna melalui terminal. Kelompok menyesuaikan menu sehingga sesuai fitur utama yang dipilih.

```bash
python3 tools/team-studio/team-feature.py readiness
python3 tools/team-studio/team-feature.py workspace latihan-01
python3 tools/team-studio/team-feature.py library docs
bash tools/team-studio/feature-menu.sh
```

`workspace` membuat README serta source C sederhana di `~/Workspaces/latihan-01` dan menolak nama tidak valid/folder yang sudah ada. `library` hanya membaca berkas pada direktori yang dipilih. `readiness` memeriksa program Python dan compiler di PATH. Ubah template C, instruksi README, atau prasyarat sesuai produk. Kompilasi source contoh di VM dengan `cc -Wall -Wextra -std=c11 main.c -o latihan`, lalu jalankan `./latihan`. Jika `cc` tidak tersedia, gunakan `build-essential` sesuai panduan kelas. Contoh ini membantu memahami cara mencoba kode; produk tetap perlu alur dan modifikasi kelompok.

Gunakan aset buatan tim atau aset berlisensi yang sesuai. Kit adalah scaffold pembelajaran; hasil contoh belum merupakan produk akhir siap dikumpulkan.
