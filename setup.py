from setuptools import setup

APP = ['app.py']  # The main entry point of your app
DATA_FILES = []  # Any data files that your app uses
OPTIONS = {
    'argv_emulation': True,
    'packages': ['tkinter', 'ttkthemes', 'requests', 'base64', 'collections', 'os', 'time', 'threading', 'datetime'],
    'includes': ['rubicon'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)