import json

from PyQt5.QtCore import QObject, pyqtSignal


class QInfoStream(QObject):

    trackStarted = pyqtSignal(object)
    playbackFinished = pyqtSignal()
    playlistChanged = pyqtSignal(object)
    disconnected = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)

        from txplayagui.client import infostream
        self._rq = infostream()
        self._rq.lineReceived.connect(self._feedEvent)
        self._rq.error.connect(self._onError)

    def _feedEvent(self, data):
        data = json.loads(data.strip())
        if 'event' not in data or 'data' not in data:
            print 'Infostream: invalid event', repr(data)
        event, data = data['event'], data['data']

        if event == 'TrackStarted':
            self.trackStarted.emit(data)

        elif event == 'PlaybackFinished':
            self.playbackFinished.emit()

        elif event == 'PlaylistChanged':
            self.playlistChanged.emit(data)

        else:
            print 'Infostream: %s event not implemented' % event

    def _onError(self, code):
        self._rq.close()
        self.disconnected.emit()
