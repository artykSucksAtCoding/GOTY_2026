# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller-спецификация для сборки Best Game Ever в один каталог (--onedir),
который потом упаковывается в setup.exe скриптом installer/installer.iss
(Inno Setup).

Собирать ТОЛЬКО из корня репозитория (там, где лежат images/, sound/, code/):
    pyinstaller installer/game.spec --noconfirm

Результат появится в installer/dist/BestGameEver/ (BestGameEver.exe + рядом
папка _internal со всеми ресурсами и Python-зависимостями).

Почему --onedir, а не --onefile: --onefile каждый запуск распаковывает всё
приложение (несколько сотен МБ из-за numpy/scipy/scikit-learn) во временную
папку — это заметно медленнее при старте игры. --onedir запускается сразу.
"""
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), ".."))

block_cipher = None

# scikit-learn динамически подгружает часть своих подмодулей (в т.ч. при
# unpickling model.joblib через joblib.load) — collect_all надёжнее, чем
# угадывать конкретные hiddenimports, которые могут отличаться между
# версиями sklearn/scipy. Собираем ДО создания Analysis и передаём как
# обычные аргументы конструктора (добавлять их в a.datas/a.binaries уже
# ПОСЛЕ Analysis() нельзя — формат TOC там уже другой, будет падать).
from PyInstaller.utils.hooks import collect_all

extra_datas, extra_binaries, extra_hiddenimports = [], [], []
for pkg in ("sklearn", "scipy", "joblib"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    extra_datas += pkg_datas
    extra_binaries += pkg_binaries
    extra_hiddenimports += pkg_hiddenimports

a = Analysis(
    [os.path.join(REPO_ROOT, "code", "platformer", "main.py")],
    pathex=[os.path.join(REPO_ROOT, "code", "platformer")],
    binaries=extra_binaries,
    datas=[
        (os.path.join(REPO_ROOT, "images"), "images"),
        (os.path.join(REPO_ROOT, "sound"), "sound"),
        (
            os.path.join(REPO_ROOT, "code", "weapon_recogniser", "model.joblib"),
            os.path.join("code", "weapon_recogniser"),
        ),
    ] + extra_datas,
    hiddenimports=extra_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BestGameEver",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BestGameEver",
)
