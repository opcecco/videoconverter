# -*- mode: python ; coding: utf-8 -*-

import gooey
gooey_root = os.path.dirname(gooey.__file__)

block_cipher = None

image_overrides = Tree('images', prefix='images')

options = [
    ('u', None, 'OPTION'),
    ('W ignore', None, 'OPTION'),
]

a = Analysis(['app.py'],  # replace me with your path
             pathex=['app.py'],
             binaries=[
                ('ffmpeg-7.1-essentials_build/bin/ffmpeg.exe', 'ffmpeg-7.1-essentials_build/bin'),
                ('ffmpeg-7.1-essentials_build/bin/ffprobe.exe', 'ffmpeg-7.1-essentials_build/bin'),
            ],
             datas=[('images', 'images')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          options,
          name='zutano_videoconverter_v1.7.1',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon=os.path.join('images', 'program_icon.png'))
