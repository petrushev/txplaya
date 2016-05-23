from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from txplayagui.ui.playlists import Ui_PlaylistsWidget


class PlaylistsWidget(Ui_PlaylistsWidget, QWidget):

    loadPlaylist = pyqtSignal(unicode)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        Ui_PlaylistsWidget.setupUi(self, self)

        self.view.doubleClicked.connect(self.playlistClicked)


    def update(self, list_):
        self.view.clear()
        for item in list_:
            self.view.addItem(item)

    def playlistClicked(self, index):
        self.loadPlaylist.emit(index.data())
