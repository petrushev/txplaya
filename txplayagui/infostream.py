import json
from PyQt5.QtCore import QObject, pyqtSignal

class QInfoStream(QObject):

    trackStarted = pyqtSignal(object)
    playlistFinished = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)

        from txplayagui.client import infostream
        self._rq = infostream()
        self._rq.lineReceived.connect(self._feedEvent)

    def _feedEvent(self, data):
        data = json.loads(data.strip())
        if 'event' not in data or 'data' not in data:
            return
        event, data = data['event'], data['data']

        if event == 'TrackStarted':
            self.trackStarted.emit(data)
        elif event == 'PlaylistFinished':
            self.playlistFinished.emit()
