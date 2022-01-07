from scripts.utils import nz, nd
from PyQt5.QtWidgets import QSizePolicy, QListWidget, QListWidgetItem, QAbstractItemView


class QCustomListWidget(QListWidget):
    def __init__(self, QCustomWidget, initializationData=[]):
        super(QCustomListWidget, self).__init__()
        self.QCustomWidget = QCustomWidget
        self.set_data(initializationData)
        # Customize SizePolicy
        self.setMinimumWidth(QCustomWidget().minimumWidth() + 30)
        sizePolicy = QSizePolicy(QSizePolicy.MinimumExpanding,
                                 QSizePolicy.Preferred)
        self.setSizePolicy(sizePolicy)
        # multi selection
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def add_default_items(self, num):
        for j in range(num):
            newItem = self.QCustomWidget()
            self.add_item(newItem)

    def add_item(self, newItemWidget):
        newItemWidget.i = self.count()
        # Create QListWidgetItem
        myQListWidgetItem = QListWidgetItem(self)
        # Set size hint
        myQListWidgetItem.setSizeHint(newItemWidget.sizeHint())
        # Add QListWidgetItem into QListWidget
        self.addItem(myQListWidgetItem)
        self.setItemWidget(myQListWidgetItem, newItemWidget)

    def set_itemData(self, j, data, strFlag=False):
        self.itemWidget(self.item(j)).set_data(data, strFlag)

    def set_item_idx(self, j, idx):
        self.itemWidget(self.item(j)).i = idx

    def get_itemData(self, j):
        itemWidget = self.itemWidget(self.item(j))
        if type(itemWidget) is self.QCustomWidget:
            return itemWidget.get_data()
        else:
            return None

    def get_item(self, j):
        return self.itemWidget(self.item(j))

    def set_state(self, j, state, txt=""):
        self.itemWidget(self.item(j)).change_status(state, txt)

    def set_progress(self, j, progress):
        self.itemWidget(self.item(j)).set_progress(progress)

    def set_progress_info(self, j, download_info):
        self.itemWidget(self.item(j)).set_download_info(*download_info)

    def set_data(self, initializationData, strFlag=False):
        self.clear()
        for data in initializationData:
            newItem = self.QCustomWidget()
            newItem.set_data(data, strFlag)
            self.add_item(newItem)

    def get_data(self):
        data = []
        for j in range(self.count()):
            data.append(self.get_itemData(j))
        return data

# >---------------------------------------------------------------------------------------------------------------------<
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QPropertyAnimation, Qt, pyqtProperty
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QMovie
from PyQt5.QtWidgets import QWidget, QLabel

class Spinner(QLabel):
    def __init__(self, pixmap=""):
        QLabel.__init__(self)
        #super(Spinner, self).__init__(*args, **kwargs)
        self.parent = None
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._angle = 0
        self.pixmap = None
        self.set_pixmap(pixmap)
        self.setScaledContents(True)

        self.animation = QPropertyAnimation(self, b"angle")
        self.animation.setDuration(2000)
        self.animation.setStartValue(0)
        self.animation.setEndValue(360)
        self.animation.setLoopCount(-1)

    def set_pixmap(self, pixmap):
        self.pixmap = QPixmap(pixmap)
        self.pixmap = self.pixmap.scaled(self.width(), self.height(), Qt.AspectRatioMode.IgnoreAspectRatio)
        self.setPixmap(self.pixmap)

    def start_animation(self):
        self.animation.start()

    def stop_animation(self):
        self.animation.stop()
        self.angle = 0

    @pyqtProperty(int)
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = value
        self.update()

    def paintEvent(self, ev=None):
        n = self.width() // 2
        painter = QPainter(self)
        painter.translate(n, n)
        painter.rotate(self._angle)
        painter.translate(-n, -n)
        painter.drawPixmap(0, 0, self.pixmap)
