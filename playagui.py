import sys

from PyQt5.QtWidgets import QApplication

from txplayagui.app import MainWindow, translator

if __name__ == '__main__':
    qtapp = QApplication(sys.argv)

    if translator is not None:
        qtapp.installTranslator(translator)

    ui = MainWindow()
    ui.show()

    sys.exit(qtapp.exec_())
