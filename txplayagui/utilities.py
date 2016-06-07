import json

from PyQt5.QtCore import QMimeData
from PyQt5.QtGui import QIcon, QPixmap


def mimeWrapJson(data):
    data_ = json.dumps(data)
    mimeData = QMimeData()
    mimeData.setText(data_)
    return mimeData

def unwrapMime(mimeData):
    return json.loads(mimeData.text())

def loadIcon(path):
    icon = QIcon()
    icon.addPixmap(QPixmap(path), QIcon.Normal, QIcon.Off)
    return icon


class SortedDict(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._orderedKeys = sorted(self.keys())

    def __setitem__(self, key, val):
        resort = (key not in self)
        dict.__setitem__(self, key, val)
        if resort:
            self._orderedKeys = sorted(self.keys())

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._orderedKeys.remove(key)

    def __getitem__(self, key):
        if isinstance(key, int):
            key = self._orderedKeys[key]
        return dict.__getitem__(self, key)

    def itemAt(self, index):
        key = self._orderedKeys[index]
        return (key, self[key])

    def index(self, key):
        return self._orderedKeys.index(key)

    def clear(self, *args, **kwargs):
        dict.clear(self, *args, **kwargs)
        self._orderedKeys[:] = []

    def popitem(self):
        key, val = dict.popitem(self)
        self._orderedKeys.remove(key)
        return key, val
