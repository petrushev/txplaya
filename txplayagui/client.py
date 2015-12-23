from PyQt5.QtCore import pyqtSignal, QObject, QUrl, pyqtSlot
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

from werkzeug.urls import url_encode, url_quote

BASE_URL = 'http://localhost:8070'


class QBaseRequest(QObject):

    finished = pyqtSignal()

    def __init__(self, url, params=None, parent=None):
        QObject.__init__(self, parent=parent)

        self.headers = {}
        self.params = params

        if params is not None:
            url = url + "?" + url_encode(params)
        self.qUrl = QUrl(url)

        self.request = QNetworkRequest(self.qUrl)

    @property
    def manager(self):
        if not hasattr(QBaseRequest, '_manager'):
            QBaseRequest._manager = QNetworkAccessManager()

        return QBaseRequest._manager

    def close(self):
        self.response.close()
        self.response.deleteLater()


class QRequest(QBaseRequest):

    def get(self):
        self.response = self.manager.get(self.request)
        self.response.finished.connect(self._onFinished)

    @pyqtSlot()
    def _onFinished(self):
        self.data = self.response.readAll().data()
        self.statusCode = self.response.attribute(QNetworkRequest.HttpStatusCodeAttribute)

        self.finished.emit()
        self.response.deleteLater()


class QStreamRequest(QBaseRequest):

    lineReceived = pyqtSignal(str)

    def __init__(self, url, params=None, parent=None):
        QBaseRequest.__init__(self, url, params, parent)
        self._buf = ''

    def get(self):
        self.response = self.manager.get(self.request)
        self.response.readyRead.connect(self._onReadyRead)
        self.response.finished.connect(self._onFinished)

    def _onReadyRead(self):
        tmp = self.response.readAll().data()
        self._buf = self._buf + tmp
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            self.lineReceived.emit(line)

    @pyqtSlot()
    def _onFinished(self):
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            self.lineReceived.emit(line)

        self.finished.emit()
        self.response.deleteLater()


def _requestGet(url):
    rq = QRequest(url)
    rq.get()
    return rq

def getPlaylist():
    url = BASE_URL + '/playlist'
    return _requestGet(url)

def insert(filepath, position=None):
    url = BASE_URL + '/playlist/insert/'
    if position is not None:
        url = url + str(position) + '/'
    url = url + url_quote(filepath[1:])
    return _requestGet(url)

def remove(position):
    url = BASE_URL + '/playlist/remove/' + str(position)
    return _requestGet(url)

def clear():
    url = BASE_URL + '/playlist/clear'
    return _requestGet(url)

def play(position=None):
    url = BASE_URL + '/player/start'
    if position is not None:
        url = url + '/' + str(position)
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

def next_():
    url = '%s/player/next' % BASE_URL
    return _requestGet(url)

def prev():
    url = '%s/player/prev' % BASE_URL
    return _requestGet(url)

def getLibrary():
    url = BASE_URL + '/library'
    return _requestGet(url)

def rescanLibrary():
    url = BASE_URL + '/library/rescan'
    rq = QStreamRequest(url)
    rq.get()
    return rq

def libraryInsert(hashes, position=None):
    url = BASE_URL + '/playlist/library/insert/'
    if position is not None:
        url = url + str(position) + '/'
    hashes_ = ','.join(hashes)
    url = url + hashes_
    return _requestGet(url)

def infostream():
    url = BASE_URL + '/infostream'
    rq = QStreamRequest(url)
    rq.get()
    return rq
