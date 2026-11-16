#!/usr/bin/env python3
"""Generate team-owned assets from the course starter config; never install them.

Only Python's standard library is required. Run from the starter repository:
python3 tools/team-studio/studio.py build --root .
Students edit branding/team-style.json and the functions below after reading them.
"""
import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path

REQUIRED = ('OS_NAME', 'OS_ID', 'OS_VERSION', 'BUILD_CHANNEL', 'BUILD_ID')
STYLE_KEYS = {'team', 'mark', 'audience', 'mission', 'background', 'foreground',
              'accent', 'pattern', 'actions'}


def read_config(path):
    values = {}
    for number, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Z][A-Z0-9_]*)="([^"\r\n]*)"', line)
        if not match:
            raise ValueError(f'{path.name}:{number}: gunakan KEY="VALUE"')
        key, value = match.groups()
        # Selaras dengan parser starter (scripts/lib/common.sh): tolak '$(', backtick, dan ';'.
        # '$' tunggal tetap diizinkan karena EXPECTED_HOSTNAME_PATTERN adalah regex berakhiran '$'.
        if key in values:
            raise ValueError(f'{path.name}:{number}: kunci ganda {key}')
        if any(c in value for c in ('$(', '`', ';', '\\')):
            raise ValueError(f'{path.name}:{number}: karakter shell tidak diizinkan pada {key}')
        if any(ord(c) < 32 for c in value):
            raise ValueError('Karakter kontrol tidak diizinkan')
        values[key] = value
    for key in REQUIRED:
        if not values.get(key) or len(values[key]) > 100:
            raise ValueError(f'Isi {key}, maksimal 100 karakter')
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,39}', values['OS_ID']):
        raise ValueError('OS_ID harus 2 sampai 40 karakter huruf kecil angka hubung')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', values['OS_VERSION']):
        raise ValueError('OS_VERSION harus menggunakan versi semantik')
    return values


def luminance(color):
    rgb = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    rgb = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    return sum(a*b for a, b in zip(rgb, (.2126, .7152, .0722)))


def read_style(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if set(value) != STYLE_KEYS:
        raise ValueError(f'Kunci style harus: {sorted(STYLE_KEYS)}')
    for key, limit in [('team', 45), ('mark', 4), ('audience', 90), ('mission', 120)]:
        if not isinstance(value[key], str) or not 1 <= len(value[key]) <= limit:
            raise ValueError(f'{key}: panjang harus 1 sampai {limit}')
        if any(ord(c) < 32 for c in value[key]):
            raise ValueError(f'{key}: karakter kontrol tidak diizinkan')
    if not re.fullmatch(r'[A-Z0-9]{1,4}', value['mark']):
        raise ValueError('mark: 1 sampai 4 huruf kapital atau angka')
    for key in ('background', 'foreground', 'accent'):
        if not isinstance(value[key], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value[key]):
            raise ValueError(f'{key} harus #RRGGBB')
    if value['pattern'] not in ('orbit', 'grid', 'ribbon'):
        raise ValueError('pattern harus orbit, grid, atau ribbon')
    if not isinstance(value['actions'], list) or len(value['actions']) != 3:
        raise ValueError('actions harus berisi tepat tiga label')
    if not all(isinstance(a, str) and 1 <= len(a) <= 40 and not any(ord(c) < 32 for c in a)
               for a in value['actions']):
        raise ValueError('Setiap action: teks maksimal 40 karakter tanpa kontrol')
    a, b = sorted((luminance(value['background']), luminance(value['foreground'])))
    if (b + .05) / (a + .05) < 4.5:
        raise ValueError('Kontras foreground dan background harus minimal 4.5 banding 1')
    return value


def pattern_svg(style):
    accent = style['accent']
    if style['pattern'] == 'grid':
        lines = [f'<path d="M{x} 0V1080"/>' for x in range(0, 1921, 120)]
        lines += [f'<path d="M0 {y}H1920"/>' for y in range(0, 1081, 120)]
        return f'<g stroke="{accent}" opacity=".11">' + ''.join(lines) + '</g>'
    if style['pattern'] == 'ribbon':
        return f'<g fill="none" stroke="{accent}" opacity=".26" stroke-width="70"><path d="M1050 -100L1800 1180"/><path d="M1300 -100L2050 1180"/></g>'
    return f'<g fill="none" stroke="{accent}" opacity=".3"><circle cx="1520" cy="410" r="240" stroke-width="2"/><circle cx="1520" cy="410" r="330" stroke-width="2"/><circle cx="1520" cy="410" r="420" stroke-width="1"/></g>'


def wallpaper(config, style):
    e = html.escape
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">'
            f'<rect width="1920" height="1080" fill="{style["background"]}"/>'
            + pattern_svg(style)
            + f'<g font-family="sans-serif" fill="{style["foreground"]}">'
            f'<text x="300" y="380" font-size="30" letter-spacing="6">{e(style["team"].upper())}</text>'
            f'<text x="300" y="510" font-size="94" font-weight="bold">{e(config["OS_NAME"])}</text>'
            f'<text x="300" y="580" font-size="27">{e(style["mission"])}</text>'
            f'<text x="300" y="850" font-size="22">{e(config["OS_VERSION"])} / {e(config["BUILD_CHANNEL"])}</text></g></svg>')


