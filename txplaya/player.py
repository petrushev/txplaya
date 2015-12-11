from decimal import Decimal
from collections import deque
from math import ceil
import gc
from uuid import uuid4
from operator import itemgetter

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.python import log

from mutagen.id3 import ID3
from mutagen.mp3 import MP3

ITER_TIME = 1.0
HISTORY_CHUNKS = 3


itemgetter0 = itemgetter(0)

def logErr(failure):
    failure.printTraceback()


class TxPlayaError(Exception): pass
class PlaylistError(TxPlayaError): pass
class PlaylistFinished(PlaylistError): pass


class ListenerRegistry(object):

    _reg = {}

    def add(self, listener):
        self._reg[id(listener)] = listener

    def remove(self, listener):
        del self._reg[id(listener)]

    def onPlaylistFinished(self):
        log.msg('ListenerRegistry::onPlaylistFinished not implemented')

    def iterListeners(self):
        for listener in self._reg.itervalues():
            yield listener


class Player(object):

    playing = False
    paused = False
    data = deque()
    history = deque()

    def __init__(self):
        self._garbageCollect()

    def _garbageCollect(self):
        _d = deferLater(reactor, 180, self._garbageCollect)
        bytes_ = gc.collect()
        log.msg('Garbage collected %d' % bytes_)

    def feed(self, track):
        rawData = track.data

        num_chunks = track.length * 1.0 / ITER_TIME
        chunk_size = int(ceil(len(rawData) / num_chunks))

        self.data.clear()

        while len(rawData) > 0:
            chunk, rawData = rawData[:chunk_size], rawData[chunk_size:]
            self.data.append(chunk)

    def play(self):
        if not self.playing or self.paused:
            return

        if len(self.data) == 0:
            self.playing = False
            self.onTrackFinished()
            return

        buf = self.data.popleft()

        self.history.append(buf)
        while len(self.history) > HISTORY_CHUNKS:
            _ = self.history.popleft()

        _d = deferLater(reactor, ITER_TIME, self.play)
        _d.addErrback(logErr)

        # push buffer to management
        self.onPush(buf)

    def start(self):
        if len(self.data) == 0:
            return

        self.playing = True
        self.paused = False
        self.play()

    def stop(self):
        self.data = deque()
        self.history = deque()
        self.playing = False
        self.paused = False

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
        self.play()

    def onPush(self, buf):
        log.err('Player not attached')

    def onTrackFinished(self):
        log.err('Player not attached')


class Track(object):

    def __init__(self, path):
        self._path = path

    @property
    def data(self):
        with open(self._path, 'rb') as f:
            data = f.read()
        return data

    @property
    def length(self):
        return MP3(self._path).info.length

    @property
    def meta(self):
        id3 = ID3(self._path)
        return {'album': id3.get('TALB').text[0],
                'artist': id3.get('TPE1').text[0],
                'trackname': id3.get('TIT2').text[0],
                'length': self.length}


class Playlist(object):

    _reg = {}
    _order = {}
    _current_uid = None

    def iterTrack(self):
        keys = sorted(self._order.keys())
        for dposition in keys:
            track_uid = self._order[dposition]
            yield self._reg[track_uid]

    def insert(self, track, position=None, track_uid=None):
        if track_uid is None:
            # track does not exist in the playlist yet
            track_uid = uuid4()

        if self._reg == {}:
            dposition = Decimal(1)

        elif position is None or position >= len(self._reg):
            dposition = max(self._order.keys()) + 1

        elif position == 0:
            dposition = min(self._order.keys()) / 2

        else: # 0 < position < len_reg
            keys = sorted(self._order.keys())
            dposition = (keys[position - 1] + keys[position]) / 2

        self._reg[track_uid] = track
        self._order[dposition] = track_uid

    def remove(self, position):
        keys = sorted(self._order.keys())
        dposition = keys[position]
        track_uid = self._order[dposition]

        del self._order[dposition]
        del self._reg[track_uid]
        self._current_uid = None

    def move(self, origin, target):
        if origin == target or origin + 1 == target:
            return

        keys = sorted(self._order.keys())
        dposition = keys[origin]
        track_uid = self._order[dposition]
        track = self._reg[track_uid]

        self.remove(origin)

        if origin > target:
            self.insert(track, target, track_uid)
        else:
            self.insert(track, target - 1, track_uid)

        self._current_uid = track_uid

    def clear(self):
        self._reg.clear()

    @property
    def currentPosition(self):
        if self._current_uid is None:
            return None

        keys = sorted(self._order.items(), key=itemgetter0)
        positions = dict((track_uid, position)
                         for position, (_, track_uid) in enumerate(keys))
        return positions[self._current_uid]

    @property
    def currentTrack(self):
        if self._current_uid is None:
            return None
        return self._reg[self._current_uid]

    def start(self, position=None):
        if self._reg == {}:
            raise PlaylistError, 'Empty playlist'

        if position >= len(self._reg):
            raise PlaylistError, 'Position out of bounds'

        if position is None:
            position = 0

        keys = sorted(self._order.keys())
        dposition = keys[position]
        track_uid = self._order[dposition]
        self._current_uid = track_uid

    def stop(self):
        self._current_uid = None

    def stepNext(self):
        position = self.currentPosition
        if position is None:
            log.err('Auto play next without playing.')
            log.err('The current song playing was probably removed')
            return None

        nextPosition = position + 1
        if nextPosition >= len(self._reg):
            return None

        self.start(nextPosition)

        return nextPosition


class MainController(object):

    def __init__(self):
        self.player = Player()
        self.playlist = Playlist()
        self.listenerRegistry = ListenerRegistry()

        self.player.onPush = self.onBufferReceived
        self.player.onTrackFinished = self.onTrackFinished

    def onTrackFinished(self):
        nextPosition = self.playlist.stepNext()

        if nextPosition is None:
            self.onPlaylistFinished()
            return

        self.player.feed(self.playlist.currentTrack)
        self.player.start()

    def onPlaylistFinished(self):
        log.msg('Playlist finished')
        self.player.history = deque()
        self.listenerRegistry.onPlaylistFinished()

    def onBufferReceived(self, buf):
        # deliver buffer to all listeners
        for listener in self.listenerRegistry.iterListeners():
            _d = deferLater(reactor, 0, listener.onPush, buf)
