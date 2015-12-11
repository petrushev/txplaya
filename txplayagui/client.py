from PyQt5.QtCore import pyqtSignal, QObject, QUrl, pyqtSlot
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

from werkzeug.urls import url_encode, url_quote

BASE_URL = 'http://localhost:8070'


class QRequest(QObject):

    manager = QNetworkAccessManager()
    finished = pyqtSignal()

    def __init__(self, url, params=None, parent=None):
        QObject.__init__(self, parent=parent)

        self.headers = {}

        self.params = params

        if params is not None:
            url = url + "?" + url_encode(params)
        self.qUrl = QUrl(url)

        self.request = QNetworkRequest(self.qUrl)

    def get(self):
        self.response = self.manager.get(self.request)
        self.response.finished.connect(self._onFinished)
        

    @pyqtSlot()
    def _onFinished(self):
        self.data = self.response.readAll().data()
        self.statusCode = self.response.attribute(QNetworkRequest.HttpStatusCodeAttribute)

        self.finished.emit()
        self.response.deleteLater()


def _requestGet(url):
    rq = QRequest(url)
    rq.get()
    return rq

def getPlaylist():
    url = BASE_URL + '/playlist'
    return _requestGet(url)

def insert(track, position=None):
    url = BASE_URL + '/playlist/insert/'
    if position is not None:
        url = url + str(position) + '/'
    url = url + url_quote(track.path[1:])
    return _requestGet(url)

def remove(position):
    url = BASE_URL + '/playlist/remove/' + str(position)
    return _requestGet(url)

def play(position=None):
    url = BASE_URL + '/player/start'
    if position is not None:
        url = url + '/' + str(position)
    return _requestGet(url)

def current():
    url = BASE_URL + '/playlist/current'
    return _requestGet(url)

def moveTrack(start, end):
    url = '%s/playlist/move/%d/%d' % (BASE_URL, start, end)
    return _requestGet(url)

def pause():
    url = '%s/player/pause' % BASE_URL
    return _requestGet(url)

def stop():
    url = '%s/player/stop' % BASE_URL
    return _requestGet(url)
