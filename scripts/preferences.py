import os
import sqlite3
import subprocess

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtWidgets import QDialog, QMessageBox, QSplashScreen

from scripts.constants import *
from scripts.logger import SENT_TO_LOG
from scripts.settings import SETTINGS, TODUS_VERSION
from scripts.todus import JWP_AUTH, REQUEST_PIN, REQUEST_PASSWORD, REQUEST_TOKEN


class Preferencias(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self)
        self.parent = parent
        uic.loadUi("recursos/settings.ui", self)
        self.cargar_config()
        #
        self.adb.hide()
        #
        self.conexiones()

    def conexiones(self):
        self.guardar_info.clicked.connect(self.guardar_opciones)
        self.auth.textChanged.connect(self.save_token)
        self.recharge_token.clicked.connect(self.extraer_internal_db_token)
        self.auth_info.clicked.connect(self.get_info)
        self.cambiar_sonido.clicked.connect(self.cambiar_sonido_alerta)
        self.cambiar_carpeta_descargas_btn.clicked.connect(self.cambiar_carpeta_descargas)
        self.test_adb.clicked.connect(self.adb_get_devices_papu)
        self.adb_connect_by.currentIndexChanged.connect(self.connect_adb_mode)
        self.version_todus.stateChanged.connect(self.change_user_agent)
        self.user_agent_edit.textChanged.connect(self.save_todus_version)
        self.token_mode.currentIndexChanged.connect(self.show_token_mode)
        self.request_act_token_btn.clicked.connect(self.check_last_request_pin)

    def validar_numero_de_telefono(self):
        phone = str(self.phone_number.value())
        assert len(phone) == 8, "Inserte un número de teléfono válido"
        return f"53{phone}"

    def re_validate(self, value):
        import re
        str = ""
        for letter in value:
            if re.match("[a-zA-Z0-9_=\-\n /.#@!$%^&*()+:><áéíúóäëïüöÁÉÍÓÚÄËÏÖÜ]", letter):
                str += letter
            else:
                str += "\x12"
        return str

    def parse_passw(self, response):
        decoded = response.decode("utf-8", "ignore")
        values = self.re_validate(decoded)
        splited = values.split("\x12")
        dict = {"password":"", "user":"", "nick":"", "description":""}
        filtered = list(filter(lambda i: len(i) and i != "\n", splited))
        print(filtered)
        dict["password"] = filtered[0].strip().replace("\n", "")
        #
        #user = filtered[1].strip().replace("\n", "")
        #dict["user"] = ""
        # dict["nick"] =
        # dict["description"] = filtered[3].strip().replace("\n", "")
        return dict

    def parse_token(self, raw):
        decoded = raw.decode("utf-8", errors="ignore")
        decoded = decoded[4:][:-3]
        return decoded

    def check_last_request_pin(self):
        try:
            last_try = SETTINGS.value("succesfully_token_request", type=bool)
            if not last_try:
                q = QMessageBox.warning(self, "Solicitar Token de activación",
                                        "Hay un inicio de sesión no exitoso. ¿Desea reanudarlo?",
                                        QMessageBox.Yes | QMessageBox.No)
                if q == QMessageBox.Yes:
                    self.request_token()
                else:
                    self.request_pin()
            else:
                self.request_pin()
        except Exception as e:
            print(e.args)
            SENT_TO_LOG(f"Chequeando última solcitud de PIN {e.args}")
            self.error("Chequeando última solcitud de PIN", e.args)

    def request_pin(self):
        try:
            phone = self.validar_numero_de_telefono()
            q = QMessageBox.warning(self, "Solicitar Token de activación",
                                    "Si usa toDus como medio de comunicación y continúa con esta operación, su sesión de toDus quedará invalidada. Aún así ¿desea proceder?",
                                    QMessageBox.Yes | QMessageBox.No)
            if q == QMessageBox.Yes:
                response_1 = REQUEST_PIN(phone)
                self.uid_input.setText(SETTINGS.value("uid", type=str))
                # deshabilitar telefono
                self.phone_number.setEnabled(False)
                # pedir PIN del SMS
                pin, ok = "", False
                while True:
                    pin, ok = QtWidgets.QInputDialog.getText(self, "Activación de cuenta emulada",
                                                             "Escriba los 6 dígitos recibidos por SMS")
                    if not ok:
                        self.phone_number.setEnabled(False)
                        break
                    if pin.isnumeric() and len(pin) == 6:
                        # actualizo vista
                        self.act_token.setValue(pin)
                        # guardo en registro
                        SETTINGS.setValue("activation_token", pin)
                        SETTINGS.sync()
                        # busco el token
                        self.request_token()
                        break
        except Exception as e:
            print(e.args)
            SENT_TO_LOG(f"Solicitando PIN para Token {e.args}")
            self.error("Solicitando PIN", e.args)

    def request_token(self):
        pin = SETTINGS.value("activation_token", type=str)
        phone = f"53{self.phone_number.value()}"
        password = ""
        try:
            response_2 = REQUEST_PASSWORD(phone, pin)
            parsed = self.parse_passw(response_2[1])
            # guardar config
            password = parsed["password"]
            SETTINGS.setValue("password", password)
            self.passw_input.setText(password)
            SETTINGS.setValue("phone_number", phone)
            SETTINGS.setValue("profile_nick", parsed["nick"])
            SETTINGS.setValue("profile_description", parsed["description"])
        except Exception as e:
            print(e.args)
            SENT_TO_LOG(f"Solicitando PASSWORD {e.args}")
            self.error("Solicitando PASSWORD", e.args)
        try:
            response_3 = REQUEST_TOKEN(phone, password)
            # emulacion completada
            SETTINGS.setValue("succesfully_token_request", True)
            #parseo
            parsed = self.parse_token(response_3[1])
            self.auth.setText(parsed)
            # guardar config
            SETTINGS.setValue("token", parsed)
            # habilitar telefono
            self.phone_number.setEnabled(True)
        except Exception as e:
            print(e.args)
            SENT_TO_LOG(f"Solicitando TOKEN {e.args}")
            self.error("Solicitando TOKEN", e.args)
        SETTINGS.sync()
        # informo exito
        QMessageBox.information(self, "Solicitud de Token", "El Token de autorización se extrajo correctamente")

    def show_token_mode(self, i):
        if not i:
            self.request_token_group.show()
            self.adb.hide()
        else:
            self.request_token_group.hide()
            self.adb.show()

    def cambiar_carpeta_descargas(self):
        carpeta = QtWidgets.QFileDialog.getExistingDirectory(self, "Seleccione una carpeta para almacenar las Descargas")
        if carpeta:
            self.dir_carpeta_descargas.setText(carpeta)

    def cambiar_sonido_alerta(self):
        sonido, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Seleccionar un audio", "sounds/", "Audio (*.mp3; *.wav; *.ogg)")
        if sonido:
            self.sonido_dir.setText(sonido)

    def get_info(self):
        auth = SETTINGS.value("token", type=str)
        if auth and "." in auth and auth.count(".") == 2:
            try:
                valores = JWP_AUTH(auth)
                self.info_ = AuthInfo(valores)
                self.info_.show()
            except Exception as e:
                self.error("[Error] Analizar Token", e.args)

    def save_token(self, token):
        SETTINGS.setValue("token", token)
        JWP_AUTH(token)

    def save_todus_version(self, txt):
        SETTINGS.setValue("todus_version", txt)
        SETTINGS.sync()

    def change_user_agent(self):
        change = self.version_todus.isChecked()
        if change:
            SETTINGS.setValue("change_ua", change)
        else:
            self.user_agent_edit.setText(TODUS_VERSION)
            self.save_todus_version(TODUS_VERSION)
        self.user_agent_edit.setEnabled(change)
        SETTINGS.setValue("change_ua", change)

    def connect_adb_mode(self, i):
        if not i:
            self.tipo_conex_adb.setPixmap(QtGui.QPixmap("recursos/recursos/data_usb.png"))
        else:
            self.tipo_conex_adb.setPixmap(QtGui.QPixmap("recursos/recursos/wifi.png"))

    # >---------------------------------------------------------------------------------------------------------<#
    def guardar_opciones(self):
        try:
            phone_number = self.phone_number.value()
            SETTINGS.setValue("phone_number", f"53{phone_number}")
            # ---------------------------------------------------------#
            paquete_todus = self.paquete_todus.currentText().strip()
            SETTINGS.setValue("paquete_todus", paquete_todus)
            # ---------------------------------------------------------#
            auth = self.auth.text().strip()
            if auth:
                SETTINGS.setValue("token", auth)
            # ---------------------------------------------------------#
            change_ua = self.version_todus.isChecked()
            SETTINGS.setValue("change_ua", change_ua)
            # ---------------------------------------------------------#
            if change_ua:
                user_agent = self.user_agent_edit.text().strip()
                if user_agent:
                    SETTINGS.setValue("todus_version", user_agent)
            # ---------------------------------------------------------#
            download_dir = self.dir_carpeta_descargas.text().strip()
            if download_dir:
                SETTINGS.setValue("download_dir", download_dir)
            # ---------------------------------------------------------#
            bajar_misma_carpeta = self.bajar_misma_carpeta.isChecked()
            SETTINGS.setValue("bajar_misma_carpeta", bajar_misma_carpeta)
            # ---------------------------------------------------------#
            alerta_fin_descarga = self.alerta_fin_descarga.isChecked()
            SETTINGS.setValue("alerta_fin_descarga", alerta_fin_descarga)
            # ---------------------------------------------------------#
            sonido_dir = self.sonido_dir.text()
            if sonido_dir:
                SETTINGS.setValue("sonido_dir", sonido_dir)
            # ---------------------------------------------------------#
            eliminar_txt_links = self.eliminar_txt_links.isChecked()
            SETTINGS.setValue("eliminar_txt_links", eliminar_txt_links)
            # ---------------------------------------------------------#
            inciar_automaticamente = self.inciar_automaticamente.isChecked()
            SETTINGS.setValue("inciar_automaticamente", inciar_automaticamente)
            # ---------------------------------------------------------#
            max_descargas = self.max_descargas.value()
            SETTINGS.setValue("max_descargas", max_descargas)
            # ---------------------------------------------------------#
            cant_intentos = self.cant_intentos.value()
            SETTINGS.setValue("cant_intentos", cant_intentos)
            # ---------------------------------------------------------#
            already_exists = self.already_exists.currentIndex()
            SETTINGS.setValue("already_exists", already_exists)
            # ---------------------------------------------------------#
            show_f_window = self.show_f_window.isChecked()
            SETTINGS.setValue("show_f_window", show_f_window)
            # ---------------------------------------------------------#
            android_ip = self.android_ip_values
            SETTINGS.setValue("android_ip", android_ip)
            # ---------------------------------------------------------#
            accion_detener_descargas = self.accion_detener_descargas.currentIndex()
            SETTINGS.setValue("accion_detener_descargas", accion_detener_descargas)
            # ---------------------------------------------------------#
            auto_scroll = self.auto_scroll.isChecked()
            SETTINGS.setValue("auto_scroll", auto_scroll)
            # ---------------------------------------------------------#
            # ---------------------------------------------------------#
            SETTINGS.sync()
        except Exception as e:
            self.error("[Error] Guardando configuración", e.args)
            SENT_TO_LOG(f"Guardando configuración {e.args}")

    def extraer_internal_db_token(self):
        self.parent.estado_actual("Extrayendo BD...")
        print("Extrayendo BD...")
        paquete_todus = self.paquete_todus.currentText().strip()
        if paquete_todus:
            splash = QSplashScreen(QtGui.QPixmap("recursos/cargando.png"))
            splash.show()
            try:
                for ext in ("", "-shm", "-wal"):
                    result = subprocess.run(
                        f'adb/adb.exe shell cp /data/data/{paquete_todus}/databases/internal.db{ext} /storage/self/primary/internal.db{ext}',
                        stdout=subprocess.PIPE)
                    if "No such file or directory" in result.stdout.decode("utf-8"):
                        raise Exception(f"No se encontró el paquete {paquete_todus} del toDus clonado")
                    subprocess.run(
                        f'adb/adb.exe pull /storage/self/primary/internal.db{ext} {APP_DATA}\internal.db{ext}', stdout=subprocess.PIPE)
                    subprocess.run(
                        f'adb/adb.exe shell rm /storage/self/primary/internal.db{ext}', stdout=subprocess.PIPE)
                self.parent.estado_actual("Listo!")
                dir = f"{APP_DATA}/internal.db"
                if os.path.exists(dir):
                    conex = sqlite3.connect(dir)
                    cur = conex.cursor()
                    cur.execute("SELECT credential FROM owner")
                    data = cur.fetchone()
                    if data:
                        data = data[0].split(",")[2]
                        token = data.replace("\"", "")
                        token = token.split(":")[1]
                        self.auth.setText(token)
            except Exception as e:
                print("ERROR EXTRAYENDO BD: ", end="")
                print(e.args)
                self.error("Extrayendo DB: ", e.args)
                SENT_TO_LOG(f"Extrayendo DB {e.args}")
            splash.finish(self)

    @property
    def android_ip_values(self):
        ip = self.android_ip.text().strip()
        if ip.replace(".", "") != "":
            nums = ip.split(".")
            for n in range(len(nums)):
                if len(nums[n]) == 0:
                    raise Exception ('Llene correctamente la dirección IP')
            ip = ".".join([i.strip() for i in nums])
        return ip

    @android_ip_values.setter
    def android_ip_values(self, value):
        self.android_ip.setText(value)

    def adb_get_devices_papu(self):
        splash = QSplashScreen(QtGui.QPixmap("recursos/cargando.png"))
        splash.show()
        try:
            type = self.adb_connect_by.currentIndex()
            if type:
                ip = self.android_ip_values
                try:
                    waiting_for = subprocess.run('adb/adb.exe wait-for-device', stdout=subprocess.PIPE, timeout=5)
                    if int(waiting_for.returncode):
                        self.parent.estado_actual("* El dispositivo no respondió *")
                        return
                except:
                    pass
                wifi = subprocess.run('adb/adb.exe tcpip 5555', stdout=subprocess.PIPE)
                self.parent.estado_actual(f"ADB {wifi.stdout.decode('utf-8')}")
                print(wifi)
                #ip = subprocess.run('adb/adb.exe shell ifconfig tiwlan0', stdout=subprocess.PIPE)
                #print(ip)
                wifi = subprocess.run(f'adb/adb.exe connect {ip}', stdout=subprocess.PIPE)
                self.parent.estado_actual(f"ADB {wifi.stdout.decode('utf-8')}")
                print(wifi)
                devices = subprocess.run('adb/adb.exe devices -l', stdout=subprocess.PIPE)
                self.parent.estado_actual(f"ADB {devices.stdout.decode('utf-8').strip()}")
            else:
                devices = subprocess.run('adb/adb.exe devices -l', stdout=subprocess.PIPE)
                self.parent.estado_actual(f"ADB {devices.stdout.decode('utf-8').strip()}")
            print(devices)
        except Exception as e:
            print("Conectando por ADB ", end="")
            print(e.args)
            self.error("Conectando por ADB ", e.args)
            SENT_TO_LOG(f"Conectando por ADB {e.args}")
        splash.finish(self)

    def cargar_config(self):
        try:
            paquete_todus = SETTINGS.value("paquete_todus")
            self.paquete_todus.setCurrentIndex(self.paquete_todus.findText(paquete_todus))
            # ---------------------------------------------------------#
            phone = SETTINGS.value("phone_number", type=str)[2:]
            if phone:
                self.phone_number.setValue(int(phone))
            # ---------------------------------------------------------#
            act_token = SETTINGS.value("activation_token", type=str)
            if act_token:
                self.act_token.setValue(int(act_token))
            # ---------------------------------------------------------#
            uid = SETTINGS.value("uid", type=str)
            self.uid_input.setText(uid)
            # ---------------------------------------------------------#
            passw = SETTINGS.value("password", type=str)
            self.passw_input.setText(passw)
            # ---------------------------------------------------------#
            auth = SETTINGS.value("token", type=str)
            self.auth.setText(auth)
            JWP_AUTH(auth)
            # ---------------------------------------------------------#
            change_ua = SETTINGS.value("change_ua", type=bool)
            self.version_todus.setChecked(change_ua)
            self.change_user_agent()
            # ---------------------------------------------------------#
            user_agent = SETTINGS.value("todus_version", type=str)
            if user_agent:
                self.user_agent_edit.setText(user_agent)
            # ---------------------------------------------------------#
            # ---------------------------------------------------------#
            self.dir_carpeta_descargas.setText(SETTINGS.value("download_dir", type=str))
            # ---------------------------------------------------------#
            self.bajar_misma_carpeta.setChecked(SETTINGS.value("bajar_misma_carpeta", type=bool))
            # ---------------------------------------------------------#
            self.alerta_fin_descarga.setChecked(SETTINGS.value("alerta_fin_descarga", type=bool))
            # ---------------------------------------------------------#
            self.sonido_dir.setText(str(SETTINGS.value("sonido_dir", type=str)))
            # ---------------------------------------------------------#
            self.eliminar_txt_links.setChecked(SETTINGS.value("eliminar_txt_links", type=bool))
            # ---------------------------------------------------------#
            self.inciar_automaticamente.setChecked(SETTINGS.value("inciar_automaticamente", type=bool))
            # ---------------------------------------------------------#
            self.max_descargas.setValue(int(SETTINGS.value("max_descargas", type=int)))
            # ---------------------------------------------------------#
            self.cant_intentos.setValue(int(SETTINGS.value("cant_intentos", type=int)))
            # ---------------------------------------------------------#
            self.already_exists.setCurrentIndex(int(SETTINGS.value("already_exists", type=int)))
            # ---------------------------------------------------------#
            show_f_window = SETTINGS.value("show_f_window", type=bool)
            self.show_f_window.setChecked(show_f_window)
            # ---------------------------------------------------------#
            android_ip = SETTINGS.value("android_ip", type=str)
            self.android_ip_values = android_ip
            # ---------------------------------------------------------#
            accion_detener_descargas = SETTINGS.value("accion_detener_descargas", type=int)
            self.accion_detener_descargas.setCurrentIndex(accion_detener_descargas)
            # ---------------------------------------------------------#
            auto_scroll = SETTINGS.value("auto_scroll", type=bool)
            self.auto_scroll.setChecked(auto_scroll)
            # ---------------------------------------------------------#
        except Exception as e:
            print(e.args)
            self.error("[Error] Cargando configuración", e.args)
            SENT_TO_LOG(f"Cargando configuración {e.args}")

    def error(self, place, text):
        self.parent.estado_actual("Error!")
        msg = QMessageBox()
        msg.setStyleSheet(DARK_STYLE)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Error")
        msg.setText("Ha ocurrido un error!")
        msg.setInformativeText(f"-> {place}")
        msg.setDetailedText(str(text))
        msg.exec_()
