import json

from PyQt5.QtCore import pyqtSlot, pyqtSignal, QModelIndex, Qt
from PyQt5.QtWidgets import QWidget, QSpacerItem, QSizePolicy, QShortcut
from PyQt5.QtGui import QKeySequence

from txplayagui.ui.library import Ui_LibraryWidget
from txplayagui.library import LibraryModel
from txplayagui.utilities import unwrapMime


class LibraryWidget(Ui_LibraryWidget, QWidget):

    rescanStarted = pyqtSignal()
    itemsActivated = pyqtSignal(list)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        Ui_LibraryWidget.setupUi(self, self)

        self.rescanButton.show()
        self.scanProgressBar.hide()

        self.libraryModel = LibraryModel()
        self.treeView.setModel(self.libraryModel)

        self.libraryModel.toggleRow.connect(self.onToggleRow)
        self.rescanButton.clicked.connect(self.rescanClicked)
        self.treeView.doubleClicked.connect(self.onTreeViewDoubleClicked)

        self.querySearchBox.textChanged.connect(self.onQueryChanged)
        self.clearSearchButton.clicked.connect(self.onQueryClear)

        # shortcuts
        releaseSearchboxShortcut = QShortcut(QKeySequence('Esc'), self.querySearchBox)
        releaseSearchboxShortcut.setContext(Qt.WidgetShortcut)
        releaseSearchboxShortcut.activated.connect(self.onReleaseSearchbox)
        scrollLibraryShortcut = QShortcut(QKeySequence(Qt.Key_Down), self.querySearchBox)
        scrollLibraryShortcut.setContext(Qt.WidgetShortcut)
        scrollLibraryShortcut.activated.connect(self.onScrollLibrary)
        activateTracksShortcut = QShortcut(QKeySequence(Qt.Key_Return), self.treeView)
        activateTracksShortcut.setContext(Qt.WidgetShortcut)
        activateTracksShortcut.activated.connect(self.onActivateTracks)

    @pyqtSlot()
    def rescanClicked(self):
        from txplayagui.client import rescanLibrary

        self.rescanButton.hide()
        self.scanControlsLayout.removeItem(self.scanControlsLayout.itemAt(2))
        self.scanProgressBar.show()

        self.scanResponse = rescanLibrary()
        self.scanResponse.lineReceived.connect(self.scanProgress)

        self.rescanStarted.emit()

    @pyqtSlot(str)
    def scanProgress(self, progress):
        data = json.loads(progress.rstrip())
        if 'scanprogress' in data:
            progress = data['scanprogress']
            self.setProgress(progress)
        else:
            self.scanResponse.close()
            self.scanResponse.deleteLater()

            self.rescanFinished(data['library'])

    @pyqtSlot(int, QModelIndex, bool)
    def onToggleRow(self, row, parentIndex, isShown):
        self.treeView.setRowHidden(row, parentIndex, not isShown)

    @pyqtSlot(QModelIndex)
    def onTreeViewDoubleClicked(self, index):
        hashes = self._getHashes(index)
        if len(hashes) == 0:
            return

        self.itemsActivated.emit(hashes)

    @pyqtSlot(unicode)
    def onQueryChanged(self, query):
        if len(query) > 2:
            self.libraryModel.filter(query)
        elif query == '':
            return self.libraryModel.showAll()

    @pyqtSlot()
    def onQueryClear(self):
        self.querySearchBox.setText('')
        self.querySearchBox.setFocus()

    def onReleaseSearchbox(self):
        self.setFocus()

    def onScrollLibrary(self):
        self.treeView.setCurrentIndex(self.libraryModel.headIndex())
        self.treeView.setFocus()

    def onActivateTracks(self):
        collectedHashes = []

        for index in self.treeView.selectedIndexes():
            for hash_ in self._getHashes(index):
                if hash_ not in collectedHashes:
                    collectedHashes.append(hash_)

        if len(collectedHashes) == 0:
            return

        self.itemsActivated.emit(collectedHashes)

    def _getHashes(self, index):
        mimeData = unwrapMime(self.libraryModel.mimeData([index]))
        item = mimeData['items'][0]
        try:
            return [item['hash']]
        except KeyError:
            if 'album' in item:
                return self.libraryModel.albumHashes(index)
        return []

    def setProgress(self, value):
        self.scanProgressBar.setValue(value)

    def rescanFinished(self, data):
        self.libraryModel.loadData(data)

        self.rescanButton.show()
        spacerItem = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.scanControlsLayout.addItem(spacerItem)
        self.scanProgressBar.hide()
        self.scanProgressBar.setValue(0)

        # apply filter if active
        query = self.querySearchBox.text().lower()
        if len(query) > 2:
            self.libraryModel.filter(query)
