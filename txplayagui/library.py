import gc

from unidecode import unidecode
from werkzeug.utils import cached_property

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, pyqtSignal

from txplayagui.utilities import mimeWrapJson, SortedDict


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

    @cached_property
    def mimeDataDict(self):
        return {'albumartist': self._data}

    def clear(self):
        LibraryItem.clear(self)
        self.model = None

    def getAlbum(self, album):
        if album in self._children:
            albumItem = self._children[album]
        else:
            albumItem = AlbumItem(album)
            albumItem._parent = self
            self._children[album] = albumItem

        return albumItem

    def removeAlbum(self, album):
        albumItem = self._children[album]
        albumItem._parent = None
        del self._children[album]
        del albumItem

        if len(self._children) == 0:
            self.model.removeArtist(self._data)


class AlbumItem(LibraryItem):

    def data(self):
        year, album = self._data
        if year:
            return '(%d) %s' % (year, album)
        return album

    @cached_property
    def mimeDataDict(self):
        year, album = self._data
        res = dict(self.artistItem().mimeDataDict)
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

    def removeTrack(self, track):
        trackItem = self._children[track]
        trackItem._parent = None
        del self._children[track]
        del trackItem

        if len(self._children) == 0:
            albumkey = self._data
            self.artistItem().removeAlbum(albumkey)

class TrackItem(LibraryItem):

    def data(self):
        disc_number, tracknumber, trackname, artist = self._data
        display = ''
        if disc_number and self.albumItem().discCount() > 1:
            display = '%d/' % disc_number
        if tracknumber:
            display = display + '%d.' % tracknumber

        if display != '':
            display = display + ' ' + trackname
        else:
            display = trackname

        albumArtist = self.albumItem().mimeDataDict['albumartist']

        if artist != '' and artist != albumArtist:
            display = display + ' - %s' % artist

        return display

    @cached_property
    def mimeDataDict(self):
        disc_number, tracknumber, trackname, artist = self._data

        res = dict(self.albumItem().mimeDataDict)
        res.update({'trackname': trackname,
                    'discnumber': disc_number,
                    'tracknumber': tracknumber,
                    'artist': artist,
                    'length': self.length,
                    'hash': self.hash})
        return res

    @cached_property
    def _queryText(self):
        meta = self.mimeDataDict
        queryText = ' '.join([meta['artist'], meta['album'], meta['albumartist'],
                              meta['trackname'], str(meta['year'])])
        queryText = unidecode(queryText).lower()
        return queryText

    def match(self, query):
        return query in self._queryText

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
        mimeDataDicts = [index.internalPointer().mimeDataDict for index in indexes]
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

    def getArtist(self, artist):
        albumartistkey = artist
        if albumartistkey.lower().startswith('the '):
            albumartistkey = artist[4:]

        if albumartistkey in self._artists:
            artistItem = self._artists[albumartistkey]
        else:
            artistItem = ArtistItem(artist)
            artistItem.model = self
            self._artists[albumartistkey] = artistItem

        return albumartistkey, artistItem

    def removeArtist(self, artist):
        if artist.lower().startswith('the '):
            artist = artist[4:]

        artistItem = self._artists[artist]
        artistItem.model = None
        del self._artists[artist]
        del artistItem

    def loadData(self, libraryData):
        self.beginResetModel()

        # clear library tree
        while self._artists:
            _, artistItem = self._artists.popitem()
            artistItem.clear()
            del artistItem

        # fill new
        for hash_, meta in libraryData.iteritems():

            albumartist = meta['albumartist']
            artist = meta['artist']
            album = (meta['year'], meta['album'])
            track = (meta['discnumber'], meta['tracknumber'], meta['trackname'])

            if albumartist != artist:
                track = track + (artist,)
            else:
                track = track + ('',)

            _albumArtistKey, artistItem = self.getArtist(albumartist)

            albumItem = artistItem.getAlbum(album)

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

                if len(albumArtists) > 1:
                    # album has multiple artists
                    continue

                # album has one artist
                newAlbumArtist = tuple(albumArtists)[0]
                newAlbumItem = self.getArtist(newAlbumArtist)[1].getAlbum(album)

                for track, trackItem in albumItem._children.items():
                    newTrack = track[:-1] + ('',)

                    if newTrack not in newAlbumItem._children:
                        newTrackItem = TrackItem(newTrack)
                        newTrackItem.hash = trackItem.hash
                        newTrackItem.length = trackItem.length
                        newTrackItem._parent = newAlbumItem

                        newAlbumItem._children[newTrack] = newTrackItem

                    albumItem.removeTrack(track)

        # put one-track artists under various
        for artist, artistItem in self._artists.items():
            if artistItem == variousArtist or len(artistItem._children) > 1:
                continue
            album, albumItem = artistItem._children.items()[0]
            if len(albumItem._children) > 1:
                continue

            track, trackItem = albumItem._children.items()[0]
            newTrack = track[:-1] + (artist,)
            newAlbumItem = variousArtist.getAlbum(album)

            if newTrack not in newAlbumItem._children:
                newTrackItem = TrackItem(newTrack)
                newTrackItem.hash = trackItem.hash
                newTrackItem.length = trackItem.length
                newTrackItem._parent = newAlbumItem

                newAlbumItem._children[newTrack] = newTrackItem

            albumItem.removeTrack(track)

        gc.collect()

        self.endResetModel()

    def albumHashes(self, index):
        item = index.internalPointer()
        if not isinstance(item, AlbumItem):
            raise TypeError, 'Suplied index does not point to AlbumItem'

        return item.albumHashes()

    def filter(self, query):
        query = unidecode(query).lower()
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
