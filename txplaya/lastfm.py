from os import environ
from datetime import datetime

import pylast


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
        self.network = pylast.LastFMNetwork(
            api_key=KEY, api_secret=SECRET, username=USER, password_hash=passHash)

    def _parseTrackData(self, track):
        artist = track.artist
        album = track.album
        if artist == '' or album == '':
            return None

        albumArtist = track.albumArtist
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

        self.network.scrobble(artist, trackName, timestamp,
                              album, albumArtist, trackNumber)

    def updateNowPlaying(self, track):
        data = self._parseTrackData(track)
        if data is None:
            return

        artist, trackName, album, albumArtist, trackNumber = data
        
        self.network.update_now_playing(artist, trackName, album, albumArtist,
            track_number=trackNumber)
