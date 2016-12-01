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
        self.isFinished = False

        self.request.notifyFinish().addErrback(self.finishWithError)

    def write(self, data):
        self.request.write(data)

    def finish(self):
        if not self.isFinished:
            self.request.finish()

    def finishWithError(self, failure):
        self.isFinished = True

    def writeJson(self, data):
        self.request.setHeader('Content-Type', 'application/json')
        self.request.write(json.dumps(data).encode('utf-8'))

    def writeJsonLine(self, data):
        self.request.write((json.dumps(data) + '\n').encode('utf-8'))

    def respondJson(self, data):
        self.writeJson(data)
        self.finish()


class BaseStream(BaseController):

    def __init__(self, request):
        BaseController.__init__(self, request)

        self.request.connectionLost = self.onConnectionLost

    def onPush(self, buf):
        self.write(buf)


class PlaylistManager(BaseController):

    def __init__(self, request, action, filepath='', position=None, start=None, end=None,
                 trackIds='', playlistName=''):
        BaseController.__init__(self, request)

        self.positionArg = position
        self.filepathArg = filepath
        self.startArg = start
        self.endArg = end
        self.trackIdsArg = trackIds
        self.playlistNameArg = playlistName

        self.request.setResponseCode(http.OK)

        action = getattr(self, action)
        response = action()

        self.respondJson(response)

    @property
    def playlistData(self):
        return self.mainController.playlist.playlistData

    def getData(self):
        return {'playlist': self.playlistData,
                'hasUndo': self.mainController.playlist.hasUndo,
                'hasRedo': self.mainController.playlist.hasRedo}

    def _insert(self, filepaths):
        self.mainController.playlist.mark()

        for filepath in filepaths:
            if not self.mainController.library.pathExists(filepath):
                continue
            track = Track(filepath)
            self.mainController.playlist.insert(track, self.positionArg)

        return {'msg': 'Tracks added'}

    def insert(self):
        filepath = '/' + url_unquote(self.filepathArg)
        return self._insert([filepath])

    def libraryInsert(self):
        trackIds = self.trackIdsArg.split(',')
        filepaths = [txplaya.library.Library.decodePath(trackId)
                     for trackId in trackIds]
        return self._insert(filepaths)

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

    def save(self):
        from txplaya.playlistregistry import playlistRegistry
        playlistName = url_unquote(self.playlistNameArg)
        self.mainController.playlist.save(playlistName)

        event = {'event': 'PlaylistRegistryUpdated',
                 'data': {'list': playlistRegistry.list_()}}
        self.mainController.announce(event)

        return {'msg': 'Playlist saved'}

    def load(self):
        playlistName = url_unquote(self.playlistNameArg)
        trackPaths = self.mainController.playlist.load(playlistName)

        return self._insert(trackPaths)

    def delete(self):
        from txplaya.playlistregistry import playlistRegistry
        playlistName = url_unquote(self.playlistNameArg)
        playlistRegistry.deletePlaylist(playlistName)

        event = {'event': 'PlaylistRegistryUpdated',
                 'data': {'list': playlistRegistry.list_()}}
        self.mainController.announce(event)

        return {'msg': 'Playlist deleted'}

    def undo(self):
        self.mainController.playlist.undo()
        return {'msg': 'Playlist undo'}

    def redo(self):
        self.mainController.playlist.redo()
        return {'msg': 'Playlist redo'}


class Player(BaseController):

    def __init__(self, request, action, position=None):
        BaseController.__init__(self, request)

        self.positionArg = position

        self.request.setResponseCode(http.OK)

        action = getattr(self, action)
        response = action()

        self.respondJson(response)

    def start(self):
        if self.positionArg is None:
            self.positionArg = 0

        return self._start(self.positionArg)

    def _start(self, position):
        try:
            self.mainController.playlist.start(position)
        except PlaylistError, err:
            return {'err': repr(err)}

        player = self.mainController.player
        playlist = self.mainController.playlist

        try:
            player.feed(playlist.currentTrack, clear=True)
        except IOError:
            currentPosition = playlist.currentPosition
            playlist.remove(playlist.currentPosition, emit=False)
            self._start(currentPosition)
        else:
            player.start()
            return {'msg': 'Started'}

    def next(self):
        position = self.mainController.playlist.currentPosition
        if position is None:
            return {'err': 'Not playing'}
        return self._start(position + 1)

    def prev(self):
        position = self.mainController.playlist.currentPosition
        if position is None:
            return {'err': 'Not playing'}
        return self._start(position - 1)

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

        self.request.setHeader('Content-Type', 'audio/mpeg')
        self.request.setHeader('Transfer-Encoding', 'chunked')
        self.request.setHeader('Content-Transfer-Encoding', 'binary')
        self.request.setHeader('Accept-Ranges', 'bytes')
        self.request.setHeader('Content-Disposition', 'inline')

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

        if not self.wait:
            self.respondJson(response)
        else:
            self.request.setHeader('Content-Type', 'application/json')

    def rescan(self):
        self.mainController.library.clear()
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
            self.writeJsonLine({'scanprogress': newProgress})

        deferLater(reactor, 0, self._loopScan)

    def scanFinished(self):
        library = self.mainController.library

        log.msg('Rescan finised in %d seconds.' % int(time() - self.startTime))
        log.msg('Total tracks: %d' % len(library.data))
        library.saveBin()

        self.writeJsonLine({'msg': 'Rescan finished',
                            'library': library.data})
        self.finish()

    def getLibrary(self):
        return {'library': self.mainController.library.data}


class InfoStream(BaseStream):

    def __init__(self, request):
        from playlistregistry import playlistRegistry

        BaseStream.__init__(self, request)

        self.request.setHeader('Content-Type', 'text/plain')
        self.mainController.infoListenerRegistry.add(self)

        playlist = self.mainController.playlist

        # push current song
        if playlist.currentPosition is None:
            event = {'event': 'PlaybackFinished',
                     'data': {}}
            self.writeJsonLine(event)

        else:
            meta = playlist.currentTrack.meta
            if meta is None:
                return
            event = {'event': 'TrackStarted',
                     'data': {'position': playlist.currentPosition,
                              'track': meta}}
            self.writeJsonLine(event)
            event = {'event': 'PlaybackPaused',
                     'data': {'paused': self.mainController.player.paused}}
            self.writeJsonLine(event)

        # push playlist data
        event = {'event': 'PlaylistChanged',
                 'data': {'playlist': playlist.playlistData,
                          'position': playlist.currentPosition,
                          'hasUndo': playlist.hasUndo,
                          'hasRedo': playlist.hasRedo}}
        self.writeJsonLine(event)

        # push list of playlists
        event = {'event': 'PlaylistRegistryUpdated',
                 'data': {'list': playlistRegistry.list_()}}
        self.writeJsonLine(event)

    def onConnectionLost(self, reason):
        self.mainController.infoListenerRegistry.remove(self)
