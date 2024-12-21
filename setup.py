from setuptools import setup

APP = ['app.py']  # The main entry point of your app
DATA_FILES = [
    'settings.py',
    'openai_api.py',
    'screenshot.py',
    'camera.py',
    'audio_feedback.py',
    'history.py',
    'session_history.json'
]
OPTIONS = {
    'argv_emulation': True,
    'packages': ['ttkthemes', 'openai', 'PIL', 'matplotlib', 'cv2', 'dotenv'],
    'includes': ['tkinter'],
    'excludes': ['zmq'],
    # 'iconfile': 'path/to/your/icon.icns',  # Commented out for now
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)