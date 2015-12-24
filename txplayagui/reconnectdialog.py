from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog

from txplayagui.ui.reconnectdialog import Ui_ReconnectDialog
from txplayagui.settings import host, port, setHost, setPort


class ReconnectDialog(Ui_ReconnectDialog, QDialog):

    reconnected = pyqtSignal()
    reconnectCanceled = pyqtSignal()

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        Ui_ReconnectDialog.setupUi(self, self)

        self.addressBox.setText(host())
        self.portBox.setText(str(port()))

        self.reconnectButton.clicked.connect(self.onReconnect)
        self.closeButton.clicked.connect(self.onClose)

    def onReconnect(self):
        setHost(self.addressBox.text().strip())
        setPort(int(self.portBox.text()))
        self.reconnected.emit()
        self.close()

    def onClose(self):
        self.reconnectCanceled.emit()
        self.close()
