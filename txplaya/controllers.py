import json
from time import time

from twisted.web import http
from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.python import log

from werkzeug.urls import url_unquote

from txplaya.track import Track
from txplaya.player import PlaylistError

import txplaya.library


class BaseController(object):

    def __init__(self, request):
        self.mainController = request.mainController
        self.request = request
        self.request.setHeader('Content-Type', 'text/html')
        self.wait = False

    def write(self, data):
        self.request.write(data)

    def finish(self):
        self.request.finish()


class BaseStream(BaseController):

    def __init__(self, request):
        BaseController.__init__(self, request)

        self.request.connectionLost = self.onConnectionLost

    def onPush(self, buf):
        self.write(buf)


class PlaylistManager(BaseController):

    def __init__(self, request, action, filepath='', position=None, start=None, end=None,
                 trackIds=''):
        BaseController.__init__(self, request)

        self.positionArg = position
        self.filepathArg = filepath
        self.startArg = start
        self.endArg = end
        self.trackIdsArg = trackIds

        self.request.setResponseCode(http.OK)

        action = getattr(self, action)
        response = action()

        self.request.setHeader('Content-Type', 'application/json')
        self.write(json.dumps(response))
        self.finish()

    @property
    def playlistData(self):
        return [track.meta
                for track in self.mainController.playlist.iterTrack()]

    def getData(self):
        return {'playlist': self.playlistData}

    def _insert(self, filepath):
        if not self.mainController.library.pathExists(filepath):
            self.request.setResponseCode(http.NOT_FOUND)
            return {'err': 'Track not in library',
                    'playlist': self.playlistData}

        track = Track(filepath)
        self.mainController.playlist.insert(track, self.positionArg)
        return {'msg': 'Track added',
                'playlist': self.playlistData}

    def insert(self):
        filepath = '/' + url_unquote(self.filepathArg)
        return self._insert(filepath)

    def libraryInsert(self):
        trackIds = self.trackIdsArg.split(',')
        trackId = trackIds[0]
        # TODO : support multiple tracks
        filepath = txplaya.library.Library.decodePath(trackId)
        return self._insert(filepath)

    def remove(self):
        try:
            self.mainController.playlist.remove(self.positionArg)
        except IndexError:
            self.request.setResponseCode(http.NOT_FOUND)
            return {'msg': 'Track out of bounds'}

        return {'msg': 'Track removed',
                'playlist': self.playlistData}

    def move(self):
        playlist = self.mainController.playlist
        start, end = self.startArg, self.endArg

        if start == end or start + 1 == end:
            return self.getData()

        playlist.move(start, end)

        return self.getData()

    def clear(self):
        self.mainController.playlist.clear()
        return {'msg': 'Playlist cleared',
                'playlist': self.playlistData}


class Player(BaseController):

    def __init__(self, request, action, position=None):
        BaseController.__init__(self, request)

        self.positionArg = position

        self.request.setResponseCode(http.OK)

        action = getattr(self, action)
        response = action()

        self.request.setHeader('Content-Type', 'application/json')
        self.write(json.dumps(response))
        self.finish()

    def start(self):
        if self.positionArg is None:
            self.positionArg = 0

        try:
            self.mainController.playlist.start(self.positionArg)
        except PlaylistError, err:
            return {'err': repr(err)}

        player = self.mainController.player

        player.stop()
        player.feed(self.mainController.playlist.currentTrack)
        player.start()

        return {'msg': 'Started'}

    def stop(self):
        self.mainController.player.stop()
        self.mainController.playlist.stop()
        return {'msg': 'Stoped'}

    def pause(self):
        if self.mainController.player.paused:
            self.mainController.player.resume()
            msg = 'Resumed'
        else:
            self.mainController.player.pause()
            msg = 'Paused'
        return {'msg': msg}


class Stream(BaseStream):

    def __init__(self, request):
        BaseStream.__init__(self, request)

        self.request.setHeader('Content-Type', 'audio/mp3')
        self.mainController.listenerRegistry.add(self)

        # push history to it
        for buf in tuple(self.mainController.player.history):
            self.onPush(buf)

    def onConnectionLost(self, reason):
        self.mainController.listenerRegistry.remove(self)


class Library(BaseController):

    def __init__(self, request, action):
        BaseController.__init__(self, request)

        self.request.setResponseCode(http.OK)

        action = getattr(self, action)
        response = action()

        self.request.setHeader('Content-Type', 'application/json')

        if not self.wait:
            self.write(json.dumps(response))
            self.finish()

    def rescan(self):
        self.request.setHeader('Content-Type', 'text/plain')

        self.dirs = self.mainController.library.scanDirs()

        self.startTime = time()
        self.total = len(self.dirs)
        self.progress = 0

        self._loopScan()
        self.wait = True

    def _loopScan(self):
        if len(self.dirs) == 0:
            return self.scanFinished()

        dirname, filenames = self.dirs.pop()
        self.mainController.library.scanFiles(dirname, filenames)

        newProgress = int((1. - len(self.dirs) * 1.0 / self.total) * 100)

        if int(newProgress) > self.progress:
            self.progress = newProgress
            self.request.write(json.dumps({'scanprogress': newProgress}) + '\n')

        deferLater(reactor, 0, self._loopScan)

    def scanFinished(self):
        library = self.mainController.library

        log.msg('Rescan finised in %d seconds.' % int(time() - self.startTime))
        log.msg('Total tracks: %d' % len(library.data))
        library.saveBin()

        self.write(json.dumps({'msg': 'Rescan finished',
                               'library': library.data}) + '\n')
        self.finish()

    def getLibrary(self):
        return {'library': self.mainController.library.data}


class InfoStream(BaseStream):

    def __init__(self, request):
        BaseStream.__init__(self, request)

        self.request.setHeader('Content-Type', 'text/plain')
        self.mainController.infoListenerRegistry.add(self)

        # push current song
        playlist = self.mainController.playlist

        if playlist.currentPosition is None:
            event = {'event': 'PlaybackFinished',
                     'data': {}}
        else:
            event = {'event': 'TrackStarted',
                     'data': {'position': playlist.currentPosition,
                          'track': playlist.currentTrack.meta}}

        self.write(json.dumps(event) + '\n')

    def onConnectionLost(self, reason):
        self.mainController.infoListenerRegistry.remove(self)
