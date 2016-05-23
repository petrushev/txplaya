import json
from math import floor, ceil

from PyQt5.QtWidgets import QMenu, QInputDialog
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QMimeData, pyqtSignal, pyqtSlot


class Track(object):

    @classmethod
    def fromData(cls, data):
        track = Track()
        track.id3 = {'Album': data['album'],
                     'Title': data['trackname'],
                     'Artist': data['artist']}
        sec = data['length']
        min_ = int(floor(sec/60))
        sec = int(ceil(sec - min_ * 60))
        track.id3['Length'] = '{0}:{1:02d}'.format(min_, sec)
        return track


class PlaylistModel(QAbstractTableModel):

    info_keys = ('Title', 'Artist', 'Album', 'Length')
    _tracks = []
    currentPosition = None

    trackInserted = pyqtSignal(int, Track)
    trackRemoved = pyqtSignal(int)

    def columnCount(self, parent=QModelIndex()):
        return 4

    def rowCount(self, parent=QModelIndex()):
        return len(self._tracks)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            track_id = index.row()
            info_key = self.info_keys[index.column()]
            return self._tracks[track_id].id3.get(info_key)

        return None

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled \
               | Qt.ItemIsEnabled

    def updateAll(self, playlistData):
        self.beginResetModel()
        self._tracks = [Track.fromData(trackData)
                        for trackData in playlistData]
        self.endResetModel()

    def mimeData(self, indexes):
        # TODO : refactor with utilities.mimeWrapJson
        data = json.dumps({'source': 'playlist',
                           'row': indexes[0].row()})
        mimeData = QMimeData()
        mimeData.setText(data)

        return mimeData

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role==Qt.DisplayRole:
            return self.info_keys[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def setPlayingPosition(self, position):
        self.currentPosition = position

    def isPlaying(self, index):
        return index.row() == self.currentPosition


class PlaylistMenu(QMenu):

    play = pyqtSignal(QModelIndex)
    remove = pyqtSignal(QModelIndex)
    clear = pyqtSignal()
    save = pyqtSignal(unicode)
    reconnect = pyqtSignal()

    def __init__(self, index, isPlaylistEmpty, parent=None):
        QMenu.__init__(self, parent)

        self.trackIndex = index

        if index.row() != -1:
            play = self.addAction("Play")
            play.triggered.connect(self._onPlay)
            remove = self.addAction("Remove")
            remove.triggered.connect(self._onRemove)
        
        if not isPlaylistEmpty:
            clear = self.addAction("Clear")
            clear.triggered.connect(self._onClear)

            save = self.addAction("Save")
            save.triggered.connect(self._onSave)

        reconnect = self.addAction("Reconnect")
        reconnect.triggered.connect(self._onReconnect)

    @pyqtSlot()
    def _onPlay(self):
        self.play.emit(self.trackIndex)

    @pyqtSlot()
    def _onRemove(self):
        self.remove.emit(self.trackIndex)

    @pyqtSlot()
    def _onClear(self):
        self.clear.emit()

    @pyqtSlot()
    def _onReconnect(self):
        self.reconnect.emit()

    @pyqtSlot()
    def _onSave(self):
        playlistName, accepted = QInputDialog.getText(self, 'Save playlist', 'Playlist name:')
        if accepted:
            self.save.emit(playlistName)
