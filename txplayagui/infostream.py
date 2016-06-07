import json
from math import ceil

from PyQt5.QtCore import QObject, pyqtSignal


class QInfoStream(QObject):

    trackStarted = pyqtSignal(object)
    playbackFinished = pyqtSignal()
    playbackPaused = pyqtSignal(bool)
    playlistChanged = pyqtSignal(object)
    disconnected = pyqtSignal()
    timerUpdated = pyqtSignal(int)
    playlistRegistryUpdated = pyqtSignal(object)

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

        elif event == 'PlaybackPaused':
            paused = data['paused']
            self.playbackPaused.emit(paused)

        elif event == 'PlaylistChanged':
            self.playlistChanged.emit(data)

        elif event == 'TimerUpdate':
            progress = int(data['time'])
            self.timerUpdated.emit(progress)

        elif event == 'PlaylistRegistryUpdated':
            list_ = data['list']
            self.playlistRegistryUpdated.emit(list_)

        else:
            print 'Infostream: %s event not implemented' % event

    def _onError(self, code):
        self._rq.close()
        self.disconnected.emit()
