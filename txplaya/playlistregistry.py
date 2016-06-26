from os.path import dirname
from os.path import join as path_join
from os import environ
from zlib import compress, decompress
import json
from base64 import b64encode, b64decode

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
        names = self._reg.keys()
        if '__current__' in names:
            names.remove('__current__')
        names.sort()
        return names

    def savePlaylist(self, name, trackPaths):
        self._reg[name] = map(b64encode, trackPaths)
        self.save()

    def loadPlaylist(self, name):
        try:
            playlist = self._reg[name]
        except KeyError:
            return []
        return map(b64decode, playlist)

    def deletePlaylist(self, name):
        try:
            del self._reg[name]
        except KeyError:
            pass
        else:
            self.save()

playlistRegistry = PlaylistRegistry()