def logo(style):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">'
            f'<rect x="12" y="12" width="488" height="488" rx="125" fill="{style["background"]}"/>'
            f'<circle cx="256" cy="256" r="195" fill="none" stroke="{style["accent"]}" stroke-width="8"/>'
            f'<text x="256" y="290" text-anchor="middle" fill="{style["foreground"]}" font-family="sans-serif" font-size="92" font-weight="bold">{style["mark"]}</text></svg>')


def welcome(config, style, guide=False):
    e = html.escape
    if guide:
        content = ''.join(f'<section id="task-{i}"><h2>{e(label)}</h2>'
                          '<p>TODO tim: tulis langkah penggunaan, contoh masukan, hasil yang diharapkan, '
                          'dan cara menangani kegagalan fitur kelompok.</p></section>'
                          for i, label in enumerate(style['actions'], 1))
        content += '<p><a href="welcome.html">Kembali ke halaman sambutan</a></p>'
    else:
        content = '<p class="eyebrow">' + e(style['team']) + ' / XFCE EDITION</p>'
        content += '<h1>' + e(config['OS_NAME']) + '</h1><p class="mission">' + e(style['mission']) + '</p>'
        content += '<p>Disiapkan untuk ' + e(style['audience']) + '.</p><div class="actions">'
        content += ''.join(f'<a href="guide.html#task-{i}"><span>0{i}</span>{e(a)}<b>→</b></a>'
                           for i, a in enumerate(style['actions'], 1))
        content += '</div><p class="note">Panduan fitur masih berupa template. Lengkapi sebelum rilis.</p>'
    return f'''<!doctype html><html lang="id"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(config['OS_NAME'])} | {e(style['team'])}</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:{style['background']};color:{style['foreground']};font-family:system-ui,sans-serif;line-height:1.6}}main{{max-width:1080px;margin:auto;padding:70px 42px}}header{{display:flex;align-items:center;justify-content:space-between;gap:20px}}header img{{width:72px}}.eyebrow{{letter-spacing:.17em;text-transform:uppercase;margin-top:55px}}h1{{font-size:clamp(44px,7vw,80px);line-height:1.1;margin:18px 0}}.mission{{font-size:22px;max-width:720px}}.actions{{margin:45px 0 24px;display:grid;gap:14px}}a{{color:inherit}}.actions a{{text-decoration:none;border:1px solid {style['accent']};padding:18px 22px;display:flex;align-items:center;gap:22px;border-radius:10px}}a:focus-visible{{outline:3px solid {style['foreground']};outline-offset:5px}}.actions span{{color:{style['accent']}}}.actions b{{margin-left:auto}}.note,footer{{font-size:13px}}footer{{margin-top:55px}}section{{padding-top:24px}}@media(max-width:550px){{main{{padding:30px 22px}}.eyebrow{{margin-top:35px}}}}</style>
<main><header><img alt="Logo tim {e(style['team'])}" src="logo.svg"><span>{e(config['OS_VERSION'])} / {e(config['BUILD_CHANNEL'])}</span></header>{content}
<footer>{e(config['BUILD_ID'])} · Berbasis Ubuntu · {e(style['team'])}</footer></main></html>'''


