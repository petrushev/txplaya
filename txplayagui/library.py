import gc

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, pyqtSignal

from txplayagui.utilities import mimeWrapJson


# TODO : split into separate widget
class SortedDict(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._orderedKeys = sorted(self.keys())

    def __setitem__(self, key, val):
        resort = (key not in self)
        dict.__setitem__(self, key, val)
        if resort:
            self._orderedKeys = sorted(self.keys())

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._orderedKeys.remove(key)

    def __getitem__(self, key):
        if isinstance(key, int):
            key = self._orderedKeys[key]
        return dict.__getitem__(self, key)

    def itemAt(self, index):
        key = self._orderedKeys[index]
        return (key, self[key])

    def index(self, key):
        return self._orderedKeys.index(key)

    def clear(self, *args, **kwargs):
        dict.clear(self, *args, **kwargs)
        self._orderedKeys[:] = []

    def popitem(self):
        key, val = dict.popitem(self)
        self._orderedKeys.remove(key)
        return key, val


class LibraryItem(object):

    def __init__(self, data):
        self._children = SortedDict()
        self._data = data
        self._parent = None

    def row(self):
        return self.parentItem()._children.index(self._data)

    def childAt(self, row):
        _key, child = self._children.itemAt(row)
        return child

    def parentItem(self):
        return self._parent

    def clear(self):
        self._parent = None
        while self._children:
            _, child = self._children.popitem()
            child.clear()


class ArtistItem(LibraryItem):

    def row(self):
        key = self._data
        if key.lower().startswith('the '):
            key = self._data[4:]
        return self.model._artists.index(key)

    def data(self):
        if self._data == '':
            return ' Various artists'
        return self._data

    def mimeDataDict(self):
        return {'albumartist': self._data}

    def clear(self):
        LibraryItem.clear(self)
        self.model = None


class AlbumItem(LibraryItem):

    def data(self):
        year, album = self._data
        if year:
            return '(%d) %s' % (year, album)
        return album

    def mimeDataDict(self):
        year, album = self._data
        res = self.artistItem().mimeDataDict()
        res.update({'album': album,
                    'year': year})
        return res

    def albumHashes(self):
        sorted_ = self._children._orderedKeys
        return [self._children[key].hash for key in sorted_]

    def artistItem(self):
        return self._parent

    def discCount(self):
        if not hasattr(self, '_discCount'):
            discPositions = set(trackItem._data[0]
                            for trackItem in self._children.itervalues())
            self._discCount = len(discPositions)

        return self._discCount


class TrackItem(LibraryItem):

    def data(self):
        disc_number, tracknumber, trackname, artist = self._data
        display = ''
        if disc_number and self.albumItem().discCount() > 1:
            display = '%d/' % disc_number
        if tracknumber:
            display = display + '%d. ' % tracknumber

        display = display + trackname
        if artist != '':
            display = display + ' - %s' % artist

        return display

    def mimeDataDict(self):
        disc_number, tracknumber, trackname, artist = self._data

        res = self.albumItem().mimeDataDict()
        res.update({'trackname': trackname,
                    'discnumber': disc_number,
                    'tracknumber': tracknumber,
                    'artist': artist,
                    'length': self.length,
                    'hash': self.hash})
        return res

    def match(self, query):
        if not hasattr(self, '_cacheQueryText'):
            meta = self.mimeDataDict()
            self._cacheQueryText = ' '.join([meta['artist'], meta['album'],
                                             meta['albumartist'], meta['trackname']]).lower()
        return query in self._cacheQueryText

    def albumItem(self):
        return self._parent


class LibraryModel(QAbstractItemModel):

    toggleRow = pyqtSignal(int, QModelIndex, bool)

    def __init__(self, *args, **kwargs):
        QAbstractItemModel.__init__(self, *args, **kwargs)
        self._rootIndex = QModelIndex()
        self._artists = SortedDict()

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
        mimeDataDicts = [index.internalPointer().mimeDataDict() for index in indexes]
        return mimeWrapJson(mimeDataDicts)

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
            _key,item = self._artists.itemAt(row)
        else:
            parentItem = parent.internalPointer()
            item = parentItem.childAt(row)

        return self.createIndex(row, column, item)

    def loadData(self, libraryData):
        self.beginResetModel()

        while self._artists:
            _, artistItem = self._artists.popitem()
            artistItem.clear()

        gc.collect()

        # fill new
        for hash_, meta in libraryData.iteritems():

            albumartist = meta['albumartist']
            album = (meta['year'], meta['album'])
            track = (meta['discnumber'], meta['tracknumber'], meta['trackname'])

            if albumartist != meta['artist']:
                track = track + (meta['artist'],)
            else:
                track = track + ('',)

            albumartistkey = albumartist
            if albumartistkey.lower().startswith('the '):
                albumartistkey = albumartist[4:]

            if albumartistkey in self._artists:
                artistItem = self._artists[albumartistkey]
            else:
                artistItem = ArtistItem(albumartist)
                artistItem.model = self
                self._artists[albumartistkey] = artistItem

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

        variousArtist = self._artists.get('')
        if variousArtist is not None:
            # recheck album artists
            for album, albumItem in variousArtist._children.items():
                albumArtists = set(trackItem._data[3]
                                   for track, trackItem in albumItem._children.iteritems())
                if '' in albumArtists:
                    albumArtists.remove('')

                if len(albumArtists) == 1:
                    newAlbumArtist = tuple(albumArtists)[0]
                    del variousArtist._children[album]

                    newAlbumArtistKey = newAlbumArtist
                    if newAlbumArtistKey.lower().startswith('the '):
                        newAlbumArtistKey = newAlbumArtistKey[4:]

                    if newAlbumArtistKey in self._artists:
                        artistItem = self._artists[newAlbumArtistKey]
                    else:
                        artistItem = ArtistItem(newAlbumArtist)
                        artistItem.model = self
                        self._artists[newAlbumArtistKey] = artistItem

                    artistItem._children[album] = albumItem
                    albumItem._parent = artistItem

        self.endResetModel()

    def albumHashes(self, index):
        item = index.internalPointer()
        if not isinstance(item, AlbumItem):
            raise TypeError, 'Suplied index does not point to AlbumItem'

        return item.albumHashes()

    def filter(self, query):
        filtered = ((artistKey, albumKey, albumItem, trackItem.row(), trackItem.match(query))
                    for artistKey, artistItem in self._artists.iteritems()
                    for albumKey, albumItem in artistItem._children.iteritems()
                    for trackItem in albumItem._children.itervalues())

        shownArtistKeys, shownAlbumKeys = set(), set()

        parentIndex = None

        for artistKey, albumKey, albumItem, trackRow, isMatch in filtered:
            parentIndex = self.createIndex(albumItem.row(), 0, albumItem)
            self.toggleRow.emit(trackRow, parentIndex, isMatch)

            if isMatch:
                shownArtistKeys.add(artistKey)
                shownAlbumKeys.add(albumKey)
        del parentIndex

        for artistKey, artistItem in self._artists.iteritems():
            if artistKey not in shownArtistKeys:
                # hide artist row
                self.toggleRow.emit(artistItem.row(), self._rootIndex, False)

            else:
                # show artist, filter albums
                self.toggleRow.emit(artistItem.row(), self._rootIndex, True)

                for albumKey, albumItem in artistItem._children.iteritems():
                    parentIndex = self.createIndex(artistItem.row(), 0, artistItem)

                    if albumKey in shownAlbumKeys:
                        self.toggleRow.emit(albumItem.row(), parentIndex, True)
                    else:
                        self.toggleRow.emit(albumItem.row(), parentIndex, False)

    def showAll(self):
        for artistItem in self._artists.itervalues():
            self.toggleRow.emit(artistItem.row(), self._rootIndex, True)
            artistIndex = self.createIndex(artistItem.row(), 0, artistItem)

            for albumItem in artistItem._children.itervalues():
                self.toggleRow.emit(albumItem.row(), artistIndex, True)
                albumIndex = self.createIndex(albumItem.row(), 0, albumItem)

                for trackItem in albumItem._children.itervalues():
                    self.toggleRow.emit(trackItem.row(), albumIndex, True)
