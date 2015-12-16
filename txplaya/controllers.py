import json
from time import time

from twisted.web import http
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
        # TODO : check for path existance, else return 404
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

    def current(self):
        if self.mainController.playlist.currentPosition is None:
            return {'msg': 'Not playing',
                    'position': -1,
                    'track': {}}

        return {'position': self.mainController.playlist.currentPosition,
                'track': self.mainController.playlist.currentTrack.meta}


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
        startTime = time()
        library = self.mainController.library
        d = library.scanAll()

        def onFinished(result):
            log.msg('Rescan finised in %d seconds.' % int(time() - startTime))
            log.msg('Total tracks: %d' % len(library.data))
            library.saveBin()

            self.write(json.dumps(
                {'msg': 'Rescan finished',
                 'library': self.mainController.library.data}))

            self.finish()

        d.addCallback(onFinished)
        self.wait = True

    def getLibrary(self):
        return {'library': self.mainController.library.data}


class InfoStream(BaseStream):

    def __init__(self, request):
        BaseStream.__init__(self, request)

        self.request.setHeader('Content-Type', 'text/plain')
        self.mainController.infoListenerRegistry.add(self)

    def onConnectionLost(self, reason):
        self.mainController.infoListenerRegistry.remove(self)
