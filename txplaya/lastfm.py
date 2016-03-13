from os import environ
from datetime import datetime

import pylast

from twisted.internet.threads import deferToThread


USER = environ.get('TXPLAYA_LASTFM_USER')
PASS = environ.get('TXPLAYA_LASTFM_PASS')
KEY = environ.get('TXPLAYA_LASTFM_KEY')
SECRET = environ.get('TXPLAYA_LASTFM_SECRET')


def getScrobbler():
    if None in set((USER, PASS, KEY, SECRET)):
        return None

    return Scrobbler()


class Scrobbler(object):

    def __init__(self):
        passHash = pylast.md5(PASS)
        self.network = None

        d = deferToThread(pylast.LastFMNetwork,
                api_key=KEY, api_secret=SECRET, username=USER, password_hash=passHash)
        d.addCallback(self.onNetworkInitialized)
        d.addErrback(self.onNetworkError)

    def onNetworkInitialized(self, network):
        self.network = network

    def onSuccess(self, *args, **kwargs):
        pass

    def onNetworkError(self, failure):
        failure.printTraceback()

    def deferToThread(self, func, *args, **kwargs):
        d = deferToThread(func, *args, **kwargs)
        d.addCallback(self.onSuccess)
        d.addErrback(self.onNetworkError)
        return d

    def _parseTrackData(self, track):
        if track is None:
            return None

        artist = track.artist
        album = track.album
        albumArtist = track.albumArtist

        if artist == '':
            artist = albumArtist

        if artist == '':
            return None

        if albumArtist == artist:
            albumArtist = None

        trackNumber = track.trackNumber
        if trackNumber == '':
            trackNumber = None

        return artist, track.trackName, album, albumArtist, trackNumber

    def scrobble(self, track):
        data = self._parseTrackData(track)
        if data is None:
            return

        artist, trackName, album, albumArtist, trackNumber = data
        
        timestamp = datetime.utcnow()

        self.deferToThread(self.network.scrobble,
            artist, trackName, timestamp, album, albumArtist, trackNumber)

    def updateNowPlaying(self, track):
        data = self._parseTrackData(track)
        if data is None:
            return

        artist, trackName, album, albumArtist, trackNumber = data

        self.deferToThread(self.network.update_now_playing,
            artist, trackName, album, albumArtist, track_number=trackNumber)
