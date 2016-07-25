import json

from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QSystemTrayIcon, QMenu
from PyQt5.QtCore import QLocale, QTranslator, pyqtSlot, QModelIndex, QPoint, QTimer, Qt, \
    QSettings

from txplayagui.ui.main import Ui_MainWindow
from txplayagui.playlist import PlaylistModel, PlaylistMenu
from txplayagui.infostream import QInfoStream
from txplayagui.librarywidget import LibraryWidget
from txplayagui.reconnectdialog import ReconnectDialog
from txplayagui.playlistswidget import PlaylistsWidget
from txplayagui.utilities import unwrapMime, httpReceiver

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
        self.nextButton.clicked.connect(self.onNextClicked)
        self.prevButton.clicked.connect(self.onPrevClicked)

        self.libraryDock.setTitleBarWidget(QWidget())
        self.playlistsDock.setTitleBarWidget(QWidget())
        self.toggleLibraryButton.clicked.connect(self.onToggleLibrary)
        self.togglePlaylistsButton.clicked.connect(self.onTogglePlaylists)

        self.library = LibraryWidget(self)
        self.libraryDock.setWidget(self.library)
        self.libraryDock.hide()
        self.library.itemsActivated.connect(self.onLibraryItemActivated)

        self.playlists = PlaylistsWidget(self)
        self.playlistsDock.setWidget(self.playlists)
        self.playlistsDock.hide()
        self.playlists.loadPlaylist.connect(self.onPlaylistLoad)

        self.dockState = 0

        self.settings = QSettings('txplaya', 'txplaya')

        if u'geometry/main' in self.settings.allKeys():
            self.setGeometry(self.settings.value(u'geometry/main'))

            for col in range(self.playlistModel.columnCount()):
                width = self.settings.value(u'geometry/playlist/col/%d' % col)
                self.playlistTable.setColumnWidth(col, int(width))

            dockState = int(self.settings.value(u'geometry/dock/state'))
            self.dockShow(dockState)

        self.systemTray = QSystemTrayIcon(self.windowIcon())
        self.systemTray.setToolTip('Playa')
        self.systemTray.show()
        self.systemTray.activated.connect(self.systemTrayToggle)
        systemTrayMenu = QMenu()
        systemTrayMenu.addAction(self.restore)
        systemTrayMenu.addAction(self.quit)
        self.systemTray.setContextMenu(systemTrayMenu)
        self.restore.triggered.connect(self.restoreWindow)
        self.quit.triggered.connect(self.quitEvent)
        self.quitButton.clicked.connect(self.quitEvent)
        self.quitFlag = False

        self.infoStreamStart()
        QTimer.singleShot(200, self.fetchLibrary)

    def infoStreamStart(self):
        self.infoStream = QInfoStream()
        self.infoStream.trackStarted.connect(self.onTrackStarted)
        self.infoStream.playbackFinished.connect(self.onPlaybackFinished)
        self.infoStream.playbackPaused.connect(self.onPlaybackPaused)
        self.infoStream.playlistChanged.connect(self.onPlaylistChanged)
        self.infoStream.disconnected.connect(self.reconnectDialog)
        self.infoStream.timerUpdated.connect(self.timerUpdated)
        self.infoStream.playlistRegistryUpdated.connect(self.playlistRegistryUpdated)

    def fetchLibrary(self):
        from txplayagui.client import getLibrary
        response = getLibrary()
        response.finished.connect(httpReceiver(response)(self.onLibraryLoaded))

    def playlistDragEnterEvent(self, event):
        self._playlistDragDropHandle(event, isDropped=False)

    def playlistDropEvent(self, event):
        self._playlistDragDropHandle(event, isDropped=True)

    def _playlistDragDropHandle(self, event, isDropped):
        from txplayagui.client import moveTrack, libraryInsert

        mimeData = event.mimeData()

        # get row
        rowPosition = event.pos().y() - self.playlistTable.rowHeight(0)
        rowTarget = self.playlistTable.rowAt(rowPosition)

        if rowTarget == -1:
            # new row
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

        try:
            data = unwrapMime(mimeData)
        except ValueError:
            # invalid data passed
            return

        # check for proper flag
        source = data.get('source')
        if source not in ('playlist', 'library'):
            return

        if not isDropped:
            # drag entered
            event.acceptProposedAction()
            return

        if source == 'playlist':
            rowSource = data['row']
            moveTrack(rowSource, rowTarget)

        elif source == 'library':
            hashes = [item['hash'] for item in data['items']]
            libraryInsert(hashes, position=rowTarget)

    def onLibraryLoaded(self, response):
        try:
            data = json.loads(response.data)
            self.library.rescanFinished(data['library'])

            if 'msg' in data:
                print data['msg']
        except Exception, err:
            print 'Library load error:', repr(err)

    def _play(self, index):
        from txplayagui.client import play
        _ = play(position=index.row())

    @pyqtSlot(QPoint)
    def playlistContextMenu(self, position):
        index = self.playlistTable.indexAt(position)
        isPlaylistEmpty = (self.playlistModel.rowCount() == 0)

        menu = PlaylistMenu(index, isPlaylistEmpty,
                            self.playlistModel.hasUndo, self.playlistModel.hasRedo)
        menu.play.connect(self.onPlaylistMenuPlay)
        menu.remove.connect(self.onPlaylistMenuRemove)
        menu.clear.connect(self.onPlaylistMenuClear)
        menu.reconnect.connect(self.reconnectDialog)
        menu.save.connect(self.onPlaylistSave)
        menu.undo.connect(self.onPlaylistUndo)
        menu.redo.connect(self.onPlaylistRedo)

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
    def onPlaylistUndo(self):
        from txplayagui.client import playlistUndo
        _ = playlistUndo()

    @pyqtSlot()
    def onPlaylistRedo(self):
        from txplayagui.client import playlistRedo
        _ = playlistRedo()

    @pyqtSlot()
    def onPlaySelected(self):
        selectedIdx = self.playlistTable.selectedIndexes()
        if len(selectedIdx) == 0:
            return

        self._play(selectedIdx[0])

    @pyqtSlot()
    def onPauseClicked(self):
        from txplayagui.client import pause
        _ = pause()

    @pyqtSlot()
    def onStopClicked(self):
        from txplayagui.client import stop
        _ = stop()

    @pyqtSlot()
    def onNextClicked(self):
        from txplayagui.client import next_
        _ = next_()

    @pyqtSlot()
    def onPrevClicked(self):
        from txplayagui.client import prev
        _ = prev()

    def dockShow(self, state):
        self.libraryDock.hide()
        self.toggleLibraryButton.setChecked(False)
        self.playlistsDock.hide()
        self.togglePlaylistsButton.setChecked(False)

        if state == 1:
            self.libraryDock.show()
            self.toggleLibraryButton.setChecked(True)

        elif state == 2:
            self.playlistsDock.show()
            self.togglePlaylistsButton.setChecked(True)

        self.dockState = state

    @pyqtSlot(bool)
    def onToggleLibrary(self, show):
        self.dockShow(1 if show else 0)

    @pyqtSlot(bool)
    def onTogglePlaylists(self, show):
        self.dockShow(2 if show else 0)

    @pyqtSlot(object)
    def onTrackStarted(self, trackData):
        trackname = trackData['track']['trackname']
        self.trackProgressBar.setFormat(trackname)

        position = trackData['position']
        self.playlistModel.setPlayingPosition(position)

        self.playButton.hide()
        self.pauseButton.show()
        self.pauseButton.setChecked(False)
        self.stopButton.show()

    @pyqtSlot()
    def onPlaybackFinished(self):
        self.trackProgressBar.setFormat('not playing')
        self.trackProgressBar.setValue(0)
        self.playlistModel.setPlayingPosition(None)

        self.playButton.show()
        self.pauseButton.hide()
        self.stopButton.hide()

    @pyqtSlot(bool)
    def onPlaybackPaused(self, paused):
        self.playButton.hide()
        self.pauseButton.show()
        self.stopButton.show()

        self.pauseButton.setChecked(paused)

    @pyqtSlot(object)
    def onPlaylistChanged(self, data):
        self.playlistModel.hasUndo = data['hasUndo']
        self.playlistModel.hasRedo = data['hasRedo']
        self.playlistModel.updateAll(data['playlist'])
        self.playlistLengthLabel.setText(self.playlistModel.fullLength())

    @pyqtSlot(list)
    def onLibraryItemActivated(self, hashes):
        from txplayagui.client import libraryInsert
        _ = libraryInsert(hashes)

    @pyqtSlot(list)
    def playlistRegistryUpdated(self, list_):
        self.playlists.update(list_)

    @pyqtSlot(unicode)
    def onPlaylistLoad(self, playlistName):
        from txplayagui.client import loadPlaylist
        _ = loadPlaylist(playlistName)

    @pyqtSlot(unicode)
    def onPlaylistSave(self, playlistName):
        from txplayagui.client import savePlaylist
        _ = savePlaylist(playlistName)

    @pyqtSlot()
    def reconnectDialog(self):
        reconnected = ReconnectDialog().exec_()
        if reconnected:
            self.infoStream.deleteLater()
            self.infoStreamStart()
        else:
            self.quitEvent()

    @pyqtSlot(int)
    def timerUpdated(self, progress):
        self.trackProgressBar.setValue(progress)

    def keyReleaseEvent(self, event):
        from txplayagui.client import remove, deletePlaylist

        result = QMainWindow.keyReleaseEvent(self, event)
        focusWidget = QApplication.focusWidget()

        if event.modifiers() == Qt.ControlModifier and event.key() == 70:
            # Ctrl + F, focus searh in library
            self.library.querySearchBox.setFocus()
            self.library.querySearchBox.selectAll()

        elif event.modifiers() == Qt.NoModifier and event.key() == 32:
            # Space, toggle playback
            if focusWidget != self.library.querySearchBox:
                if self.pauseButton.isVisible():
                    self.onPauseClicked()
                else:
                    self.onPlaySelected()

        elif event.modifiers() == Qt.NoModifier and event.key() == 16777223:
            # Del key

            if focusWidget == self.playlistTable:
                # delete item in playlist
                selectedIndexes = self.playlistTable.selectedIndexes()
                if len(selectedIndexes) > 0:
                    _ = remove(selectedIndexes[0].row())

            elif focusWidget == self.playlists.view:
                # delete playlist from registry
                selectedIndexes = self.playlists.view.selectedIndexes()
                if len(selectedIndexes) > 0:
                    playlistName = selectedIndexes[0].data()
                    _ = deletePlaylist(playlistName)

        return result

    def systemTrayToggle(self, reason):
        if self.isVisible():
            self.hide()
        else:
            self.restoreWindow()

    def restoreWindow(self):
        self.show()
        self.setWindowState(Qt.WindowNoState)
        self.setFocus()

    def closeEvent(self, event):
        if not self.quitFlag:
            self.hide()
            event.ignore()
        QMainWindow.closeEvent(self, event)

    @pyqtSlot(bool)
    def quitEvent(self, checked=None):
        self.settings.setValue(u'geometry/main', self.geometry())

        for col in range(self.playlistModel.columnCount()):
            self.settings.setValue(u'geometry/playlist/col/%d' % col,
                                   self.playlistTable.columnWidth(col))

        self.settings.setValue(u'geometry/dock/state', self.dockState)
        self.systemTray.deleteLater()

        self.quitFlag = True
        self.close()
