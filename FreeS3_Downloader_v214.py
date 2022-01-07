import pickle
import subprocess

import certifi
import psutil
import sqlite3
from datetime import date, datetime

import requests

from PyQt5 import uic, QtGui, QtWidgets
from PyQt5.QtGui import QPixmap, QIcon

from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QDialog, QSplashScreen, QInputDialog, QMenu, \
    QAction, QTableWidgetItem, QLabel, QApplication
from PyQt5.QtCore import Qt, QTime, QTimer, QEvent
from sys import argv

import threading
from scripts.constants import *

# >---------------------------------------------------------------------------------------------------------------<
from scripts.downloader import Descarga, DescargarThread
from scripts.logger import SENT_TO_LOG
from scripts.preferences import Preferencias
from scripts.profile_info import Perfil
from scripts.qcustom_list_widget import QCustomListWidget, QModernListWidgetItem, Spinner
from scripts.settings import SETTINGS, USER_AGENT
from scripts.utils import *

os.environ["SSL_CERT_FILE"] = certifi.where()
if not os.path.exists(APP_DATA):
    os.makedirs(APP_DATA)
# > ------------------------------------------------------------------------------------------------------------------
from PyQt5 import QtCore
# >---------------------------------------------------------------------------------------------------------------------<
class MainApp(QMainWindow):#Ui_MainWindow, QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self)
        uic.loadUi("recursos/main_v214.ui", self)
        #self.setupUi(self)
        #self.comprobar_instancias()
        self.setWindowTitle(APP_NAME)
        self.estado = QLabel("!Bienvenido a FS3 Downloader!")#QPlainTextEdit("Esperando operación")#QLabel("Esperando operación")
        info = QLabel(f'Programado y diseñado por {AUTHOR}')
        info.setStyleSheet('font: bold 10pt "MS Shell Dlg 2"')
        self.statusbar.addWidget(self.estado)
        self.statusbar.addPermanentWidget(info)
        #insertar lista de descargas
        self.insertar_lista()
        # vars
        self.links_seleccionados = []
        self.elementos = []
        self.const_autenticado = False
        #
        self.tam_total = 0
        self.velocidad_total = []
        self.archivos_descargados = 0
        self.obtener_espacio_libre()
        #
        self.txt_enlace = []
        self.detenido = False
        self.descargando = False
        # timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.tiempo_transcurrido_timer)
        self.time = QTime(0, 0, 0)
        # shuw
        self.show()
        #
        self.Start_Thread = None
        self.lista_hilos = []
        #
        self.f_w = Ventana_Flotante(self)
        self.settings_w = Preferencias(self)
        # conexiones
        self.conexiones()

    def comprobar_instancias(self):
        for process in psutil.process_iter():
            if process.name() == "FreeS3_Downloader_v213.exe":
                QMessageBox.critical(self, "Error", "Solo puede haber una instancia del programa en ejecución")
                QApplication.instance().quit()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() == Qt.WindowState.WindowMinimized or event.oldState() == Qt.WindowState.WindowMaximized:
                self.show_floating_window()
            elif event.oldState() == Qt.WindowState.WindowMinimized:
                self.f_w.hide()

    def show_floating_window(self):
        if SETTINGS.value("show_f_window", type=bool):
            self.f_w.showNormal()

    def insertar_lista(self):
        self.lista_descargas = QCustomListWidget(QModernListWidgetItem, [])
        self.contenedor.addWidget(self.lista_descargas, 0, 0, 1, 1)

    def conexiones(self):
        self.save_list.triggered.connect(self.guardar_queue)
        self.load_list.triggered.connect(self.cargar_queue)
        self.buscar_txt_btn.clicked.connect(self.buscar_txt)
        self.iniciar_btn.clicked.connect(self.toggle_play_pause)
        self.detener_btn.clicked.connect(self.detener_totalmente_descargas)
        self.settings_trigger.triggered.connect(self.settings_w.show)
        self.add_link.clicked.connect(self.annadir_enlace)
        self.actionAcerca_de.triggered.connect(self.acerca_de)
        self.cargar_datos_perfil.triggered.connect(self.extraer_datos_del_perfil)
        self.eliminar_seleccionados.clicked.connect(self.eliminar_elementos_seleccionados)
        self.eliminar_todo.clicked.connect(self.limpiar_lista)
        self.profile_img.clicked.connect(self.mostrar_perfil)
        self.lista_descargas.itemDoubleClicked.connect(self.abrir_descargado)
        self.open_d_folder.clicked.connect(self.abrir_carpeta_destino)
        self.lista_descargas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista_descargas.customContextMenuRequested.connect(self.menu_contextual)
        self.lista_descargas.itemClicked.connect(self.mostrar_link)
        self.vaciar_informe.triggered.connect(self.cleanTable)
        self.ordenar_por_nombre.triggered.connect(self.sort_list)
        self.actionExportar.triggered.connect(self.export_informe)

    def mostrar_link(self):
        i = self.lista_descargas.currentRow()
        if i != -1:
            link = self.elementos[i].link
            self.estado_actual(link)
        else:
            self.estado_actual("")

    def sort_list(self):
        if not self.descargando:
            self.estado_actual("Ordenando lista...")
            self.elementos = sorted(self.elementos, key=lambda descarga: descarga.nombre_archivo)
            self.llenar_cola()
            self.estado_actual("Listo!")

    def export_informe(self):
        archivo, _ = QFileDialog.getSaveFileName(self, "Guardar informe", "", "Archivo de texto (*.txt)")
        if archivo:
            txt = "========= Free S3 Download Manager v2.1.3 =========\n\n"
            if self.informe_lista.rowCount():
                for i in range(self.informe_lista.rowCount()):
                    txt += f"{self.informe_lista.item(i, 0).text()} | {self.informe_lista.item(i, 1).text()} | {self.informe_lista.item(i, 2).text()} > {self.informe_lista.item(i, 3).text()}\n"
                with open(archivo, mode="w", encoding="UTF-8") as txt_file:
                    txt_file.write(txt)

    def cleanTable(self):
        while self.informe_lista.rowCount () > 0:
            self.informe_lista.removeRow (0)

    def guardar_queue(self):
        try:
            if self.elementos:
                archivo, _ = QFileDialog.getSaveFileName(self, "Guardar lista de descarga", "", "Lista de descarga (*.fs3dm)")
                if archivo:
                    enlaces = [(descarga.link, descarga.nombre_archivo, descarga.txt) for descarga in self.elementos]
                    with open(archivo, "wb") as f:
                        pickle.dump(enlaces, f)
        except Exception as e:
            SENT_TO_LOG(f"Guardando lista de descarga {str(e.args)}")
            self.error("Guardando lista de descarga", e.args)

    def cargar_queue(self):
        try:
            archivo, _ = QFileDialog.getOpenFileName(self, "Cargar lista de descarga", "", "Lista de descarga (*.fs3dm)")
            if archivo:
                with open(archivo, "rb") as f:
                    enlaces = pickle.load(f)
                    for descarga in enlaces:
                        d = Descarga(*descarga)
                        self.elementos.append(d)
                    self.llenar_cola()
        except Exception as e:
           SENT_TO_LOG(f"Cargando lista de descarga {str(e.args)}")
           self.error("Cargando lista de descarga", e.args)

    def abrir_carpeta_destino(self):
        try:
            carpeta = SETTINGS.value("download_dir", type=str)
            self.abrir_descargado(carpeta, True, False)
        except Exception as e:
            self.error("Abriendo carpeta de descargas", e.args)
            SENT_TO_LOG(f"Abriendo carpeta de descargas {e.args}")

    def menu_contextual(self, posicion):
        try:
            indice = self.lista_descargas.currentRow()
            if indice != -1:
                menu = QMenu()
                abrir_ex = QAction("Seleccionar archivo en Explorer", menu)
                #abrir_explorer.setData(indice)
                def abrir_explorer():
                    self.abrir_descargado("", False, True)
                abrir_ex.triggered.connect(abrir_explorer)
                menu.addAction(abrir_ex)
                abrir = QAction("Eliminar archivo", menu)
                # abrir_explorer.setData(indice)
                def abrir_archivo():
                    item = self.elementos[indice]
                    file_path = os.path.join(item.dir_descarga, item.txt, item.nombre_archivo)
                    file_path = file_path.replace("/", "\\")
                    if os.path.exists(file_path):
                        q = QMessageBox.question(self, "Borrar archivo del disco duro", f"¿Realmente desea eliminar el archivo?", QMessageBox.Yes | QMessageBox.No)
                        if q == QMessageBox.Yes:
                            os.remove(file_path)
                abrir.triggered.connect(abrir_archivo)
                menu.addAction(abrir)
                menu.exec(self.lista_descargas.viewport().mapToGlobal(posicion))
        except Exception as e:
            self.error("Mostrando menú conceptual", e.args)
            SENT_TO_LOG(f"Mostrando menú conceptual {e.args}")

    def limpiar_lista(self):
        if len(self.elementos):
            self.tam_total = 0
            self.archivos_descargados = 0
            self.elementos.clear()
            self.lista_descargas.clear()
            self.reiniciar_elementos_ui(True)
        else:
            self.estado_actual("No hay elementos que eliminar")

    def mostrar_perfil(self):
        img = SETTINGS.value("profile_image")
        nick = SETTINGS.value("profile_nick")
        descrip = SETTINGS.value("profile_description")
        self.extraer_datos_del_perfil()
        if not nick and not descrip:
            return
        self.detalles_perfil = Perfil(img, nick, descrip, self)
        self.detalles_perfil.show()