# >---------------------------------------------------------------------------------------------------------------------<
class AuthInfo(QDialog):
    def __init__(self, valores):
        QDialog.__init__(self)
        self.setObjectName("Dialog")
        self.resize(480, 100)
        self.setMinimumSize(QtCore.QSize(480, 100))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("recursos/Emoji Objects-54.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)
        self.setStyleSheet(DARK_STYLE)
        self.setModal(True)
        self.gridLayout = QtWidgets.QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")
        self.lista = QtWidgets.QListWidget(self)
        self.lista.setStyleSheet("font: 75 14pt \"MS Shell Dlg 2\";")
        self.lista.setWordWrap(True)
        self.lista.setObjectName("lista")
        item = QtWidgets.QListWidgetItem()
        self.lista.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.lista.addItem(item)
        self.gridLayout.addWidget(self.lista, 0, 0, 1, 1)
        self.retranslateUi()
        QtCore.QMetaObject.connectSlotsByName(self)
        self.init(valores)

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Dialog", "Información de la autorización"))
        __sortingEnabled = self.lista.isSortingEnabled()
        self.lista.setSortingEnabled(False)
        item = self.lista.item(0)
        item.setText(_translate("Dialog", "Usuario:"))
        item = self.lista.item(1)
        item.setText(_translate("Dialog", "Expiración:"))
        self.lista.setSortingEnabled(__sortingEnabled)

    def init(self, valores):
        header = []
        for i in range(len(valores)):
            header.append(self.lista.item(i).text())
        self.lista.clear()
        for i in range(len(valores)):
            self.lista.addItem(f"{header[i]} {valores[i]}")