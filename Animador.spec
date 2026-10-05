# Receita do PyInstaller para gerar o Animador.exe (um arquivo só, sem console).
# Uso: pyinstaller Animador.spec

a = Analysis(
    ["AnimadorApp.py"],
    datas=[("recursos", "recursos")],
    hiddenimports=["interface", "Animador", "importlib.machinery", "importlib.util"],
    excludes=["tkinter", "unittest", "pydoc"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="Animador",
    icon="recursos/icone.ico",
    console=False,
    upx=False,
)
