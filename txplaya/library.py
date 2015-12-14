from os.path import dirname
from os.path import join as path_join
from os import environ, walk
from zlib import compress, decompress
import json
from base64 import urlsafe_b64encode, urlsafe_b64decode

from twisted.internet.defer import Deferred
from twisted.internet.task import deferLater

from txplaya.track import Track

if 'TXPLAYA_LIBPATH' in environ:
    PATH = environ['TXPLAYA_LIBPATH']
else:
    from os.path import expanduser
    PATH = path_join(expanduser('~'), 'Music')

BINPATH = path_join(dirname(dirname(__file__)), '.library')


class Library(object):

    def __init__(self, reactor):
        self.reactor = reactor
        try:
            self.readBin()
        except Exception:
            self._lib = {}

    @property
    def data(self):
        return self._lib.copy()

    def readBin(self):
        with open(BINPATH, 'rb') as f:
            self._lib = json.loads(decompress(f.read()))

    @classmethod
    def encodePath(cls, path):
        return urlsafe_b64encode(compress(path))

    @classmethod
    def decodePath(cls, encodedPath):
        compressed = urlsafe_b64decode(str(encodedPath))
        return decompress(compressed)

    def scanAll(self):
        """Returns a deferred that fires empty when the library is scanned completely"""
        d = Deferred()
        self._scanning = {}
        self._lib = {}

        for _pathId, (dirpath, _, filenames) in tuple(enumerate(walk(PATH))):
            partialDeferredUid = len(self._scanning)
            partialDeferred = deferLater(self.reactor, 0, self._scanPartial,
                                         dirpath, filenames)
            partialDeferred.addCallback(self._partialScanFinished, partialDeferredUid, d)
            self._scanning[partialDeferredUid] = partialDeferred

        return d

    def _scanPartial(self, dirpath, filenames):
        for filename in filenames:
            path_ = path_join(dirpath, filename)
            track = Track(path_)

            if not track.has_tags or track.trackName == '':
                continue

            trackId = Library.encodePath(path_)
            self._lib[trackId] = track.meta

    def _partialScanFinished(self, _, partialDeferredUid, scanAllDeferred):
        del self._scanning[partialDeferredUid]
        if len(self._scanning) == 0:
            self._scanning = None
            scanAllDeferred.callback(None)

    def saveBin(self):
        with open(BINPATH, 'wb') as f:
            f.write(compress(json.dumps(self._lib)))
