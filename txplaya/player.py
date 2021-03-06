from decimal import Decimal
from collections import deque
import gc
from uuid import uuid4
from operator import itemgetter
import json

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.python import log

from txplaya.library import Library
from txplaya.lastfm import getScrobbler
from txplaya.track import Track

ITER_TIME = 0.2
HISTORY_CHUNKS = 4


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
    currentSize = 0

    def __init__(self):
        self._garbageCollect()

    def _garbageCollect(self):
        _bytes = gc.collect()
        if _bytes == 0:
            interval = 3000
        else:
            interval = 1000
        _d = deferLater(reactor, interval, self._garbageCollect)

        #log.msg('Garbage collected %d' % bytes_)

    def feed(self, track, clear=False):
        if clear:
            self.data.clear()

        try:
            chunks = track.dataChunks(ITER_TIME)
        except IOError:
            log.err('{0} can not be read'.format(repr(track)))
            #self.onTrackFinished()
            raise
        else:
            self.currentSize = sum(map(len, chunks))
            self.data.extend(chunks)

    def play(self):
        if not self.playing or self.paused:
            return

        if len(self.data) == 0:
            self.playing = False
            self.currentSize = 0
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

        self._timerUpdate()

    def _timerUpdate(self):
        if self.currentSize == 0:
            self.onTimerUpdate(0)
            return

        remainingSize = sum(map(len, self.data))
        progressPercent = int((self.currentSize - remainingSize ) * 100.0 / self.currentSize)

        # update timer
        self.onTimerUpdate(progressPercent)

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

    _undos = deque()
    _redos = deque()

    def iterTrackUid(self):
        keys = sorted(self._order.keys())
        for dposition in keys:
            trackUid = self._order[dposition]
            yield trackUid

    def iterTrack(self):
        for trackUid in self.iterTrackUid():
            yield self._reg[trackUid]

    @property
    def playlistData(self):
        data = (track.meta for track in self.iterTrack())
        data = [meta for meta in data if meta is not None]
        return data

    @property
    def _paths(self):
        return [track._path for track in self.iterTrack()]

    def insert(self, track, position=None, emit=True):
        if self._reg == {}:
            dposition = Decimal(1)

        elif position is None or position >= len(self._order):
            dposition = max(self._order.keys()) + 1

        elif position == 0:
            dposition = min(self._order.keys()) / 2

        else: # 0 < position < len_reg
            keys = sorted(self._order.keys())
            dposition = (keys[position - 1] + keys[position]) / 2

        trackUid = uuid4()
        self._reg[trackUid] = track
        self._order[dposition] = trackUid

        if emit:
            self.onChanged()

    def mark(self):
        self._undos.append((dict(self._reg), dict(self._order)))
        self._redos.clear()

    def undo(self):
        if not self.hasUndo:
            return

        self._redos.appendleft((dict(self._reg), dict(self._order)))
        self._reg, self._order = self._undos.pop()

        if self._currentUid not in self._reg:
            self._currentUid = None

        self.onChanged()

    def redo(self):
        if not self.hasRedo:
            return

        self._undos.append((dict(self._reg), dict(self._order)))
        self._reg, self._order = self._redos.popleft()

        if self._currentUid not in self._reg:
            self._currentUid = None

        self.onChanged()

    @property
    def hasUndo(self):
        return len(self._undos) > 0
    @property
    def hasRedo(self):
        return len(self._redos) > 0

    def remove(self, position, emit=True):
        keys = sorted(self._order.keys())
        dposition = keys[position]
        trackUid = self._order[dposition]

        self.mark()

        del self._order[dposition]
        del self._reg[trackUid]

        if trackUid == self._currentUid:
            self._currentUid = None

        if emit:
            self.onChanged()

    def move(self, origin, target, emit=True):
        if origin == target or origin + 1 == target:
            return

        keys = sorted(self._order.keys())
        dpositionOrigin = keys[origin]
        trackUid = self._order[dpositionOrigin]

        if target == 0:
            dpositionTarget = keys[0] / 2
        elif target >= len(self._order):
            dpositionTarget = max(self._order.keys()) + 1
        else:
            dpositionTarget = (keys[target] + keys[target - 1]) / 2

        self.mark()

        del self._order[dpositionOrigin]
        self._order[dpositionTarget] = trackUid

        if emit:
            self.onChanged()

    def clear(self):
        self.mark()

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

    def save(self, name, trackPaths=None):
        from txplaya.playlistregistry import playlistRegistry
        if trackPaths is None:
            trackPaths = [track._path for track in self.iterTrack()]
        playlistRegistry.savePlaylist(name, trackPaths)

    def load(self, name):
        from txplaya.playlistregistry import playlistRegistry
        return playlistRegistry.loadPlaylist(name)


class MainController(object):

    def __init__(self):
        self.player = Player()
        self.playlist = Playlist()
        self.listenerRegistry = ListenerRegistry()
        self.infoListenerRegistry = ListenerRegistry()
        self.library = Library()

        self.scrobbler = getScrobbler()

        self.player.onPush = self.onBufferReceived
        self.player.onStart = self.onPlaybackStarted
        self.player.onTrackFinished = self.onTrackFinished
        self.player.onStop = self.onPlayerStopped
        self.player.onTimerUpdate = self.onTimerUpdate
        self.player.onPaused = self.onPlayerPaused
        self.playlist.onChanged = self.onPlaylistChange

    def onStart(self):
        from txplaya.playlistregistry import playlistRegistry

        filepaths = playlistRegistry.loadPlaylist('__current__')

        for filepath in filepaths:
            if not self.library.pathExists(filepath):
                continue
            track = Track(filepath)
            self.playlist.insert(track)

    def onStop(self):
        from txplaya.playlistregistry import playlistRegistry

        paths = [track._path for track in self.playlist.iterTrack()]
        playlistRegistry.savePlaylist('__current__', paths)

    def announce(self, data):
        buf = (json.dumps(data) + '\n').encode('utf-8')
        for listener in self.infoListenerRegistry.iterListeners():
            deferLater(reactor, 0, listener.onPush, buf)

    def onTrackFinished(self):
        if self.scrobbler is not None:
            deferLater(reactor, 0, self.scrobbler.scrobble, self.playlist.currentTrack)

        if self.playlist.stepNext() is None:
            self.onPlaylistFinished()
            return

        while True:
            try:
                self.player.feed(self.playlist.currentTrack, clear=False)
            except IOError:
                # next track not found on disk
                currentPosition = self.playlist.currentPosition
                self.playlist.remove(currentPosition, emit=False)

                if currentPosition >= len(self.playlist._reg):
                    # no more tracks
                    self.onPlaylistFinished()
                    break
                else:
                    # try next
                    self.playlist.start(currentPosition)
            else:
                # track loaded successfuly
                self.player.start()
                self.onPlaybackStarted()
                break

    def onPlaybackStarted(self):
        track = self.playlist.currentTrack

        if self.scrobbler is not None:
            deferLater(reactor, 0, self.scrobbler.updateNowPlaying, track)

        if track.meta is None:
            return

        event = {'event': 'TrackStarted',
                 'data': {'position': self.playlist.currentPosition,
                          'track': track.meta}}
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
        playlist = self.playlist
        event = {'event': 'PlaylistChanged',
                 'data': {'playlist': playlist.playlistData,
                          'hasUndo': playlist.hasUndo,
                          'hasRedo': playlist.hasRedo,
                          'position': playlist.currentPosition}}
        self.announce(event)

    def onTimerUpdate(self, percent):
        event = {'event': 'TimerUpdate',
                 'data': {'time': percent}}
        self.announce(event)
