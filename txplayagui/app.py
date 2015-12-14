import json

from PyQt5.QtWidgets import QMainWindow, QWidget
from PyQt5.QtCore import QLocale, QTranslator, pyqtSlot, QModelIndex, QPoint

from txplayagui.ui.main import Ui_MainWindow
from txplayagui.playlist import PlaylistModel, Track, PlaylistMenu
from txplayagui.library import LibraryModel
from txplayagui.library import unwrapMime
from txplayagui.infostream import QInfoStream

# load translations
locale = QLocale.system().name()
translator = QTranslator()

_success = translator.load('txplayagui/l10n/deskdict.' + locale + '.qm')
if not _success:
    translator = None


class MainWindow(Ui_MainWindow, QMainWindow):

    def __init__(self):
        from txplayagui.client import current

        QMainWindow.__init__(self)
        Ui_MainWindow.setupUi(self, self)

        self.playlistDrop.dragEnterEvent = self.playlistDragEnterEvent
        self.playlistDrop.dropEvent = self.playlistDropEvent

        self.playlistModel = PlaylistModel()
        self.playlistTable.setModel(self.playlistModel)

        self.playlistTable.customContextMenuRequested.connect(self.playlistContextMenu)
        self.playlistTable.doubleClicked.connect(self.onPlaylistDoubleClick)

        self.playButton.clicked.connect(self.onPlaySelected)
        self.pauseButton.clicked.connect(self.onPauseClicked)
        self.stopButton.clicked.connect(self.onStopClicked)

        self.libraryDock.setTitleBarWidget(QWidget())
        self.toggleLibraryButton.clicked.connect(self.onToggleLibrary)
        self.rescanLibraryButton.clicked.connect(self.rescanLibraryClicked)

        self.libraryModel = LibraryModel()
        self.libraryTreeView.setModel(self.libraryModel)
        self.libraryTreeView.doubleClicked.connect(self.onLibraryDoubleClick)

        self.fetchPlaylist()
        self.fetchLibrary()
        currentResponse = current()
        currentResponse.finished.connect(self.getCallbackCurrentFetched(currentResponse))

        self.infoStream = QInfoStream()
        self.infoStream.trackStarted.connect(self.onTrackStarted)
        self.infoStream.playlistFinished.connect(self.onPlaylistFinished)

    def fetchPlaylist(self):
        from txplayagui.client import getPlaylist
        response = getPlaylist()
        response.finished.connect(self.getCallbackPlaylistUpdated(response))

    def fetchLibrary(self):
        from txplayagui.client import getLibrary
        response = getLibrary()
        response.finished.connect(self.getCallbackLibraryLoaded(response))

    def playlistDragEnterEvent(self, event):
        self._playlistDragDropHandle(event, isDropped=False)

    def playlistDropEvent(self, event):
        self._playlistDragDropHandle(event, isDropped=True)

    def _playlistDragDropHandle(self, event, isDropped):
        mimeData = event.mimeData()

        rowPosition = event.pos().y() - self.playlistTable.rowHeight(0)
        rowTarget = self.playlistTable.rowAt(rowPosition)

        if rowTarget == -1:
            rowTarget = self.playlistModel.rowCount()

        if mimeData.hasUrls():
            urls = mimeData.urls()
            if len(urls) > 0:
                url = urls[0]
                if url.isLocalFile():
                    if not isDropped:
                        event.acceptProposedAction()
                        return

                    # file dropped
                    filepath = url.toLocalFile()
                    track = Track(filepath)

                    from txplayagui.client import insert
                    response = insert(track, rowTarget)
                    response.finished.connect(self.getCallbackPlaylistUpdated(response))

                    return

        # no urls or not local file
        if not mimeData.hasText():
            return

        text = mimeData.text()
        try:
            data = json.loads(text)
        except ValueError:
            # invalid data passed
            return

        # check for proper flag and position
        if data.get('source') != 'playlist':
            return

        rowSource = data.get('row')
        if not isinstance(rowSource, int):
            return

        if not isDropped:
            event.acceptProposedAction()
            return

        from txplayagui.client import moveTrack
        response = moveTrack(rowSource, rowTarget)
        response.finished.connect(self.getCallbackPlaylistUpdated(response))

    def getCallbackLogServer(self, response):

        @pyqtSlot()
        def logServer():
            print '[%d] %s' % (response.statusCode, response.data)

        return logServer

    def getCallbackCurrentFetched(self, response):

        @pyqtSlot()
        def onCurrentFetched():
            print '[%d] %s' % (response.statusCode, response.data)
            data = json.loads(response.data)

            position = data['position']
            if position == -1:
                position = None
            self.playlistModel.setPlayingPosition(data['position'])

            if position is None:
                self.playingLabel.setText('not playing')
            else:
                self.playingLabel.setText(data['track']['trackname'])

        return onCurrentFetched

    def getCallbackPlaylistUpdated(self, response):

        @pyqtSlot()
        def playlistUpdated():
            data = json.loads(response.data)
            self.playlistModel.updateAll(data['playlist'])

        return playlistUpdated

    def getCallbackLibraryLoaded(self, response):

        @pyqtSlot()
        def libraryLoaded():
            data = json.loads(response.data)
            self.libraryModel.loadData(data['library'])

            if 'msg' in data:
                print data['msg']

        return libraryLoaded

    def _play(self, index):
        from txplayagui.client import play, current
        response = play(position=index.row())

        @pyqtSlot()
        def onFinish():
            print '[%d] %s' % (response.statusCode, response.data)
            data = json.loads(response.data)
            if 'err' in data:
                # playlist not in sync
                self.fetchPlaylist()
                return

            response2 = current()
            response2.finished.connect(self.getCallbackCurrentFetched(response2))

        response.finished.connect(onFinish)

    @pyqtSlot(QPoint)
    def playlistContextMenu(self, position):
        index = self.playlistTable.indexAt(position)

        menu = PlaylistMenu(index)
        menu.play.connect(self.onPlaylistMenuPlay)
        menu.remove.connect(self.onPlaylistMenuRemove)
        menu.clear.connect(self.onPlaylistMenuClear)

        globalPosition = self.playlistTable.mapToGlobal(position)
        menu.exec_(globalPosition)

    @pyqtSlot(QModelIndex)
    def onPlaylistMenuPlay(self, index):
        self._play(index)

    @pyqtSlot(QModelIndex)
    def onPlaylistMenuRemove(self, index):
        from txplayagui.client import remove
        response = remove(index.row())
        response.finished.connect(self.getCallbackPlaylistUpdated(response))

    @pyqtSlot()
    def onPlaylistMenuClear(self):
        from txplayagui.client import clear
        response = clear()
        response.finished.connect(self.getCallbackPlaylistUpdated(response))

    @pyqtSlot(QModelIndex)
    def onPlaylistDoubleClick(self, index):
        self._play(index)

    @pyqtSlot()
    def onPlaySelected(self):
        selectedIdx = self.playlistTable.selectedIndexes()
        if len(selectedIdx) == 0:
            return

        self._play(selectedIdx[0])

    @pyqtSlot()
    def onPauseClicked(self):
        from txplayagui.client import pause
        response = pause()
        response.finished.connect(self.getCallbackLogServer(response))

    @pyqtSlot()
    def onStopClicked(self):
        from txplayagui.client import stop, current
        response = stop()

        @pyqtSlot()
        def onFinish():
            print '[%d] %s' % (response.statusCode, response.data)
            response2 = current()
            response2.finished.connect(self.getCallbackCurrentFetched(response2))

        response.finished.connect(onFinish)

    @pyqtSlot(bool)
    def onToggleLibrary(self, show):
        if show:
            self.libraryDock.show()
        else:
            self.libraryDock.hide()

    @pyqtSlot()
    def rescanLibraryClicked(self):
        from txplayagui.client import rescanLibrary
        response = rescanLibrary()
        response.finished.connect(self.getCallbackLibraryLoaded(response))

    @pyqtSlot(QModelIndex)
    def onLibraryDoubleClick(self, index):
        mimeData = unwrapMime(self.libraryModel.mimeData([index]))[0]
        if 'hash' in mimeData:
            hashes = [mimeData['hash']]

        elif 'album' in mimeData:
            hashes = self.libraryModel.albumHashes(index)
        else:
            # artist clicked
            return

        from txplayagui.client import libraryInsert
        response = libraryInsert(hashes)
        response.finished.connect(self.getCallbackPlaylistUpdated(response))

    @pyqtSlot(object)
    def onTrackStarted(self, trackData):
        trackname = trackData['track']['trackname']
        self.playingLabel.setText(trackname)

    @pyqtSlot()
    def onPlaylistFinished(self):
        self.playingLabel.setText('not playing')
