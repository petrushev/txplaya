from math import ceil

from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from werkzeug.utils import cached_property


def _parseId3(id3):
    meta = {'type': 'mp3'}

    for meta_key, tag_key in (('album', 'TALB'), ('artist', 'TPE1'), ('albumartist', 'TPE2'),
                              ('trackname', 'TIT2')):
        try:
            meta[meta_key] = id3.get(tag_key).text[0]
        except Exception:
            meta[meta_key] = ''

    try:
        meta['tracknumber'] = int(id3.get('TRCK').text[0].split('/')[0])
    except Exception:
        meta['tracknumber'] = ''

    try:
        meta['discnumber'] = int(id3.get('TPOS').text[0].split('/')[0])
    except Exception:
        meta['discnumber'] = ''

    try:
        meta['year'] = int(id3.get('TDRC').text[0].text[:4])
    except Exception:
        meta['year'] = ''

    return meta


def _parseMp4(mp4):
    meta = {'type': 'm4a'}

    for meta_key, tag_key in (('album', '\xa9alb'), ('artist', '\xa9ART'),
                              ('albumartist', 'aART'), ('trackname', '\xa9nam')):
        try:
            meta[meta_key] = mp4[tag_key][0]
        except Exception:
            meta[meta_key] = ''

    try:
        meta['tracknumber'] = int(mp4['trkn'][0][0])
    except Exception:
        meta['tracknumber'] = ''

    try:
        meta['discnumber'] = int(mp4['disk'][0][0])
    except Exception:
        meta['discnumber'] = ''

    try:
        meta['year'] = int(mp4['\xa9day'][0][:4])
    except Exception:
        meta['year'] = ''

    return meta


class Track(object):

    def __init__(self, path):
        self._path = path
        self._meta = {'artist': '', 'length': ''}
        self._parseTags()

    def _parseTags(self):
        try:
            id3 = ID3(self._path)
        except Exception:
            try:
                mp4 = MP4(self._path)
            except Exception:
                print 'no id3, no m4a', repr(self._path[-10:])
            else:
                self._meta.update(_parseMp4(mp4.tags))
        else:
            self._meta.update(_parseId3(id3))

        self._meta['length'] = self.length

    @property
    def data(self):
        with open(self._path, 'rb') as f:
            data = f.read()
        return data

    def dataChunks(self, iterTime):
        type_ = self.meta.get('type')
        if type_ == 'mp3':
            prebufTime = 2.0
        elif type_ == 'm4a':
            prebufTime = 70.0
        else:
            return []

        rawData = self.data

        numChunks = self.length * 1.0 / iterTime
        chunkSize = int(ceil(len(rawData) / numChunks))

        chunks = []

        while len(rawData) > 0:
            chunk, rawData = rawData[:chunkSize], rawData[chunkSize:]
            chunks.append(chunk)

        del rawData

        numPrebufChunks = int(ceil(prebufTime / iterTime))

        prebufChunk, chunks = chunks[:numPrebufChunks], chunks[numPrebufChunks:]
        prebufChunk = ''.join(prebufChunk)
        chunks.insert(0, prebufChunk)

        return chunks

    @cached_property
    def length(self):
        try:
            return MP3(self._path).info.length
        except Exception:
            try:
                return MP4(self._path).info.length
            except Exception:
                return 0

    @property
    def meta(self):
        return self._meta

    @cached_property
    def has_tags(self):
        meta = dict(self.meta)
        del meta['length']
        return set(meta.values()) != set([''])

    @property
    def trackName(self):
        return self._meta['trackname']

    @cached_property
    def artist(self):
        return self._meta['artist']

    @cached_property
    def album(self):
        return self._meta['album']

    @cached_property
    def albumArtist(self):
        return self._meta['albumartist']

    @cached_property
    def discNumber(self):
        return self._meta['discnumber']

    @cached_property
    def trackNumber(self):
        return self._meta['tracknumber']

    @cached_property
    def year(self):
        return self._meta['year']