############ CONFIGURACIONES ###########################
    def alertar_descargado(self):
        sonido = SETTINGS.value("sonido_dir", type=str)
        if os.path.exists(sonido):
            sonido_thread = ReproducirSonido()
            thread = threading.Thread(target=sonido_thread.run, args=(sonido,))
            thread.start()

    def abrir_descargado(self, file_path, folder=False, highlight=False):
        try:
            CREATE_NO_WINDOW = 0x08000000
            if folder:
                file_path = file_path.replace("/", "\\")
                subprocess.Popen(['explorer.exe', file_path],
                                 stderr=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stdin=subprocess.PIPE,
                                 shell=False,
                                 creationflags=CREATE_NO_WINDOW)
            else:
                i = self.lista_descargas.currentRow()
                if i != -1:
                    item = self.elementos[i]
                    file_path = os.path.join(item.dir_descarga, item.txt, item.nombre_archivo)
                    file_path = file_path.replace("/", "\\")
                    if highlight:
                        subprocess.Popen(['explorer.exe', '/select,', file_path],
                                         stderr=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stdin=subprocess.PIPE,
                                         shell=False,
                                         creationflags=CREATE_NO_WINDOW)

                    else:
                        subprocess.Popen(['cmd', '/C', 'start', file_path, file_path],
                                         stderr=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stdin=subprocess.PIPE,
                                         shell=False,
                                         creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            self.error("Abriendo archivo descargado", e.args)
            SENT_TO_LOG(f"Abriendo archivo descargado {e.args}")

    def eliminar_elementos_seleccionados(self):
        # lista con indices seleccionados
        listItems = self.lista_descargas.selectedIndexes()#selectedItems()
        # si no hay nada termino la funcion
        if not listItems: return
        # ordeno descendente
        listItems.sort(key=lambda item: item.row(), reverse=True)
        a = QMessageBox.warning(self, "Eliminar links seleccionados",
                                "¿Realmente desea eliminar los links seleccionados de la lista?",
                                QMessageBox.Ok | QMessageBox.Cancel)
        if a == QMessageBox.Ok:
            # elimino de la lista
            del_size = 0
            for i in listItems:
                del_size += self.elementos[i.row()].content_size
            for i in listItems:
                print(i.row())
                self.elementos.pop(i.row())
            # descuento el tamanno de los objetos eliminados del total a descargar
            print(f"{self.tam_total} - {del_size}")
            self.tam_total -= del_size
            # actualizo los elementos visuales
            self.progreso_total_bar.setFormat(f"{self.archivos_descargados}/{len(self.elementos)}")
            self.tam_total_descarga.setText(f"Tamaño total: {nz(self.tam_total)}")
            # elimino del QListWidget
            for item in listItems:
                row = item.row()
                self.lista_descargas.takeItem(row)
            # actualizo los indices de la lista y los items del QListWidget
            for i in range(len(self.elementos)):
                self.elementos[i].idx = i
                self.lista_descargas.set_item_idx(i, i)

    def buscar_txt(self):
        location, _ = QFileDialog.getOpenFileNames(self, "Seleccione archivos de texto", SETTINGS.value("txt_dir", type=str), "TXT (*.txt)")
        if location:
            # guardar dir
            SETTINGS.setValue("txt_dir", os.path.split(location[0])[0])
            self.txt_enlace = location
            # ---------------------------------------------------------#
            # llenar la lista
            self.analizar_txt()

    def analizar_txt(self):
        try:
            for file in self.txt_enlace:
                dir_descarga = SETTINGS.value('download_dir', type=str)
                # opciones
                nombre_txt = os.path.split(file)[-1][:-4].strip()
                import re
                nombre_txt = re.sub('[\"\\\></?]+', '', nombre_txt)
                if SETTINGS.value("bajar_misma_carpeta", type=bool):
                    dir_descarga += "/" + nombre_txt
                # TXT
                if os.path.exists(file):
                    with open(file, "r", encoding="UTF-8") as f:
                        contenido = f.readlines()
                        if "\n" in contenido: contenido.remove("\n")
                        if contenido:
                            for i in range(len(contenido)):
                                linea = contenido[i]
                                if "https://s3.todus.cu" in linea:
                                    link, archivo = linea.split("?" if "?" in linea else "\t")
                                    try:
                                        archivo = archivo.replace("=", ".")
                                    except:
                                        pass
                                    archivo = archivo.replace("\n", "")
                                    descarga = Descarga(link, archivo, nombre_txt)
                                    descarga.set_idx(len(self.elementos))
                                    self.annadir_descarga(descarga)
                                    tam_total = descarga.content_size
                                    progreso = (i + 1) * 100 // len(contenido)
                                    self.progreso_lectura(progreso, archivo, tam_total)
            self.fin_analisis_txt()
        except Exception as e:
            print("ERROR ANALIZANDO TXT: ", end="")
            print(e)
            #self.error("Analizando TXT", e.args)
            SENT_TO_LOG(f"Analizando TXT {e.args}")

    def fin_analisis_txt(self):
        self.progreso_total_bar.setValue(0)
        self.progreso_total_bar.setFormat(f"0/{len(self.elementos)}")
        #self.llenar_cola()
        if SETTINGS.value("inciar_automaticamente", type=bool):
            self.iniciar_descarga_thread()

    def progreso_lectura(self, progreso, archivo, tam_total):
        # asignacion
        self.tam_total += tam_total
        # visual
        self.tam_total_descarga.setText(f"Tamaño total: {nz(self.tam_total)}")
        self.estado_actual(f"Cargando TXT {progreso}%")
        if progreso == 100:
            self.obtener_espacio_libre()
            self.estado_actual("Listo!")

    def obtener_espacio_libre(self):
        #return
        tam_total = self.tam_total
        path = SETTINGS.value("download_dir", type=str)
        drive = os.path.splitdrive(path)[0]
        # print(drive)
        disk_usage = psutil.disk_usage(drive)
        # print("Espacio total: {:.2f} GB.".format(to_gb(disk_usage.total)))
        # print("Espacio libre: {:.2f} GB.".format(to_gb(disk_usage.free)))
        # print("Espacio usado: {:.2f} GB.".format(to_gb(disk_usage.used)))
        # print("Porcentaje de espacio usado: {}%.".format(disk_usage.percent))
        libre = disk_usage.free
        self.espacio_disponible.setText(f"Espacio disponible: {nz(libre)}")
        self.espacio_disponible.setStyleSheet("color:lightgreen;")
        if tam_total >= libre:
            self.espacio_disponible.setStyleSheet("color:red;")

    def annadir_descarga(self, descarga):
        if not descarga in self.elementos:
            self.elementos.append(descarga)
            self.add_i(descarga)

    def annadir_enlace(self):
        try:
            url_, _ = QInputDialog.getMultiLineText(self, "Añadir enlaces", "Escriba los enlaces. Para añadir varios sepárelos con un salto de línea (Presionando Enter)")
            if url_ and _:
                url_ += "\n"
                urls = url_.split("\n")
                for url in urls:
                    if "https://s3.todus.cu" in url:
                        link, archivo = url.split("?" if "?" in url else "\t")
                        archivo = archivo.replace("=", ".")
                        d = Descarga(link, archivo, "")
                        d.set_idx(len(self.elementos))
                        self.annadir_descarga(d)
        except Exception as e:
            print("[Error] " + str(e.args))
            SENT_TO_LOG(f"Anadiendo enlace {e.args}")

    def add_i(self, descarga):
        item = QModernListWidgetItem(self, descarga.nombre_archivo)
        item.i = len(self.elementos)
        f_t = file_type(descarga.nombre_archivo)
        item.change_status(f_t)
        item.set_info(f"{nz(descarga.content_size) if descarga.content_size else 'Esperando...'}")
        self.lista_descargas.add_item(item)
        if descarga.errores:
            item.change_status(EstadoDescarga.NO_ENCONTRADO)
            item.set_error(f"{descarga.errores[0]}")

    def llenar_cola(self):
        self.lista_descargas.clear()
        for descarga in self.elementos:
            self.add_i(descarga)

    def estado_actual(self, txt):
        self.estado.setText(txt)#setPlainText(txt)

    def extraer_datos_del_perfil(self):
        self.estado_actual("Cargando datos del perfil...")
        print("Cargando datos del perfi...")
        # perfil
        img = ""
        nombre = "Sin datos"
        dir = f"{APP_DATA}/internal.db"
        if os.path.exists(dir):
            try:
                conex = sqlite3.connect(dir)
                cur = conex.cursor()
                cur.execute("SELECT photoUrl FROM owner")
                img = cur.fetchone()[0]
                cur.execute("SELECT displayName FROM owner")
                nombre = cur.fetchone()[0]
                cur.execute("SELECT info FROM owner")
                info = cur.fetchone()[0]
                # registro papu
                SETTINGS.setValue("profile_nick", nombre)
                SETTINGS.setValue("profile_description", info)
            except Exception as e:
                self.error("Extrayendo datos del perfil ", e.args)
                SENT_TO_LOG(f"Extrayendo datos del perfil {e.args}")
            #
            splash = QSplashScreen(QPixmap("recursos/cargando.png"))
            splash.show()
            # cargar perfil
            pixmap = QPixmap("recursos/default_user.png")
            try:
                if img:
                    todus_version = SETTINGS.value("todus_version", type=str)
                    headers = {"User-Agent":USER_AGENT%todus_version, "Authorization": f"Bearer {SETTINGS.value('token', type=str)}"}
                    img_remota = requests.get(img, headers=headers, stream=True, verify=False)
                    if img_remota.status_code == 200:
                        with open(f"{APP_DATA}/img", "wb") as i:
                            i.write(img_remota.content)
                            SETTINGS.setValue("profile_img", f"{APP_DATA}/img")
                            SETTINGS.sync()
                        pixmap = QPixmap(f"{APP_DATA}/img")
                        if pixmap.width() > 60 or pixmap.height() > 60:
                            pixmap = pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.profile_name.setText(nombre)
                self.profile_img.setIcon(QIcon(pixmap))
                #
                # actualizar estadod e la red
                self.estado_actual("Listo!")
            except Exception as e:
                print("Descargando imagen de perfil", end="")
                self.error("Descargando imagen de perfil", e.args)
                self.estado_actual(f"* No se pudo descargar la imagen de perfil *")
            splash.finish(self)
        else:
            self.estado_actual("Listo!")

    def estado_descarga(self, i, estado, txt=""):
        total_percent = self.archivos_descargados * 100 // len(self.elementos)
        if estado.name == "DESCARGADO":
            self.archivos_descargados += 1
            self.progreso_total_bar.setValue(total_percent)
            self.progreso_total_bar.setFormat(f"%p% [{self.archivos_descargados}/{len(self.elementos)}]")
            self.obtener_espacio_libre()
        self.f_w.estado_descarga(total_percent, self.tam_total, self.archivos_descargados, len(self.elementos))
        self.lista_descargas.set_state(i, estado, txt)

    def add_informe(self, tupla):
        i = self.informe_lista.rowCount()
        self.informe_lista.insertRow (i)
        for n in range(len(tupla)):
            txt = str(tupla[n])
            self.informe_lista.setItem (i, n, QTableWidgetItem(txt))

    def toggle_play_pause(self):
        # isChecked == True ---> Inicio de descarga (Play)
        if self.iniciar_btn.isChecked():
            # si hay elementos en la lista
            if self.elementos:
                # cambio el icono del boton de Iniciar/Pausar
                self.iniciar_btn.setIcon(QIcon("recursos/pause.png"))#
                # limpio progreso
                if not self.tam_total:
                    self.clear_progress()
                # inicio descarga
                self.iniciar_descarga_thread()
            # si no hay, pues nada que hacer
            else:
                self.iniciar_btn.setChecked(False)
                self.estado_actual("* Lista vacía *")
        # isChecked == False ---> Descarga Pausada (Pause)
        else:
            # si hay elementos en la lista
            if self.elementos:
                # pausamos
                self.iniciar_btn.setIcon(QIcon("recursos/play.png"))
                self.detener_descargas()
            # si no hay, pues nada que hacer
            else:
                self.iniciar_btn.setChecked(True)
                self.estado_actual("* Lista vacía *")

    def iniciar_descarga_thread(self):
        max_workers = SETTINGS.value("max_descargas", type=int)
        # timer
        self.timer.start(1000)
        #
        self.descargando = True
        #
        reintentos = SETTINGS.value("cant_intentos", type=int)
        self.Start_Thread = DescargarThread(max_workers, reintentos, self.elementos)
        self.Start_Thread.barra_progreso.connect(self.lista_descargas.set_progress)
        self.Start_Thread.info_progreso.connect(self.lista_descargas.set_progress_info)
        self.Start_Thread.estado.connect(self.estado_descarga)
        self.Start_Thread.error.connect(self.add_informe)
        self.Start_Thread.terminado.connect(self.descargado)
        self.Start_Thread.tam_total_descarga.connect(self.update_tam_total_descarga)
        self.Start_Thread.detener_finish.connect(self.habilitar_controles)
        self.Start_Thread.current_row.connect(self.current_download)
        self.download_thread = threading.Thread(target=self.Start_Thread.run_all)
        self.download_thread.setDaemon(True)
        self.descargando = True
        self.download_thread.start()
        self.habilitar_controles(False)
        # ventana flotante
        self.f_w.cambiar_estado(EstadoDescarga.DESCARGANDO)

    def current_download(self, i):
        if SETTINGS.value("auto_scroll", type=bool):
            self.lista_descargas.setCurrentRow(i)

    def update_tam_total_descarga(self, tam):
        self.tam_total += tam
        self.tam_total_descarga.setText(f"Tamaño total: {nz(self.tam_total)}")

    def tiempo_transcurrido_timer(self):
        self.time = self.time.addSecs(1)
        self.tiempo_transcurrido.setText(f"Tiempo transcurrido: {self.time.toString('hh:mm:ss')}")
        self.f_w.tiempo_transcurrido(self.time.toString('hh:mm:ss'))

    def detener_una(self, i):
        try:
            if not self.elementos[i].detenido:
                eliminar = False
                accion_detener_descargas = SETTINGS.value("accion_detener_descargas", type=int)
                if not accion_detener_descargas:
                    q = QMessageBox.question(self, "Borrar archivo del disco duro",
                                             f"¿Desea eliminar los archivos incompletos?",
                                             QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                    if q == QMessageBox.Yes:
                        eliminar = True
                elif accion_detener_descargas == 1:
                    eliminar = True
                self.elementos[i].detenido = True
                self.elementos[i].eliminar_si_se_detiene = eliminar
                self.estado_descarga(i, EstadoDescarga.NO_DESCARGADO, "Detenido por el usuario*")
                self.tam_total -= self.elementos[i].content_size
                #self.progreso_total_bar.setFormat(f"{self.archivos_descargados}/{len(self.elementos)}")
                self.tam_total_descarga.setText(f"Tamaño total: {nz(self.tam_total)}")
                #self.estado_actual("* Descarga pausada *")
                #self.archivos_descargados += 1
        except Exception as e:
            SENT_TO_LOG(f"[Error] Deteniendo una descarga {e.args}")
            self.error("Deteniendo una descarga", e.args)

    def detener_descargas(self):
        try:
            if self.descargando:
                self.estado_actual("Pausando todo...")
                self.Start_Thread.detener_descargas()
                self.f_w.cambiar_estado(EstadoDescarga.PAUSADO)
                self.estado_actual("* Descarga pausada *")
                self.descargando = False
                self.timer.stop()
                self.habilitar_controles(True)
        except Exception as e:
            SENT_TO_LOG(f"[Error] Pausando descargas {e.args}")
            self.error("Pausando descargas", e.args)

    def detener_totalmente_descargas(self):
        try:
            if self.descargando:
                # param
                eliminar = False
                #
                accion_detener_descargas = SETTINGS.value("accion_detener_descargas", type=int)
                if not accion_detener_descargas:
                    q = QMessageBox.question(self, "Borrar archivo del disco duro", f"¿Desea eliminar los archivos incompletos?",
                                             QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                    if q == QMessageBox.Yes:
                        eliminar = True
                elif accion_detener_descargas == 1:
                    eliminar = True
                self.estado_actual("Deteniendo todo...")
                self.Start_Thread.detener_totalmente_descargas(eliminar)
                self.f_w.cambiar_estado(EstadoDescarga.NO_DESCARGADO)
                self.estado_actual("* Descarga detenida *")
                self.descargando = False
                self.timer.stop()
                self.time = QTime(0, 0, 0)
                self.habilitar_controles(True)
        except Exception as e:
            SENT_TO_LOG(f"[Error] Deteniención total {e.args}")
            self.error("Deteniendo todas las descargas", e.args)

    def habilitar_controles(self, b = True):
        self.titulo_bar.setVisible(b)
        if SETTINGS.value("show_profile_info", type=bool):
            self.profile_.setVisible(b)
        self.tools.setEnabled(b)

    def clear_progress(self):
        self.tam_total_descarga.setText(f"Tamaño total: 0.0 MB")
        self.tiempo_transcurrido.setText(f"Tiempo transcurrido: -")
        self.progreso_total_bar.setValue(0)
        self.progreso_total_bar.setFormat(f"0/{len(self.elementos)}")

    def reiniciar_elementos_ui(self, clear_progress=False):
        self.iniciar_btn.setChecked(False)
        self.habilitar_controles()
        if not clear_progress:
            self.clear_progress()

    def descargado(self):
        #
        self.iniciar_btn.setChecked(False)
        self.iniciar_btn.setIcon(QIcon("recursos/play.png"))
        # timer
        self.timer.stop()
        self.time = QTime(0, 0, 0)
        #ventana flotante
        self.f_w.cambiar_estado(EstadoDescarga.DESCARGADO)
        try:
            if SETTINGS.value("eliminar_txt_links", type=bool):
                import os
                for txt in self.txt_enlace:
                    os.remove(txt)
            if self.alerta_fin_descarga.isChecked():
                self.alertar_descargado()
        except Exception as e:
            self.add_informe(f"No se pudo eliminar el TXT [{str(e.args)}]")
        # informe
        self.add_informe((str(datetime.now())[:-7], "-", "-", f"""# Archivos descargados: {self.archivos_descargados}
{f"# Archivos no descargados: {len(self.elementos) - self.archivos_descargados}" if self.archivos_descargados != len(self.elementos) else ""}"""))
        # estado_actual
        if not self.descargando:
            self.estado_actual("!Descarga detenida por el usuario!")
        else:
            self.estado_actual("Descarga finalizada!")
            self.descargando = False
        self.reiniciar_elementos_ui()

    def error(self, place, text):
        self.estado_actual("Error!")
        msg = QMessageBox()
        msg.setStyleSheet(DARK_STYLE)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Error")
        msg.setText("Ha ocurrido un error!")
        msg.setInformativeText(f"-> {place}")
        msg.setDetailedText(str(text))
        msg.exec_()

    def acerca_de(self):
        QMessageBox.about(self, "Acerca de",
                          f"{APP_NAME}\n=============================\nDesarrollado por {AUTHOR}\nContacto > +5354655909\neMail: javierglez9910@gmail.com\nAporte de método de descarga:\n\t@EL_Garro (- Nyan -)\nAporte de método de conexión ADB:\n\t@RathHunt\nAgradecimientos a todos los testers que han participado y participan en la prueba de la app, incluyéndote.\nEspecialmente a los usuarios:\n\tRaúl Andres\n\tMi amigo de toda la vida @Christian_S_Ll\n{SUPPORT}\nActualización {VERSION} [{date.today()}]")

# >---------------------------------------------------------------------------------------------------------------------<
    def closeEvent(self, event):
        resultado = QMessageBox.question(self, "Salir de FS3DM", "¿Está seguro que desea salir?",
                                         QMessageBox.Yes | QMessageBox.No)
        if resultado == QMessageBox.Yes:
            #event.accept()
            self.f_w.close()
            QApplication.instance().quit()
        else: event.ignore()
# >---------------------------------------------------------------------------------------------------------------------<

# >---------------------------------------------------------------------------------------------------------------------<

# >---------------------------------------------------------------------------------------------------------------------<
class Ventana_Flotante(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self)
        self.parent = parent
        # INIT
        self.setObjectName("Dialog")
        self.resize(295, 110)
        self.setMinimumSize(QtCore.QSize(295, 110))
        self.setMaximumSize(QtCore.QSize(16777215, 114))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("recursos/icono.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)
        self.setWindowOpacity(1.0)
        self.setStyleSheet(DARK_STYLE)
        self.setModal(False)
        self.gridLayout_2 = QtWidgets.QGridLayout(self)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout_3 = QtWidgets.QGridLayout()
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.opacidad = QtWidgets.QSlider(self)
        self.opacidad.setMinimum(10)
        self.opacidad.setMaximum(100)
        self.opacidad.setProperty("value", 100)
        self.opacidad.setOrientation(QtCore.Qt.Horizontal)
        self.opacidad.setObjectName("opacidad")
        self.gridLayout_3.addWidget(self.opacidad, 2, 0, 1, 3)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_3.addItem(spacerItem, 1, 1, 1, 1)
        self.widget = QtWidgets.QWidget(self)
        self.widget.setObjectName("widget")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.widget)
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_5.setSpacing(0)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.play = QtWidgets.QToolButton(self.widget)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("recursos/play.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.play.setIcon(icon1)
        self.play.setObjectName("play")
        self.gridLayout_5.addWidget(self.play, 0, 0, 1, 1)
        self.pause = QtWidgets.QToolButton(self.widget)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap("recursos/pause.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pause.setIcon(icon2)
        self.pause.setObjectName("recursos/pause")
        self.gridLayout_5.addWidget(self.pause, 0, 1, 1, 1)
        self.stop = QtWidgets.QToolButton(self.widget)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap("recursos/stop.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.stop.setIcon(icon3)
        self.stop.setObjectName("stop")
        self.gridLayout_5.addWidget(self.stop, 0, 2, 1, 1)
        self.gridLayout_3.addWidget(self.widget, 1, 0, 1, 1)
        self.tiempo = QtWidgets.QLabel(self)
        self.tiempo.setObjectName("tiempo")
        self.gridLayout_3.addWidget(self.tiempo, 1, 2, 1, 1)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setContentsMargins(9, -1, -1, -1)
        self.gridLayout.setObjectName("gridLayout")
        self.estado_lbl = Spinner(EstadoDescarga.ESPERANDO.value)
        self.estado_lbl.setMinimumSize(QtCore.QSize(20, 20))
        self.estado_lbl.setMaximumSize(QtCore.QSize(20, 20))
        self.estado_lbl.setText("...")
        #self.estado_lbl.setScaledContents(True)
        self.estado_lbl.setObjectName("estado_lbl")
        self.gridLayout.addWidget(self.estado_lbl, 0, 0, 1, 1)
        self.progreso = QtWidgets.QProgressBar(self)
        self.progreso.setStyleSheet("")
        self.progreso.setProperty("value", 0)
        self.progreso.setObjectName("progreso")
        self.gridLayout.addWidget(self.progreso, 0, 1, 1, 1)
        self.gridLayout_3.addLayout(self.gridLayout, 0, 0, 1, 3)
        self.gridLayout_2.addLayout(self.gridLayout_3, 0, 0, 1, 1)
        self.control = QtWidgets.QGridLayout()
        self.control.setObjectName("control")
        self.cerrar = QtWidgets.QToolButton(self)
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap("recursos/pss_close_over.png"), QtGui.QIcon.Mode.Normal,
                        QtGui.QIcon.State.Off)
        self.cerrar.setIcon(icon4)
        self.cerrar.setAutoRaise(True)
        self.cerrar.setObjectName("cerrar")
        self.control.addWidget(self.cerrar, 1, 0, 1, 1)
        self.max = QtWidgets.QToolButton(self)
        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap("recursos/pss_maximize_nor.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.max.setIcon(icon5)
        self.max.setAutoRaise(True)
        self.max.setObjectName("max")
        self.control.addWidget(self.max, 0, 0, 1, 1)
        self.gridLayout_2.addLayout(self.control, 0, 1, 1, 1)
        self.actionSalir = QtWidgets.QAction(self)
        self.actionSalir.setObjectName("actionSalir")

        self.retranslateUi()
        self.cerrar.clicked.connect(self.close)
        QtCore.QMetaObject.connectSlotsByName(self)
        #
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowSystemMenuHint)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.pressing = False
        #####################
        self.max.clicked.connect(self.maximizarPrincipal)
        self.opacidad.valueChanged.connect(self.cambiarOpacidad)
        self.play.clicked.connect(self.parent.iniciar_descarga_thread)
        self.pause.clicked.connect(self.parent.detener_descargas)
        self.stop.clicked.connect(self.parent.detener_totalmente_descargas)
        #####################

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("self", "FreeS3 Download Manager - Ventana flotante"))
        self.opacidad.setToolTip(_translate("Dialog",
                                            "<html><head/><body><p><span style=\" font-weight:600;\">Transparencia de la ventana</span></p><p><br/></p></body></html>"))
        self.play.setToolTip(_translate("Dialog",
                                        "<html><head/><body><p><span style=\" font-weight:600;\">Iniciar/Reanudar la descarga</span></p><p>Da inicio a las descargas o las reanuda si estaban pausadas</p></body></html>"))
        self.play.setText(_translate("Dialog", "..."))
        self.pause.setToolTip(_translate("Dialog",
                                         "<html><head/><body><p><span style=\" font-weight:600;\">Pausar la descarga</span></p><p>Detiene las descargas. Puede reanudarlas luego.</p></body></html>"))
        self.pause.setText(_translate("Dialog", "..."))
        self.stop.setToolTip(_translate("Dialog",
                                        "<html><head/><body><p><span style=\" font-weight:600;\">Detener la descarga totalmente</span></p><p>Luego no podrá reanudar las descargas</p></body></html>"))
        self.stop.setText(_translate("Dialog", "..."))
        self.tiempo.setToolTip(_translate("Dialog",
                                          "<html><head/><body><p><span style=\" font-weight:600;\">Tiempo de descarga transcurrido</span></p></body></html>"))
        self.tiempo.setText(_translate("Dialog", "--:--:--"))
        self.estado_lbl.setToolTip(_translate("Dialog",
                                              "<html><head/><body><p><span style=\" font-weight:600;\">Icono de estado</span></p></body></html>"))
        self.progreso.setToolTip(_translate("Dialog",
                                            "<html><head/><body><p><span style=\" font-weight:600;\">Progreso total de descarga</span></p><p>x% -&gt; Por ciento total descargado</p><p>[x/x] -&gt; Archivos descargados/Total de archivos</p><p>[x MB] -&gt; Tamaño total de descarga</p></body></html>"))
        self.progreso.setFormat(_translate("Dialog", "%p% [0/0] [0.0MB]"))
        self.cerrar.setToolTip(_translate("Dialog", "Cerrar ventana flotante"))
        self.cerrar.setText(_translate("Dialog", "..."))
        self.max.setToolTip(_translate("Dialog", "Cambiar a la ventana principal"))
        self.max.setText(_translate("Dialog", "..."))
        self.actionSalir.setText(_translate("Dialog", "salir"))

    def cambiar_estado(self, estado):
        self.estado_lbl.set_pixmap(estado.value)
        if estado.name == "DESCARGANDO":
            self.estado_lbl.start_animation()
        else:
            self.estado_lbl.stop_animation()

    def estado_descarga(self, total_percent, tam_total, archivos_descargados, total_elementos):
        self.progreso.setFormat(f"%p% [{archivos_descargados}/{total_elementos}][{nz(tam_total)}]")
        self.progreso.setValue(total_percent)
        if archivos_descargados == total_elementos:
            self.progreso.setValue(100)

    def cambiarOpacidad(self, value):
        self.setWindowOpacity(value/100)

    def tiempo_transcurrido(self, txt):
        self.tiempo.setText(txt)

    def velocidad_red(self, up, down):
        self.subida.setText(up)
        self.bajada.setText(down)

    def ultima_actualizacion(self, t):
        self.hora_act.setText(t)

    def maximizarPrincipal(self):
        self.parent.showNormal()
        self.close()

    #def hideEvent(self, event):
        #self.parent.showNormal()
        #event.accept()

    def mousePressEvent(self, event):
        self.start = self.mapToGlobal(event.pos())
        self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing:
            self.end = self.mapToGlobal(event.pos())
            self.movement = self.end - self.start
            self.setGeometry(self.mapToGlobal(self.movement).x(),
                             self.mapToGlobal(self.movement).y(),
                             self.width(), self.height())
            self.start = self.end

    def mouseReleaseEvent(self, QMouseEvent):
        self.pressing = False
# >-------------------------------------------------------------------------------------------------------------------<

def main():
    app = QApplication(argv)
    window = MainApp()
    app.exec_()
if __name__ == '__main__':
    main()
