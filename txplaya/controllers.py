import json

from twisted.web import http

from werkzeug.urls import url_unquote

from txplaya.player import Track, PlaylistError


class BaseController(object):

    def __init__(self, request):
        self.mainController = request.mainController
        self.request = request
        self.request.setHeader('Content-Type', 'text/html')

    def write(self, data):
        self.request.write(data)

    def finish(self):
        self.request.finish()


class PlaylistManager(BaseController):

    def __init__(self, request, action, filepath='', position=None, start=None, end=None):
        BaseController.__init__(self, request)

        self.positionArg = position
        self.filepathArg = filepath
        self.startArg = start
        self.endArg = end

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

    def insert(self):
        filepath = '/' + url_unquote(self.filepathArg)
        track = Track(filepath)
        self.mainController.playlist.insert(track, self.positionArg)

        return {'msg': 'Track added',
                'playlist': self.playlistData}

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


class Stream(BaseController):

    def __init__(self, request):
        BaseController.__init__(self, request)

        self.request.setHeader('Content-Type', 'audio/mp3')
        self.request.connectionLost = self.onConnectionLost

        self.mainController.listenerRegistry.add(self)

        # push history to it
        for buf in tuple(self.mainController.player.history):
            self.onPush(buf)

    def onConnectionLost(self, reason):
        self.mainController.listenerRegistry.remove(self)

    def onPush(self, buf):
        self.write(buf)