# >---------------------------------------------------------------------------------------------------------------------<
class QModernListWidgetItem(QWidget):
    def __init__(self, parent=None, nombre_archivo="-", download_info=(0, 0, 0, 0), progress=0):
        QWidget.__init__(self)
        self.parent = parent
        self.__i = 0
        self.setupUi()
        self.set_filename(nombre_archivo)
        self.set_download_info(*download_info)
        self.set_progress(progress)

    @property
    def i(self):
        return self.__i

    @i.setter
    def i(self, value):
        self.__i = value

    def setupUi(self):
        self.setObjectName("item")
        self.resize(400, 80)
        self.setMinimumSize(QtCore.QSize(0, 80))
        self.setMaximumSize(QtCore.QSize(16777215, 80))
        self.gridLayout = QtWidgets.QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")
        self.status_lbl = Spinner()#QLabel(self)
        self.status_lbl.setScaledContents(True)
        self.status_lbl.setMinimumSize(QtCore.QSize(60, 60))
        self.status_lbl.setMaximumSize(QtCore.QSize(60, 60))
        icon = QtGui.QPixmap("recursos/Emoji Objects-98.png")
        self.status_lbl.setPixmap(icon)
        self.status_lbl.setObjectName("status_lbl")
        self.gridLayout.addWidget(self.status_lbl, 0, 0, 3, 1)
        self.filename = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.filename.setFont(font)
        self.filename.setStyleSheet("color: rgb(255, 255, 255);")
        self.filename.setWordWrap(True)
        self.filename.setObjectName("filename")
        self.gridLayout.addWidget(self.filename, 0, 1, 1, 1)
        self.progressBar = QtWidgets.QProgressBar(self)
        self.progressBar.setMinimumSize(QtCore.QSize(0, 5))
        self.progressBar.setMaximumSize(QtCore.QSize(16777215, 5))
        self.progressBar.setAlignment(QtCore.Qt.AlignCenter)
        self.progressBar.setTextVisible(False)
        self.progressBar.setFont(font)
        self.progressBar.setFormat("")
        self.progressBar.setObjectName("progressBar")
        self.gridLayout.addWidget(self.progressBar, 1, 1, 1, 1)
        self.info = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(11)
        self.info.setFont(font)
        self.info.setStyleSheet("color: rgb(158, 158, 158);")
        self.info.setWordWrap(True)
        self.info.setObjectName("info")
        self.gridLayout.addWidget(self.info, 2, 1, 1, 1)
        self.action_btn = QtWidgets.QToolButton(self)
        self.action_btn.setMinimumSize(QtCore.QSize(60, 60))
        self.action_btn.setMaximumSize(QtCore.QSize(60, 60))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("recursos/close.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.action_btn.setIcon(icon)
        self.action_btn.setIconSize(QtCore.QSize(60, 60))
        self.action_btn.setAutoRaise(True)
        self.action_btn.setObjectName("action_btn")
        self.gridLayout.addWidget(self.action_btn, 0, 2, 3, 1)
        self.action_btn.clicked.connect(self.action_button_state)

        self.retranslateUi()
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("item", "Item"))
        self.status_lbl.setText(_translate("item", "..."))
        self.filename.setText(_translate("item", "-"))
        self.info.setText(_translate("item", "0 B/0 B • ∞ • 0B/s"))

    def set_filename(self, filename):
        self.filename.setText(filename)

    def set_progress(self, value):
        self.progressBar.setValue(value)

    def set_download_info(self, downloaded, total_size, elapsed_time, speed):
        self.info.setText(f"{nz(downloaded)}/{nz(total_size)} • {nd(elapsed_time)} • {nz(speed)}/s")

    def set_info(self, info):
        if info:
            self.info.setStyleSheet("color: rgb(158, 158, 158);")
            self.info.setText(info)

    def set_error(self, info):
        self.info.setStyleSheet("color: rgb(255, 161, 163);")
        self.info.setText(info)

    def change_status(self, status, txt=""):
        self.status_lbl.set_pixmap(status.value)
        if status.name == "DESCARGANDO":
            self.status_lbl.start_animation()
        else:
            self.status_lbl.stop_animation()
        if txt:
            if status.name == "ERROR":
                self.set_error(txt)
            else:
                self.set_info(txt)

    def action_button_state(self):
        self.parent.detener_una(self.i)
