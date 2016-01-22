from PyQt5.QtWidgets import QDialog

from txplayagui.ui.reconnectdialog import Ui_ReconnectDialog
from txplayagui.settings import host, port, setHost, setPort


class ReconnectDialog(Ui_ReconnectDialog, QDialog):

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
        self.accept()

    def onClose(self):
        self.reject()
