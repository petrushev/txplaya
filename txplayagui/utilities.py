import json

from PyQt5.QtCore import QMimeData


def mimeWrapJson(data):
    data_ = json.dumps(data)
    mimeData = QMimeData()
    mimeData.setText(data_)
    return mimeData

def unwrapMime(mimeData):
    return json.loads(mimeData.text())
