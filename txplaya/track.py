from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from werkzeug.utils import cached_property


class Track(object):

    def __init__(self, path):
        self._path = path

    @property
    def data(self):
        with open(self._path, 'rb') as f:
            data = f.read()
        return data

    @cached_property
    def length(self):
        try:
            return MP3(self._path).info.length
        except Exception:
            return None

    @cached_property
    def _id3(self):
        return ID3(self._path)

    @cached_property
    def album(self):
        try:
            return self._id3.get('TALB').text[0]
        except Exception:
            return ''

    @cached_property
    def artist(self):
        try:
            return self._id3.get('TPE1').text[0]
        except Exception:
            return ''

    @cached_property
    def albumArtist(self):
        try:
            return self._id3.get('TPE2').text[0]
        except Exception:
            return ''

    @cached_property
    def trackName(self):
        try:
            return self._id3.get('TIT2').text[0]
        except Exception:
            return ''

    @cached_property
    def trackNumber(self):
        try:
            return int(self._id3.get('TRCK').text[0].split('/')[0])
        except Exception:
            return ''

    @cached_property
    def discNumber(self):
        try:
            return int(self._id3.get('TPOS').text[0].split('/')[0])
        except Exception:
            return ''

    @cached_property
    def year(self):
        try:
            return int(self._id3.get('TDRC').text[0].text[:4])
        except Exception:
            return ''

    @cached_property
    def meta(self):
        return {'album': self.album,
                'artist': self.artist,
                'albumartist': self.albumArtist,
                'trackname': self.trackName,
                'length': self.length,
                'discnumber': self.discNumber,
                'tracknumber': self.trackNumber,
                'year': self.year}

    @cached_property
    def has_tags(self):
        meta = dict(self.meta)
        del meta['length']
        return set(meta.values()) != set([''])
