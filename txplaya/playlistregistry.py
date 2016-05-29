from os.path import dirname
from os.path import join as path_join
from os import environ
from zlib import compress, decompress
import json

if 'TXPLAYA_PLAYLISTS' in environ:
    PATH = environ['TXPLAYA_PLAYLISTS']
else:
    from os.path import expanduser
    PATH = path_join(expanduser('~'), 'Music')

BINPATH = path_join(dirname(dirname(__file__)), '.playlists')


class PlaylistRegistry(object):

    def __init__(self):
        try:
            self.load()
        except Exception:
            self._reg = {}

    def load(self):
        with open(BINPATH, 'rb') as f:
            content = f.read()

        self._reg = json.loads(decompress(content))

    def save(self):
        content = json.dumps(self._reg)
        content = compress(content)

        with open(BINPATH, 'wb') as f:
            f.write(content)

    def list_(self):
        return sorted(self._reg.keys())

    def savePlaylist(self, name, trackPaths):
        self._reg[name] = trackPaths
        self.save()

    def loadPlaylist(self, name):
        try:
            return self._reg[name]
        except KeyError:
            return []

    def deletePlaylist(self, name):
        try:
            del self._reg[name]
        except KeyError:
            pass
        else:
            self.save()

playlistRegistry = PlaylistRegistry()
