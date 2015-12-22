# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'txplayagui/ui/library.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_LibraryWidget(object):
    def setupUi(self, LibraryWidget):
        LibraryWidget.setObjectName("LibraryWidget")
        LibraryWidget.resize(362, 557)
        self.verticalLayout = QtWidgets.QVBoxLayout(LibraryWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.querySearchBox = QtWidgets.QLineEdit(LibraryWidget)
        self.querySearchBox.setObjectName("querySearchBox")
        self.horizontalLayout_3.addWidget(self.querySearchBox)
        self.clearSearchButton = QtWidgets.QPushButton(LibraryWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.clearSearchButton.sizePolicy().hasHeightForWidth())
        self.clearSearchButton.setSizePolicy(sizePolicy)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/img/clear_text.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.clearSearchButton.setIcon(icon)
        self.clearSearchButton.setFlat(True)
        self.clearSearchButton.setObjectName("clearSearchButton")
        self.horizontalLayout_3.addWidget(self.clearSearchButton)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.treeView = QtWidgets.QTreeView(LibraryWidget)
        self.treeView.setMinimumSize(QtCore.QSize(300, 0))
        self.treeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.treeView.setObjectName("treeView")
        self.treeView.header().setVisible(False)
        self.verticalLayout.addWidget(self.treeView)
        self.scanControlsLayout = QtWidgets.QHBoxLayout()
        self.scanControlsLayout.setObjectName("scanControlsLayout")
        self.rescanButton = QtWidgets.QPushButton(LibraryWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.rescanButton.sizePolicy().hasHeightForWidth())
        self.rescanButton.setSizePolicy(sizePolicy)
        self.rescanButton.setObjectName("rescanButton")
        self.scanControlsLayout.addWidget(self.rescanButton)
        self.scanProgressBar = QtWidgets.QProgressBar(LibraryWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scanProgressBar.sizePolicy().hasHeightForWidth())
        self.scanProgressBar.setSizePolicy(sizePolicy)
        self.scanProgressBar.setProperty("value", 0)
        self.scanProgressBar.setObjectName("scanProgressBar")
        self.scanControlsLayout.addWidget(self.scanProgressBar)
        self.verticalLayout.addLayout(self.scanControlsLayout)

        self.retranslateUi(LibraryWidget)
        QtCore.QMetaObject.connectSlotsByName(LibraryWidget)

    def retranslateUi(self, LibraryWidget):
        _translate = QtCore.QCoreApplication.translate
        LibraryWidget.setWindowTitle(_translate("LibraryWidget", "Form"))
        self.querySearchBox.setPlaceholderText(_translate("LibraryWidget", "Search media library"))
        self.rescanButton.setText(_translate("LibraryWidget", "Rescan"))

import resource_rc
