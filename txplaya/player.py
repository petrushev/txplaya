from decimal import Decimal
from collections import deque
from math import ceil
import gc
from uuid import uuid4
from operator import itemgetter
import json

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.python import log

from txplaya.library import Library

ITER_TIME = 1.0
HISTORY_CHUNKS = 1


itemgetter0 = itemgetter(0)

def logErr(failure):
    failure.printTraceback()


class TxPlayaError(Exception): pass
class PlaylistError(TxPlayaError): pass
class PlaylistFinished(PlaylistError): pass


class ListenerRegistry(object):

    def __init__(self):
        self._reg = {}

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
        _d = deferLater(reactor, 1000, self._garbageCollect)
        bytes_ = gc.collect()
        log.msg('Garbage collected %d' % bytes_)

    def feed(self, track):
        rawData = track.data

        num_chunks = track.length * 1.0 / ITER_TIME
        chunk_size = int(ceil(len(rawData) / num_chunks))

        self.data.clear()
        self.timer = 0

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

        # update timer
        self.timer = self.timer + ITER_TIME
        self.onTimerUpdate()

    def start(self):
        if len(self.data) == 0:
            return

        self.onStart()

        if self.playing and not self.paused:
            return

        self.playing = True
        self.paused = False
        self.play()

    def stop(self):
        self.data = deque()
        self.history = deque()
        self.playing = False
        self.paused = False

        self.onStop()

    def pause(self):
        self.paused = True
        self.onPaused(True)

    def resume(self):
        self.paused = False
        self.play()
        self.onPaused(False)

    def onPush(self, buf):
        log.err('Player not attached')

    def onStart(self):
        log.err('Player not attached')

    def onTrackFinished(self):
        log.err('Player not attached')

    def onStop(self):
        log.err('Player not attached')

    def onTimerUpdate(self):
        log.err('Player not attached')

    def onPaused(self):
        log.err('Player not attached')


class Playlist(object):

    _reg = {}
    _order = {}
    _currentUid = None

    def iterTrack(self):
        keys = sorted(self._order.keys())
        for dposition in keys:
            trackUid = self._order[dposition]
            yield self._reg[trackUid]

    def insert(self, track, position=None, trackUid=None, emit=True):

        if self._reg == {}:
            dposition = Decimal(1)

        elif position is None or position >= len(self._order):
            dposition = max(self._order.keys()) + 1

        elif position == 0:
            dposition = min(self._order.keys()) / 2

        else: # 0 < position < len_reg
            keys = sorted(self._order.keys())
            dposition = (keys[position - 1] + keys[position]) / 2

        if trackUid is None:
            # track does not exist in the playlist yet
            trackUid = uuid4()

        self._reg[trackUid] = track

        self._order[dposition] = trackUid

        if emit:
            self.onChanged()

    def remove(self, position, emit=True):
        keys = sorted(self._order.keys())
        dposition = keys[position]
        trackUid = self._order[dposition]

        del self._order[dposition]
        del self._reg[trackUid]

        if trackUid == self._currentUid:
            self._currentUid = None

        if emit:
            self.onChanged()

    def move(self, origin, target):
        if origin == target or origin + 1 == target:
            return

        keys = sorted(self._order.keys())
        dposition = keys[origin]
        trackUid = self._order[dposition]
        track = self._reg[trackUid]

        self.remove(origin, emit=False)

        if origin > target:
            self.insert(track, target, trackUid, emit=False)
        else:
            self.insert(track, target - 1, trackUid, emit=False)

        self.onChanged()

    def clear(self):
        self._order.clear()
        self._reg.clear()
        self._currentUid = None
        self.onChanged()

    @property
    def currentPosition(self):
        if self._currentUid is None:
            return None

        keys = sorted(self._order.items(), key=itemgetter0)

        for position, (_, trackUid) in enumerate(keys):
            if trackUid == self._currentUid:
                return position

        raise PlaylistError, 'current uid not in _reg'

    @property
    def currentTrack(self):
        if self._currentUid is None:
            return None
        return self._reg[self._currentUid]

    def start(self, position=None):
        if self._reg == {}:
            raise PlaylistError, 'Empty playlist'

        if position >= len(self._reg) or position < 0:
            raise PlaylistError, 'Position out of bounds'

        if position is None:
            position = 0

        keys = sorted(self._order.keys())
        dposition = keys[position]
        trackUid = self._order[dposition]
        self._currentUid = trackUid

    def stop(self):
        self._currentUid = None

    def stepNext(self):
        position = self.currentPosition
        if position is None:
            log.err('Auto play next without playing.')
            log.err('The current song playing was probably removed')
            return None

        nextPosition = position + 1
        if nextPosition >= len(self._reg):
            self._currentUid = None
            return None

        self.start(nextPosition)

        return nextPosition

    def onChanged(self):
        log.err('Playlist not attached')


class MainController(object):

    def __init__(self):
        self.player = Player()
        self.playlist = Playlist()
        self.listenerRegistry = ListenerRegistry()
        self.infoListenerRegistry = ListenerRegistry()
        self.library = Library()

        self.player.onPush = self.onBufferReceived
        self.player.onStart = self.onPlaybackStarted
        self.player.onTrackFinished = self.onTrackFinished
        self.player.onStop = self.onPlayerStopped
        self.player.onTimerUpdate = self.onTimerUpdate
        self.player.onPaused = self.onPlayerPaused
        self.playlist.onChanged = self.onPlaylistChange

    def announce(self, data):
        buf = json.dumps(data) + '\n'
        for listener in self.infoListenerRegistry.iterListeners():
            _d = deferLater(reactor, 0, listener.onPush, buf)

    def onTrackFinished(self):
        nextPosition = self.playlist.stepNext()

        if nextPosition is None:
            self.onPlaylistFinished()
            return

        event = {'event': 'TrackStarted',
                 'data': {'position': self.playlist.currentPosition,
                          'track': self.playlist.currentTrack.meta}}
        self.announce(event)

        self.player.feed(self.playlist.currentTrack)
        self.player.start()

    def onPlaybackStarted(self):
        event = {'event': 'TrackStarted',
                 'data': {'position': self.playlist.currentPosition,
                          'track': self.playlist.currentTrack.meta}}
        self.announce(event)

    def onPlayerStopped(self):
        event = {'event': 'PlaybackFinished',
                 'data': {}}
        self.announce(event)

    def onPlayerPaused(self, paused):
        event = {'event': 'PlaybackPaused',
                 'data': {'paused': paused}}
        self.announce(event)

    def onPlaylistFinished(self):
        log.msg('Playlist finished')

        event = {'event': 'PlaybackFinished',
                 'data': {}}
        self.announce(event)

        self.player.history = deque()
        self.listenerRegistry.onPlaylistFinished()

    def onBufferReceived(self, buf):
        # deliver buffer to all listeners
        for listener in self.listenerRegistry.iterListeners():
            _d = deferLater(reactor, 0, listener.onPush, buf)

    def onPlaylistChange(self):
        playlistData = [track.meta
                        for track in self.playlist.iterTrack()]
        event = {'event': 'PlaylistChanged',
                 'data': {'playlist': playlistData}}

        self.announce(event)

    def onTimerUpdate(self):
        event = {'event': 'TimerUpdate',
                 'data': {'time': self.player.timer}}
        self.announce(event)
