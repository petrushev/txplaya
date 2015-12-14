from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, pyqtSignal

from txplayagui.utilities import mimeWrapJson, unwrapMime


class LibraryItem(object):

    def __init__(self, data):
        self._children = {}
        self._data = data
        self._parent = None

    def row(self):
        sorted_ = sorted(self.parentItem()._children.keys())
        return sorted_.index(self._data)

    def childAt(self, row):
        sorted_ = sorted(self._children.keys())
        key = sorted_[row]
        return self._children[key]

    def parentItem(self):
        return self._parent


class ArtistItem(LibraryItem):

    def row(self):
        sorted_ = sorted(self.model._artists.keys())
        return sorted_.index(self._data)

    def data(self):
        return self._data

    def mimeData(self):
        return mimeWrapJson({'albumartist': self._data})


class AlbumItem(LibraryItem):

    def data(self):
        year, album = self._data
        if year:
            return '(%d) %s' % (year, album)

        return album

    def mimeData(self):
        year, album = self._data
        res = unwrapMime(self._parent.mimeData())
        res.update({'album': album,
                    'year': year})
        return mimeWrapJson(res)

    def albumHashes(self):
        sorted_ = sorted(self._children.keys())
        return [self._children[key].hash for key in sorted_]


class TrackItem(LibraryItem):

    def _parseData(self):
        if len(self._data) == 4:
            disc_number, tracknumber, trackname, artist = self._data
        else:
            disc_number, tracknumber, trackname = self._data
            artist = ''

        return disc_number, tracknumber, trackname, artist

    def data(self):
        disc_number, tracknumber, trackname, artist = self._parseData()
        display = ''
        if disc_number:
            display = '#%d - ' % disc_number
        if tracknumber:
            display = display + '%d. ' % tracknumber

        display = display + trackname
        if artist != '':
            display = display + ' - %s' % artist

        return display

    def mimeData(self):
        disc_number, tracknumber, trackname, artist = self._parseData()

        res = unwrapMime(self._parent.mimeData())
        res.update({'trackname': trackname,
                    'discnumber': disc_number,
                    'tracknumber': tracknumber,
                    'artist': artist,
                    'length': self.length,
                    'hash': self.hash})
        return mimeWrapJson(res)

    def match(self, query):
        meta = unwrapMime(self.mimeData())
        qText = ' '.join([meta['artist'], meta['album'], meta['albumartist'], meta['trackname']])
        return query in qText.lower()


class LibraryModel(QAbstractItemModel):

    toggleRow = pyqtSignal(int, QModelIndex, bool)

    def __init__(self, *args, **kwargs):
        QAbstractItemModel.__init__(self, *args, **kwargs)
        self._rootIndex = QModelIndex()
        self._artists = {}

    def columnCount(self, parent=QModelIndex()):
        return 1

    def rowCount(self, parent=QModelIndex()):
        parentItem = parent.internalPointer()
        if parentItem is None:
            return len(self._artists)

        return len(parentItem._children)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            item = index.internalPointer()
            return item.data()

        return None

    def mimeData(self, indexes):
        mimeDatas = (index.internalPointer().mimeData() for index in indexes)
        mimeDataUnwrapped = [unwrapMime(mimeData) for mimeData in mimeDatas]
        return mimeWrapJson(mimeDataUnwrapped)

    def flags(self, index):
        item = index.internalPointer()
        if isinstance(item, TrackItem):
            return Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled
        else:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def parent(self, index):
        item = index.internalPointer()

        parentItem = item.parentItem()

        if parentItem is None:
            return self._rootIndex

        return self.createIndex(parentItem.row(), 0, parentItem)

    def index(self, row, column, parent):
        if not parent.isValid():
            sorted_artists = sorted(self._artists.keys())
            key = sorted_artists[row]
            item = self._artists[key]
        else:
            parentItem = parent.internalPointer()
            item = parentItem.childAt(row)

        return self.createIndex(row, column, item)

    def loadData(self, libraryData):
        self.beginResetModel()

        self._artists.clear()

        # fill new
        for hash_, meta in libraryData.items():

            albumartist = meta['albumartist']
            album = (meta['year'], meta['album'])
            track = (meta['discnumber'], meta['tracknumber'], meta['trackname'])

            if albumartist != meta['artist']:
                track = track + (meta['artist'],)

            if albumartist in self._artists:
                artistItem = self._artists[albumartist]
            else:
                artistItem = ArtistItem(albumartist)
                artistItem.model = self
                self._artists[albumartist] = artistItem

            if album in artistItem._children:
                albumItem = artistItem._children[album]
            else:
                albumItem = AlbumItem(album)
                albumItem._parent = artistItem
                artistItem._children[album] = albumItem

            if track not in albumItem._children:
                trackItem = TrackItem(track)
                trackItem.hash = hash_
                trackItem.length = meta['length']
                trackItem._parent = albumItem
                albumItem._children[track] = trackItem

        self.endResetModel()

    def albumHashes(self, index):
        item = index.internalPointer()
        if not isinstance(item, AlbumItem):
            raise TypeError, 'Suplied index does not point to AlbumItem'

        return item.albumHashes()

    def filter(self, query):
        filtered = ((artistKey, albumKey, albumItem, trackItem.row(), trackItem.match(query))
                    for artistKey, artistItem in self._artists.items()
                    for albumKey, albumItem in artistItem._children.items()
                    for trackItem in albumItem._children.values())

        shownArtistKeys, shownAlbumKeys = set(), set()

        for artistKey, albumKey, albumItem, trackRow, isMatch in filtered:
            parentIndex = self.createIndex(albumItem.row(), 0, albumItem)
            self.toggleRow.emit(trackRow, parentIndex, isMatch)

            if isMatch:
                shownArtistKeys.add(artistKey)
                shownAlbumKeys.add(albumKey)
        del parentIndex

        for artistKey, artistItem in self._artists.items():
            if artistKey not in shownArtistKeys:
                # hide artist row
                self.toggleRow.emit(artistItem.row(), self._rootIndex, False)

            else:
                # show artist, filter albums
                self.toggleRow.emit(artistItem.row(), self._rootIndex, True)
                for albumKey, albumItem in artistItem._children.items():
                    parentIndex = self.createIndex(artistItem.row(), 0, artistItem)

                    if albumKey in shownAlbumKeys:
                        self.toggleRow.emit(albumItem.row(), parentIndex, True)
                    else:
                        self.toggleRow.emit(albumItem.row(), parentIndex, False)
