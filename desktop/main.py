"""
CGTips 3D Desktop Application
Built with PySide6 & QML (Qt Quick)
"""

import os
import sys
from pathlib import Path

# Some Windows Pythons (e.g. Microsoft Store) don't put PySide6's folder on the
# DLL search path, so QML plugins like QtQuick.Controls fail to load.
if sys.platform == "win32" and not getattr(sys, "frozen", False):
    import PySide6
    os.add_dll_directory(os.path.dirname(PySide6.__file__))

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys._MEIPASS)
    base_dir = ROOT_DIR / "desktop"
else:
    base_dir = Path(__file__).resolve().parent
    ROOT_DIR = base_dir.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

import config
from backend.app_bridge import AppBridge
from backend.image_provider import CGTipsImageProvider


def main():
    # Set modern controls style
    QQuickStyle.setStyle("Fusion")

    # High-DPI scaling configuration
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)
    app.setOrganizationName("CGTips")
    app.setApplicationName("CGTips 3D")
    app.setApplicationDisplayName("CGTips 3D Desktop")

    # Set native modern font
    from PySide6.QtGui import QFontDatabase
    font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
    font.setPointSize(11)
    app.setFont(font)

    # Register Font Awesome 6 Free fonts
    fonts_dir = base_dir / "assets" / "fonts"
    if fonts_dir.exists():
        QFontDatabase.addApplicationFont(str(fonts_dir / "fa-solid-900.ttf"))
        QFontDatabase.addApplicationFont(str(fonts_dir / "fa-regular-400.ttf"))

    # Initialize PySide6 backend bridge
    bridge = AppBridge()

    # Register singleton for QML
    qmlRegisterSingletonInstance(AppBridge, "CGTips", 1, 0, "Bridge", bridge)

    # Create QML Application Engine
    engine = QQmlApplicationEngine()

    # Register custom image provider to bypass DNS timeouts and cache images
    image_provider = CGTipsImageProvider()
    engine.addImageProvider("cgtips", image_provider)

    # Base QML directory
    qml_dir = base_dir / "qml"

    # Add QML import paths
    engine.addImportPath(str(qml_dir))

    # Expose bridge to root context as well
    engine.rootContext().setContextProperty("bridge", bridge)

    # Load root QML file
    qml_file = qml_dir / "main.qml"
    engine.load(os.fspath(qml_file))

    if not engine.rootObjects():
        print("Error: Could not load QML main file.", file=sys.stderr)
        sys.exit(-1)

    # Trigger initial direct scraper data load
    bridge.refreshStatus()
    bridge.loadCategories()
    bridge.loadLibrary()

    sys.exit(app.exec())



if __name__ == "__main__":
    main()
