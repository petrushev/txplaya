from math import floor, ceil

from werkzeug.utils import cached_property

from PyQt5.QtWidgets import QMenu, QInputDialog, QWidget
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor

from txplayagui.ui.playlistmenu import Ui_PlaylistMenuWidget
from txplayagui.utilities import mimeWrapJson


class Track(object):

    @classmethod
    def fromData(cls, data):
        track = Track()
        track.id3 = {'Album': data['album'],
                     'Title': data['trackname'],
                     'Artist': data['artist'],
                     'AlbumArtist': data['albumartist'],
                     'Year': data['year'],
                     'TrackNumber': data['tracknumber']}

        track.length = data['length']
        sec = track.length
        min_ = int(floor(sec/60))
        sec = int(ceil(sec - min_ * 60))
        track.id3['Length'] = '{0}:{1:02d}'.format(min_, sec)
        return track

    def getToolTip(self, infoKey):
        return getattr(self, infoKey.lower() + 'Tip')

    @cached_property
    def titleTip(self):
        try:
            return u'%d. %s' % (self.id3['TrackNumber'], self.id3['Title'])
        except TypeError:
            return self.id3['Title']

    @cached_property
    def artistTip(self):
        return self.id3['Artist']

    @cached_property
    def albumTip(self):
        album = self.id3['Album']
        artist = self.id3['Artist']
        albumArtist = self.id3['AlbumArtist']
        if albumArtist != artist:
            album = u'%s - %s' % (album, albumArtist)
        album = album.strip('- ')

        try:
            return u'%s (%d)' % (album, self.id3['Year'])
        except TypeError:
            return album

    @cached_property
    def lengthTip(self):
        return self.id3['Length']


class PlaylistModel(QAbstractTableModel):

    infoKeys = ('Title', 'Artist', 'Album', 'Length')
    _tracks = []
    currentPosition = None
    hasUndo = False
    hasRedo = False

    trackInserted = pyqtSignal(int, Track)
    trackRemoved = pyqtSignal(int)

    def columnCount(self, parent=QModelIndex()):
        return len(self.infoKeys)

    def rowCount(self, parent=QModelIndex()):
        return len(self._tracks)

    def data(self, index, role=Qt.DisplayRole):
        trackId = index.row()
        if role == Qt.DisplayRole:
            infoKey = self.infoKeys[index.column()]
            return self._tracks[trackId].id3.get(infoKey)

        elif role == Qt.ToolTipRole:
            infoKey = self.infoKeys[index.column()]
            return self._tracks[trackId].getToolTip(infoKey)

        elif role == Qt.BackgroundColorRole:
            if trackId == self.currentPosition:
                return QColor(255, 255, 130)

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
        return mimeWrapJson({'source': 'playlist',
                             'row': indexes[0].row()})

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role==Qt.DisplayRole:
            return self.infoKeys[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def setPlayingPosition(self, position):
        self.beginResetModel()
        self.currentPosition = position
        self.endResetModel()

    def isPlaying(self, index):
        return index.row() == self.currentPosition

    def trackActivated(self, trackData=None):
        if trackData is None:
            position = None
        else:
            position = trackData['position']

        self.setPlayingPosition(position)

    def fullLength(self):
        sec = sum([track.length for track in self._tracks])
        min_ = int(floor(sec/60))
        sec = int(ceil(sec - min_ * 60))
        return '{0}:{1:02d}'.format(min_, sec)


class PlaylistMenuWidget(Ui_PlaylistMenuWidget, QWidget):

    def __init__(self):
        QWidget.__init__(self)
        Ui_PlaylistMenuWidget.setupUi(self, self)


class PlaylistMenu(QMenu):

    play = pyqtSignal(QModelIndex)
    remove = pyqtSignal(QModelIndex)
    clear = pyqtSignal()
    save = pyqtSignal(unicode)
    reconnect = pyqtSignal()
    undo = pyqtSignal()
    redo = pyqtSignal()

    def __init__(self, index, isPlaylistEmpty, hasUndo, hasRedo, parent=None):
        QMenu.__init__(self, parent)

        self.trackIndex = index
        self.w = PlaylistMenuWidget()

        if index.row() != -1:
            self.addAction(self.w.play)
            self.w.play.triggered.connect(self._onPlay)
            self.addAction(self.w.remove)
            self.w.remove.triggered.connect(self._onRemove)

        if not isPlaylistEmpty:
            self.addAction(self.w.clear)
            self.w.clear.triggered.connect(self._onClear)

            self.addAction(self.w.save)
            self.w.save.triggered.connect(self._onSave)

        if hasUndo:
            self.addAction(self.w.undo)
            self.w.undo.triggered.connect(self._onUndo)

        if hasRedo:
            self.addAction(self.w.redo)
            self.w.redo.triggered.connect(self._onRedo)

        self.addAction(self.w.reconnect)
        self.w.reconnect.triggered.connect(self._onReconnect)

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

    @pyqtSlot()
    def _onUndo(self):
        self.undo.emit()

    @pyqtSlot()
    def _onRedo(self):
        self.redo.emit()
