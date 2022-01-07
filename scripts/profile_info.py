from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QDialog

from scripts.constants import DARK_STYLE


class Perfil(QDialog):
    def __init__(self, foto, nick, descrip, parent=None):
        QDialog.__init__(self)
        self.parent = parent
        self.setObjectName("Dialog")
        self.resize(400, 300)
        self.setMinimumSize(QtCore.QSize(400, 300))
        self.setMaximumSize(QtCore.QSize(400, 350))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("recursos/todus.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)
        self.setStyleSheet(DARK_STYLE)
        self.setModal(True)
        self.gridLayout = QtWidgets.QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")
        self.profile_description = QtWidgets.QTextEdit(self)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.profile_description.setFont(font)
        self.profile_description.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.profile_description.setReadOnly(True)
        self.profile_description.setObjectName("profile_description")
        self.gridLayout.addWidget(self.profile_description, 2, 0, 1, 1)
        self.profile_name = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.profile_name.setFont(font)
        self.profile_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.profile_name.setWordWrap(True)
        self.profile_name.setObjectName("profile_name")
        self.gridLayout.addWidget(self.profile_name, 1, 0, 1, 1)
        self.widget = QtWidgets.QWidget(self)
        self.widget.setObjectName("widget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.widget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.profile_img = QtWidgets.QLabel(self.widget)
        self.profile_img.setMinimumSize(QtCore.QSize(150, 150))
        self.profile_img.setMaximumSize(QtCore.QSize(150, 150))
        self.profile_img.setStyleSheet("border: 2px solid #76797C;")
        self.profile_img.setText("")
        self.profile_img.setPixmap(QtGui.QPixmap("default_user.png"))
        self.profile_img.setScaledContents(True)
        self.profile_img.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.profile_img.setObjectName("recursos/profile_img")
        self.gridLayout_2.addWidget(self.profile_img, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.widget, 0, 0, 1, 1)

        self.retranslateUi()
        QtCore.QMetaObject.connectSlotsByName(self)
        # vars
        self.foto = foto
        self.nick = nick
        self.descrip = descrip
        self.mostrar_info()

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Dialog", "Perfil de toDus"))
        self.profile_description.setToolTip(_translate("Dialog", "Descripción de su perfil en toDus"))
        self.profile_description.setHtml(_translate("Dialog",
                                                    "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
                                                    "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
                                                    "p, li { white-space: pre-wrap; }\n"
                                                    "</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:12pt; font-weight:400; font-style:normal;\">\n"
                                                    "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:11pt;\">Sin datos</span></p></body></html>"))
        self.profile_name.setToolTip(
            _translate("Dialog", "<html><head/><body><p>Nickname de su perfil de toDus</p></body></html>"))
        self.profile_name.setText(_translate("Dialog", "Sin datos"))
        self.profile_img.setToolTip(_translate("Dialog",
                                               "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Imagen de su perfil de toDus</span></p></body></html>"))

    def mostrar_info(self):
        self.profile_img.setPixmap(QtGui.QPixmap(self.foto))
        self.profile_name.setText(self.nick)
        self.profile_description.setPlainText(self.descrip)