def build(root):
    root = root.resolve()
    config = read_config(root / 'configs/project.env')
    style = read_style(root / 'branding/team-style.json')
    rgb = ', '.join(f'{int(style["background"][i:i+2], 16)/255:.4f}' for i in (1, 3, 5))
    if config['OS_NAME'].startswith('TODO') or config['OS_ID'].startswith('todo'):
        raise ValueError('Ganti identitas TODO di configs/project.env terlebih dahulu')
    dest = root / 'build/team-preview'
    if any(p.is_symlink() for p in (root/'build', dest)):
        raise ValueError('Direktori keluaran tidak boleh berupa symlink')
    dest.mkdir(parents=True, exist_ok=True)
    banner = (f"+{'-'*54}+\n| {style['mark']}  {config['OS_NAME']}\n"
              f"| {style['team']} / {config['OS_VERSION']}\n"
              f"| {style['mission']}\n+{'-'*54}+\n")
    files = {'wallpaper.svg': wallpaper(config, style), 'logo.svg': logo(style),
             'SOURCE-INPUTS.json': json.dumps({
                 'project_config': hashlib.sha256((root/'configs/project.env').read_bytes()).hexdigest(),
                 'team_style': hashlib.sha256((root/'branding/team-style.json').read_bytes()).hexdigest(),
                 'generator': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
             },sort_keys=True,indent=2)+'\n',
             'welcome.html': welcome(config, style), 'guide.html': welcome(config, style, True),
             'banner.txt': banner,
             'trpl-custom-os-release': '\n'.join(f'{k}={config[k]}' for k in REQUIRED) + '\n',
             f'{config["OS_ID"]}-welcome.desktop': '[Desktop Entry]\nType=Application\n'
             f'Name={config["OS_NAME"]} Welcome\nComment=Panduan pengguna tim\n'
             f'Exec=xdg-open /usr/share/{config["OS_ID"]}/welcome.html\n'
             f'Icon={config["OS_ID"]}\nTerminal=false\nCategories=Utility;\n',
             f'{config["OS_ID"]}.plymouth': '[Plymouth Theme]\n'
             f'Name={config["OS_NAME"]}\nDescription=Tema latihan tim\nModuleName=script\n\n'
             f'[script]\nImageDir=/usr/share/plymouth/themes/{config["OS_ID"]}\n'
             f'ScriptFile=/usr/share/plymouth/themes/{config["OS_ID"]}/splash.script\n',
             'splash.script': '// Tema statis latihan untuk VM tanpa enkripsi disk.\n'
             '// Tidak menyediakan dialog password disk atau indikator progres.\n'
             f'Window.SetBackgroundTopColor({rgb});\n'
             f'Window.SetBackgroundBottomColor({rgb});\n'
             'logo.image = Image("logo.png");\n'
             'logo.sprite = Sprite(logo.image);\n'
             'logo.sprite.SetX(Window.GetWidth() / 2 - logo.image.GetWidth() / 2);\n'
             'logo.sprite.SetY(Window.GetHeight() / 2 - logo.image.GetHeight() / 2);\n',
             '50-team-greeter.conf': '[greeter]\n'
             f'background=/usr/share/backgrounds/{config["OS_ID"]}-wallpaper.png\n'
             'user-background=false\nfont-name=Sans 11\n',
             'BUILD-NOTES.txt': 'Hasil generator lokal. Belum dipasang ke OS.\n'
             'Lengkapi TODO panduan. Ekspor SVG ke PNG sebelum Plymouth.\n'
             'Runtime desktop, service, boot dan ISO harus diuji pada VM Linux.\n'}
    for name in files:
        if (dest/name).is_symlink() or ((dest/name).exists() and not (dest/name).is_file()):
            raise ValueError(f'Target harus berupa file biasa: {name}')
    if (dest/'SHA256SUMS').is_symlink():
        raise ValueError('SHA256SUMS tidak boleh berupa symlink')
    for name, text in files.items():
        (dest/name).write_text(text, encoding='utf-8')
    sums = ''.join(f'{hashlib.sha256((dest/n).read_bytes()).hexdigest()}  {n}\n' for n in sorted(files))
    (dest/'SHA256SUMS').write_text(sums, encoding='utf-8')
    print(banner + f'Keluaran: {dest}\nTidak ada perubahan pada sistem operasi.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'check'])
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='root starter resmi')
    args = parser.parse_args()
    try:
        if args.command == 'check':
            read_config(args.root/'configs/project.env')
            read_style(args.root/'branding/team-style.json')
            print('PASS konfigurasi dan style valid. Belum membuktikan runtime OS.')
        else:
            build(args.root)
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f'GAGAL: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
