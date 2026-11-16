#!/usr/bin/env python3
"""Prepare an explicit rootfs overlay and apply only reviewed manifest paths.

prepare/plan are local, root-free steps. apply is exclusively for Ubuntu VM or
Cubic chroot. It does not install packages, purge desktops, start services,
configure firewall, or rebuild initramfs: those operations have separate labs.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('studio', HERE/'studio.py')
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_child(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise ValueError('Target manifest harus relatif tanpa ..')
    target = root/rel
    current = root
    if root.is_symlink():
        raise ValueError('Root target berupa symlink')
    for part in rel.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f'Target symlink ditolak: {current}')
    return target


def desktop(name, executable, icon, terminal=False):
    return ('[Desktop Entry]\nType=Application\n'+f'Name={name}\nExec={executable}\n'
            f'Icon={icon}\nTerminal={str(terminal).lower()}\nCategories=Utility;\n')


def panel_xml(os_id, profile):
    root = ET.Element('channel', name='xfce4-panel', version='1.0')
    def prop(parent, name, kind, value=None):
        attrs = dict(name=name, type=kind)
        if value is not None:
            attrs['value'] = str(value).lower() if isinstance(value, bool) else str(value)
        return ET.SubElement(parent, 'property', attrs)
    def array(parent, name, kind, values):
        node = prop(parent, name, 'array')
        for v in values:
            ET.SubElement(node, 'value', type=kind, value=str(v))
        return node
    prop(root, 'configver', 'int', 2)
    panels = array(root, 'panels', 'int', [1, 2])
    for num, position, size, length, plugins in [
        (1, 'p=6;x=0;y=0', profile['top_panel_size'], 100, [1,2,3,4,5,6]),
        (2, 'p=10;x=0;y=0', profile['dock_size'], 36, [7,8,9,10])]:
        node = prop(panels, f'panel-{num}', 'empty')
        for name,kind,value in [('position','string',position),('position-locked','bool',True),
                                ('size','uint',size),('length','uint',length),
                                ('length-adjust','bool',True),('autohide-behavior','uint',0)]:
            prop(node,name,kind,value)
        array(node, 'plugin-ids', 'int', plugins)
    plugins = prop(root, 'plugins', 'empty')
    for num, kind in [(1,'applicationsmenu'),(2,'tasklist'),(3,'separator'),
                      (4,'systray'),(5,'clock'),(6,'actions')]:
        node = prop(plugins, f'plugin-{num}', 'string', kind)
        if num == 1:
            prop(node, 'button-title', 'string', os_id.upper())
            prop(node, 'show-button-title', 'bool', True)
            prop(node, 'button-icon', 'string', os_id)
        if num == 3:
            prop(node, 'expand', 'bool', True)
            prop(node, 'style', 'uint', 0)
    for num, suffix in [(7,'center'),(8,'terminal'),(9,'files'),(10,'welcome')]:
        node = prop(plugins, f'plugin-{num}', 'string', 'launcher')
        array(node, 'items', 'string', [f'{os_id}-{suffix}.desktop'])
    return ET.tostring(root, encoding='unicode')+'\n'


def settings_xml(profile):
    return (f'<channel name="xsettings" version="1.0"><property name="Net" type="empty">'
            f'<property name="ThemeName" type="string" value="{profile["gtk_theme"]}"/>'
            f'<property name="IconThemeName" type="string" value="{profile["icon_theme"]}"/></property>'
            f'<property name="Gtk" type="empty"><property name="FontName" type="string" value="{profile["font"]}"/></property></channel>\n')


def prepare(root):
    root = root.resolve()
    config = studio.read_config(root/'configs/project.env')
    style = studio.read_style(root/'branding/team-style.json')
    profile = json.loads((root/'branding/desktop-profile.json').read_text())
    expected = {'profile_revision','gtk_theme','icon_theme','font','terminal_font',
                'top_panel_size','dock_size','compositing','first_login_welcome'}
    if set(profile) != expected:
        raise ValueError('Kunci desktop-profile.json tidak sesuai contoh')
    for key in ['profile_revision','gtk_theme','icon_theme','font','terminal_font']:
        if not isinstance(profile[key],str) or not re.fullmatch(r'[A-Za-z0-9 ._-]{1,50}', profile[key]):
            raise ValueError(f'Nilai profile {key} tidak valid')
    for key in ['top_panel_size','dock_size']:
        if type(profile[key]) is not int or not 24 <= profile[key] <= 64:
            raise ValueError('Ukuran panel harus 24 sampai 64')
    for key in ['compositing','first_login_welcome']:
        if type(profile[key]) is not bool:
            raise ValueError(f'{key} harus true atau false')
    os_id = config['OS_ID']
    service = config.get('CUSTOM_SERVICE','')
    marker = config.get('CUSTOM_SERVICE_HEALTH_PATTERN','')
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,55}\.service',service):
        raise ValueError('CUSTOM_SERVICE harus berupa nama unit lengkap yang valid')
    if not marker or len(marker)>80 or any(ord(c)<32 for c in marker):
        raise ValueError('Isi CUSTOM_SERVICE_HEALTH_PATTERN')
    wp = config.get('BRANDING_WALLPAPER_PATH','')
    logo = config.get('BRANDING_LOGO_PATH','')
    if not re.fullmatch(r'/usr/share/backgrounds/[a-z0-9.-]+\.png',wp):
        raise ValueError('Wallpaper target harus PNG di /usr/share/backgrounds')
    if not re.fullmatch(r'/usr/share/pixmaps/[a-z0-9.-]+\.svg',logo):
        raise ValueError('Logo target harus SVG di /usr/share/pixmaps')
    monitor=f'/usr/local/lib/{os_id}/team-health'
    if config.get('MONITOR_COMMAND')!=monitor:
        raise ValueError(f'MONITOR_COMMAND harus {monitor} untuk resep contoh')
    if config.get('CUSTOM_FEATURE_COMMAND')!=f'/usr/local/lib/{os_id}/feature-self-test':
        raise ValueError('CUSTOM_FEATURE_COMMAND harus menunjuk feature-self-test resep')
    if config.get('SECURITY_PATHS')!=f'/etc/{os_id} /var/lib/{os_id}':
        raise ValueError('SECURITY_PATHS resep: /etc/OS_ID /var/lib/OS_ID')
    if logo!=f'/usr/share/pixmaps/{os_id}.svg':
        raise ValueError('Nama logo resep harus /usr/share/pixmaps/OS_ID.svg')
    preview=root/'build/team-preview'
    provenance=json.loads((preview/'SOURCE-INPUTS.json').read_text())
    expected_inputs=dict(project_config=digest(root/'configs/project.env'),
                         team_style=digest(root/'branding/team-style.json'),
                         generator=digest(HERE/'studio.py'))
    if provenance!=expected_inputs:
        raise ValueError('Aset tidak sesuai input/source aktif. Jalankan studio build dan ekspor ulang.')
    required=['welcome.html','guide.html','logo.svg','banner.txt','trpl-custom-os-release',
              'wallpaper.png','logo.png',f'{os_id}.plymouth','splash.script']
    for name in required:
        source=safe_child(preview,name)
        if not source.is_file():raise ValueError('Source belum tersedia: '+name)
    for name in ['wallpaper.png','logo.png']:
        if not (preview/name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError(name+' bukan PNG')
    safe_child(root,'build/team-overlay')
    output=root/'build/team-overlay'
    output.mkdir(parents=True,exist_ok=True)
    records=[]
    def put(target, data, mode=0o644):
        path=safe_child(output,target.lstrip('/'))
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data if isinstance(data,bytes) else data.encode())
        path.chmod(mode)
        records.append(dict(path=target.lstrip('/'),mode=mode,sha256=digest(path)))
    for name in ['welcome.html','guide.html','logo.svg','banner.txt']:
        put(f'/usr/share/{os_id}/{name}',(preview/name).read_bytes())
    put(wp,(preview/'wallpaper.png').read_bytes())
    put(logo,(preview/'logo.svg').read_bytes())
    put('/etc/trpl-custom-os-release',(preview/'trpl-custom-os-release').read_bytes())
    put(f'/etc/{os_id}/policy.txt','Konfigurasi produk dikelola root; data workspace milik pengguna.\n')
    put(f'/var/lib/{os_id}/README','Direktori data sistem contoh. Jangan simpan data pribadi di image.\n')
    info=dict(id=os_id,name=config['OS_NAME'],build=config['BUILD_ID'],mission=style['mission'],
              wallpaper=wp,welcome=f'/usr/share/{os_id}/welcome.html',
              profile_revision=profile['profile_revision'],
              first_login_welcome=profile['first_login_welcome'])
    put(f'/usr/local/lib/{os_id}/ui.json',json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    for filename, target in [('team-center.py','team-center'),('team-session.py','team-session'),
                             ('team-health.sh','team-health')]:
        content=(HERE/'templates'/filename).read_text().replace('@HEALTH_MARKER@',shlex.quote(marker))
        put(f'/usr/local/lib/{os_id}/{target}',content,0o755)
    for filename in ['team-feature.py','feature-menu.sh']:
        put(f'/usr/local/lib/{os_id}/{filename}',(HERE/filename).read_bytes(),0o755)
    put(f'/usr/local/lib/{os_id}/tests/test-feature.py',(HERE/'tests/test-feature.py').read_bytes())
    put(f'/usr/local/lib/{os_id}/feature-self-test',
        f'#!/usr/bin/env bash\nexec python3 /usr/local/lib/{os_id}/tests/test-feature.py\n',0o755)
    apps={
      'center':desktop(config['OS_NAME']+' Control Center',f'/usr/local/lib/{os_id}/team-center',os_id),
      'terminal':desktop(config['OS_NAME']+' Terminal','xfce4-terminal --command="bash --login"','utilities-terminal'),
      'files':desktop(config['OS_NAME']+' Files','thunar','system-file-manager'),
      'welcome':desktop(config['OS_NAME']+' Welcome',f'xdg-open /usr/share/{os_id}/welcome.html',os_id)}
    for key,value in apps.items():
        put(f'/usr/share/applications/{os_id}-{key}.desktop',value)
    for num,key in [(7,'center'),(8,'terminal'),(9,'files'),(10,'welcome')]:
        put(f'/etc/skel/.config/xfce4/panel/launcher-{num}/{os_id}-{key}.desktop',apps[key])
    profile_base='/etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml'
    put(profile_base+'/xfce4-panel.xml',panel_xml(os_id,profile))
    put(profile_base+'/xsettings.xml',settings_xml(profile))
    put(profile_base+'/xfwm4.xml','<channel name="xfwm4" version="1.0"><property name="general" type="empty">'
        f'<property name="theme" type="string" value="{profile["gtk_theme"]}"/>'
        f'<property name="use_compositing" type="bool" value="{str(profile["compositing"]).lower()}"/>'
        '</property></channel>\n')
    put('/etc/skel/.config/xfce4/terminal/terminalrc',
        '[Configuration]\nFontName='+profile['terminal_font']+'\nColorForeground='+style['foreground']+
        '\nColorBackground='+style['background']+'\nScrollingLines=10000\n')
    put(f'/etc/xdg/autostart/{os_id}-session.desktop',desktop(config['OS_NAME']+' Session',
        f'/usr/local/lib/{os_id}/team-session',os_id)+'OnlyShowIn=XFCE;\n')
    put(f'/etc/profile.d/90-{os_id}-banner.sh',
        f'case $- in *i*) test ! -r /usr/share/{os_id}/banner.txt || cat /usr/share/{os_id}/banner.txt ;; esac\n')
    put('/etc/lightdm/lightdm.conf.d/50-team-desktop.conf',
        '[Seat:*]\ngreeter-session=lightdm-gtk-greeter\nuser-session=xfce\n')
    put('/etc/lightdm/lightdm-gtk-greeter.conf.d/50-team-greeter.conf',
        f'[greeter]\nbackground={wp}\nuser-background=false\n'
        f'theme-name={profile["gtk_theme"]}\nicon-theme-name={profile["icon_theme"]}\nfont-name=Sans 11\n')
    for name in [f'{os_id}.plymouth','splash.script','logo.png']:
        put(f'/usr/share/plymouth/themes/{os_id}/{name}',(preview/name).read_bytes())
    put(f'/etc/systemd/system/{service}',
        f'[Unit]\nDescription={config["OS_NAME"]} readiness and resource report\nAfter=local-fs.target\n\n'
        f'[Service]\nType=oneshot\nRemainAfterExit=yes\nDynamicUser=yes\nExecStart={monitor}\n'
        'NoNewPrivileges=yes\nPrivateTmp=yes\nProtectSystem=strict\nProtectHome=yes\n'
        'StandardOutput=journal\nStandardError=journal\n\n[Install]\nWantedBy=multi-user.target\n')
    input_paths=[root/'configs/project.env',root/'branding/team-style.json',
                 root/'branding/desktop-profile.json',HERE/'recipe.py',
                 HERE/'studio.py',HERE/'team-feature.py',HERE/'feature-menu.sh',
                 HERE/'tests/test-feature.py',
                 *sorted((HERE/'templates').glob('*'))]
    inputs={str(p.resolve().relative_to(root)):digest(p) for p in input_paths if p.is_file()}
    manifest=dict(schema=1,os_id=os_id,build_id=config['BUILD_ID'],service=service,
                  root=str(output),inputs=inputs,files=sorted(records,key=lambda r:r['path']))
    (root/'build/team-overlay-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'PREPARED {len(records)} files: {output}')


def load_manifest(root):
    manifest=json.loads((root/'build/team-overlay-manifest.json').read_text())
    c=studio.read_config(root/'configs/project.env')
    if manifest['os_id']!=c['OS_ID'] or manifest['build_id']!=c['BUILD_ID']:
        raise ValueError('Manifest tidak sesuai identitas/build aktif. Jalankan prepare ulang.')
    for relative,expected in manifest['inputs'].items():
        if digest(safe_child(root,relative))!=expected:
            raise ValueError('Input berubah; lakukan build/prepare ulang: '+relative)
    overlay=root/'build/team-overlay'
    seen=set()
    os_id=c['OS_ID']
    exact={c['BRANDING_WALLPAPER_PATH'].lstrip('/'),c['BRANDING_LOGO_PATH'].lstrip('/'),
           'etc/trpl-custom-os-release',f'etc/systemd/system/{c["CUSTOM_SERVICE"]}',
           'etc/lightdm/lightdm.conf.d/50-team-desktop.conf',
           'etc/lightdm/lightdm-gtk-greeter.conf.d/50-team-greeter.conf',
           f'etc/profile.d/90-{os_id}-banner.sh',f'etc/xdg/autostart/{os_id}-session.desktop'}
    prefixes=(f'usr/share/{os_id}/',f'usr/local/lib/{os_id}/',
              f'usr/share/plymouth/themes/{os_id}/','etc/skel/.config/xfce4/',
              f'etc/{os_id}/',f'var/lib/{os_id}/')
    for record in manifest['files']:
        relative=record['path']
        if relative in seen:raise ValueError('Target ganda')
        seen.add(relative)
        app=relative.startswith(f'usr/share/applications/{os_id}-') and relative.endswith('.desktop')
        if relative not in exact and not relative.startswith(prefixes) and not app:
            raise ValueError('Target di luar area produk')
        if not isinstance(record['mode'],int) or record['mode'] not in (0o644,0o755):
            raise ValueError('Mode tidak diizinkan')
        if digest(safe_child(overlay,relative))!=record['sha256']:
            raise ValueError('Source berubah setelah prepare: '+relative)
    return manifest,overlay


def verify_target(mode,snapshot):
    if platform.system()!='Linux' or platform.machine()!='x86_64' or os.geteuid()!=0:
        raise ValueError('Apply memerlukan root pada Ubuntu AMD64 target, bukan macOS')
    release=Path('/etc/os-release').read_text()
    if not re.search(r'^ID=ubuntu$',release,re.M) or not re.search(r'^VERSION_ID="24\.04"$',release,re.M):
        raise ValueError('Target bukan Ubuntu 24.04')
    chroot=subprocess.run(['systemd-detect-virt','--chroot'],capture_output=True).returncode==0
    if mode=='image':
        if not chroot:raise ValueError('Mode image hanya untuk chroot Cubic yang terdeteksi')
    else:
        if chroot:raise ValueError('Gunakan mode image untuk chroot')
        result=subprocess.run(['systemd-detect-virt','--vm'],capture_output=True,text=True)
        if result.returncode or not snapshot:raise ValueError('VM dan pengakuan snapshot wajib')
        if not Path('/sys/firmware/efi').exists():raise ValueError('UEFI target tidak terdeteksi')


def install_manifest(root,target,backup=None):
    manifest,overlay=load_manifest(root)
    # Validate every path and collision before touching any target.
    for r in manifest['files']:
        dest=safe_child(target,r['path'])
        if dest.exists() and not dest.is_file():raise ValueError('Target bukan file: '+str(dest))
    changed=0
    for r in manifest['files']:
        source=safe_child(overlay,r['path']);dest=safe_child(target,r['path'])
        same=dest.is_file() and digest(dest)==r['sha256'] and stat.S_IMODE(dest.stat().st_mode)==r['mode']
        if same:continue
        if backup and dest.exists():
            prior=safe_child(backup,r['path']);prior.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(dest,prior)
        # Give newly created directories an explicit non-world-writable mode.
        current=target
        for part in Path(r['path']).parts[:-1]:
            current /= part
            if not current.exists():current.mkdir(mode=0o755)
        fd,tmp=tempfile.mkstemp(prefix='.team-',dir=dest.parent)
        try:
            with os.fdopen(fd,'wb') as f:f.write(source.read_bytes())
            os.chmod(tmp,r['mode']);os.replace(tmp,dest)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        changed+=1
    return changed


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['prepare','plan','apply'])
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--mode',choices=['vm','image'])
    p.add_argument('--confirm-snapshot',default='')
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args();root=a.root.resolve()
    try:
        if a.command=='prepare':prepare(root);return 0
        manifest,overlay=load_manifest(root)
        if a.command=='plan' or a.dry_run:
            for r in manifest['files']:print(f'{r["mode"]:04o} /{r["path"]}')
            print('PLAN ONLY - tidak ada perubahan sistem');return 0
        if not a.mode:raise ValueError('Pilih --mode vm atau --mode image secara eksplisit')
        verify_target(a.mode,a.confirm_snapshot)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=Path('/var/backups')/manifest['os_id']/stamp
        backup.mkdir(parents=True,exist_ok=False)
        changed=install_manifest(root,Path('/'),backup)
        (backup/'RECORD.json').write_text(json.dumps(dict(build=manifest['build_id'],mode=a.mode,changed=changed),indent=2))
        print(f'APPLIED changed={changed} backup={backup}')
        print('Aktivasi service/firewall/Plymouth dan pengujian dilakukan pada langkah modul berikutnya.')
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('GAGAL:',error,file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
