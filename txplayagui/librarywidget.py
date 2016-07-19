import json

from PyQt5.QtCore import pyqtSlot, pyqtSignal, QModelIndex
from PyQt5.QtWidgets import QWidget, QSpacerItem, QSizePolicy

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
        mimeData = unwrapMime(self.libraryModel.mimeData([index]))[0]
        if 'hash' in mimeData:
            hashes = [mimeData['hash']]

        elif 'album' in mimeData:
            hashes = self.libraryModel.albumHashes(index)
        else:
            # artist clicked
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
