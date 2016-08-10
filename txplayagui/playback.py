from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSlot

from txplayagui.ui.playback import Ui_PlaybackWidget


class PlaybackWidget(Ui_PlaybackWidget, QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        Ui_PlaybackWidget.setupUi(self, self)

        self.pauseButton.clicked.connect(self.onPauseClicked)
        self.stopButton.clicked.connect(self.onStopClicked)

    @pyqtSlot()
    def onPauseClicked(self):
        from txplayagui.client import pause
        _ = pause()

    @pyqtSlot()
    def onStopClicked(self):
        from txplayagui.client import stop
        _ = stop()

    def trackStarted(self, trackData):
        trackname = trackData['track']['trackname']
        self.trackProgressBar.setFormat(trackname)

        self.playButton.hide()
        self.pauseButton.show()
        self.pauseButton.setChecked(False)
        self.stopButton.show()

    @pyqtSlot()
    def finished(self):
        self.trackProgressBar.setFormat('not playing')
        self.trackProgressBar.setValue(0)

        self.playButton.show()
        self.pauseButton.hide()
        self.stopButton.hide()

    @pyqtSlot(bool)
    def paused(self, paused):
        self.playButton.hide()
        self.pauseButton.show()
        self.stopButton.show()

        self.pauseButton.setChecked(paused)

    @pyqtSlot(int)
    def timerUpdated(self, progress):
        self.trackProgressBar.setValue(progress)
