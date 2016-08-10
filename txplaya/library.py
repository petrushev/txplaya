from os.path import dirname, abspath
from os.path import join as path_join
from os import environ, walk, pathsep, stat
from zlib import compress, decompress
from base64 import urlsafe_b64encode, urlsafe_b64decode
import pickle

from txplaya.track import Track

if 'TXPLAYA_LIBPATH' in environ:
    PATH = environ['TXPLAYA_LIBPATH']
else:
    from os.path import expanduser
    PATH = path_join(expanduser('~'), 'Music')

BINPATH = path_join(dirname(dirname(__file__)), '.library')


class Library(object):

    def __init__(self):
        try:
            self.readBin()
        except Exception:
            self._lib = {}

    @property
    def data(self):
        return self._lib.copy()

    def readBin(self):
        with open(BINPATH, 'rb') as f:
            self._lib = pickle.loads(decompress(f.read()))

    @classmethod
    def encodePath(cls, path):
        return urlsafe_b64encode(compress(path))

    @classmethod
    def decodePath(cls, encodedPath):
        compressed = urlsafe_b64decode(str(encodedPath))
        return decompress(compressed)

    def clear(self):
        self._lib.clear()

    def scanDirs(self):
        paths = map(abspath, PATH.split(pathsep))

        result = []
        for path_ in paths:
            partial = [(dirpath, filenames)
                       for _pathId, (dirpath, _, filenames) in tuple(enumerate(walk(path_)))]
            result.extend(partial)

        return result

    def scanFiles(self, dirpath, filenames):
        for filename in filenames:
            path_ = path_join(dirpath, filename)

            size = stat(path_).st_size / 1000 # kB
            if size < 100 or size > 100000:
                continue

            track = Track(path_)
            if not track.has_tags or track.trackName == '':
                continue

            trackId = Library.encodePath(path_)
            self._lib[trackId] = track.meta

    def saveBin(self):
        with open(BINPATH, 'wb') as f:
            f.write(compress(pickle.dumps(self._lib, 1)))

    def pathExists(self, filepath):
        filepath = abspath(filepath)
        trackUid = Library.encodePath(filepath)
        return trackUid in self._lib
