from PyQt5.QtWidgets import QWidget, QShortcut
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QKeySequence

from txplayagui.ui.playlists import Ui_PlaylistsWidget


class PlaylistsWidget(Ui_PlaylistsWidget, QWidget):

    loadPlaylist = pyqtSignal(unicode)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        Ui_PlaylistsWidget.setupUi(self, self)

        self.view.doubleClicked.connect(self.playlistClicked)

        deletePlaylistShortcut = QShortcut(QKeySequence('Del'), self.view)
        deletePlaylistShortcut.setContext(Qt.WidgetShortcut)
        deletePlaylistShortcut.activated.connect(self.onDeletePlaylist)

    def update(self, list_):
        self.view.clear()
        for item in list_:
            self.view.addItem(item)

    def playlistClicked(self, index):
        self.loadPlaylist.emit(index.data())

    def onDeletePlaylist(self):
        from txplayagui.client import deletePlaylist
        selectedIndexes = self.view.selectedIndexes()
        if len(selectedIndexes) > 0:
            playlistName = selectedIndexes[0].data()
            _ = deletePlaylist(playlistName)
