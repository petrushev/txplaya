import json

from PyQt5.QtWidgets import QMainWindow, QWidget, QSpacerItem, QSizePolicy
from PyQt5.QtCore import QLocale, QTranslator, pyqtSlot, QModelIndex, QPoint

from txplayagui.ui.main import Ui_MainWindow
from txplayagui.playlist import PlaylistModel, PlaylistMenu
from txplayagui.library import LibraryModel
from txplayagui.utilities import unwrapMime
from txplayagui.infostream import QInfoStream

# load translations
locale = QLocale.system().name()
translator = QTranslator()

_success = translator.load('txplayagui/l10n/deskdict.' + locale + '.qm')
if not _success:
    translator = None


class MainWindow(Ui_MainWindow, QMainWindow):

    def __init__(self):

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

        self.scanProgressBar.hide()
        spacerItem = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.scanControlsLayout.addItem(spacerItem)

        self.libraryModel = LibraryModel()
        self.libraryModel.toggleRow.connect(self.onToggleRow)
        self.libraryTreeView.setModel(self.libraryModel)
        self.libraryTreeView.doubleClicked.connect(self.onLibraryDoubleClick)
        self.queryLibSearchBox.textChanged.connect(self.onLibraryQueryChanged)
        self.clearLibSearchButton.clicked.connect(self.onLibraryQueryClear)

        self.fetchLibrary()
        self.infoStreamStart()

    def infoStreamStart(self):
        self.infoStream = QInfoStream()
        self.infoStream.trackStarted.connect(self.onTrackStarted)
        self.infoStream.playbackFinished.connect(self.onPlaybackFinished)
        self.infoStream.playlistChanged.connect(self.onPlaylistChanged)

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

                    from txplayagui.client import insert
                    _ = insert(filepath, rowTarget)
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
        moveTrack(rowSource, rowTarget)

    def getCallbackLogServer(self, response):

        @pyqtSlot()
        def logServer():
            print '[%d] %s' % (response.statusCode, response.data)

        return logServer

    def getCallbackLibraryLoaded(self, response):

        @pyqtSlot()
        def libraryLoaded():
            data = json.loads(response.data)
            self.libraryModel.loadData(data['library'])

            if 'msg' in data:
                print data['msg']

        return libraryLoaded

    def _play(self, index):
        from txplayagui.client import play
        _ = play(position=index.row())

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
        _ = remove(index.row())

    @pyqtSlot()
    def onPlaylistMenuClear(self):
        from txplayagui.client import clear
        _ = clear()

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
        from txplayagui.client import stop
        response = stop()
        response.finished.connect(self.getCallbackLogServer(response))

    @pyqtSlot(bool)
    def onToggleLibrary(self, show):
        if show:
            self.libraryDock.show()
        else:
            self.libraryDock.hide()

    @pyqtSlot()
    def rescanLibraryClicked(self):
        from txplayagui.client import rescanLibrary
        self.scanResponse = rescanLibrary()
        self.scanResponse.lineReceived.connect(self.scanProgress)
        self.rescanLibraryButton.hide()
        self.scanProgressBar.show()
        self.scanControlsLayout.removeItem(self.scanControlsLayout.itemAt(2))

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
        _ = libraryInsert(hashes)

    @pyqtSlot(object)
    def onTrackStarted(self, trackData):
        trackname = trackData['track']['trackname']
        self.playingLabel.setText(trackname)

    @pyqtSlot()
    def onPlaybackFinished(self):
        self.playingLabel.setText('not playing')

    @pyqtSlot(object)
    def onPlaylistChanged(self, data):
        self.playlistModel.updateAll(data['playlist'])

    @pyqtSlot(int, QModelIndex, bool)
    def onToggleRow(self, row, parentIndex, isShown):
        self.libraryTreeView.setRowHidden(row, parentIndex, not isShown)

    @pyqtSlot(unicode)
    def onLibraryQueryChanged(self, query):
        if len(query) > 2:
            self.libraryModel.filter(query)
        elif query == '':
            return self.libraryModel.showAll()

    @pyqtSlot()
    def onLibraryQueryClear(self):
        return self.libraryModel.showAll()

    @pyqtSlot(str)
    def scanProgress(self, progress):
        data = json.loads(progress.rstrip())
        if 'scanprogress' in data:
            progress = data['scanprogress']
            self.scanProgressBar.setValue(progress)
        else:
            self.scanResponse.close()
            del self.scanResponse

            self.libraryModel.loadData(data['library'])
            self.rescanLibraryButton.show()
            spacerItem = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.scanControlsLayout.addItem(spacerItem)
            self.scanProgressBar.hide()

            # apply filter if active
            query = self.queryLibSearchBox.text().lower()
            if len(query) > 2:
                self.libraryModel.filter(query)
