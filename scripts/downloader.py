import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import requests
from PyQt5.QtCore import QObject, pyqtSignal

from scripts.constants import EstadoDescarga
from scripts.logger import SENT_TO_LOG
from scripts.settings import SETTINGS, USER_AGENT
from scripts.todus import SIGN_URL
from scripts.utils import ThreadWithReturnValue, nz


class Descarga(QObject):
    def __init__(self, link, nombre_archivo, txt):
        QObject.__init__(self)
        # -------- DATOS DEL ARCHIVO -------------#
        self.link = link
        self.link_firmado = ""
        self.txt = txt
        self.nombre_archivo = nombre_archivo
        self.dir_descarga = SETTINGS.value("download_dir", type=str)
        #self.__fecha_subida = None
        # -------- PARAMS --------------#
        # indice en la lista
        self.idx = 0
        # reintentos
        self.retries = 5
        # bool para idicar si se descargoe l archivo
        self.descargado = False
        # tamanno del epdazo a descargar
        self.chunk_size = 1024#*100
        # indica que ladescarga esta pausada
        self.detenido = False
        # indica que la descarga se detuvo
        self.detenido_total = False
        # inidica si al detener la descarga se elimina el archivo incompleto
        self.eliminar_si_se_detiene = False
        # indica si la descarga es valida o no
        self.valido = True
        # lista de errores
        self.errores = []
        # hedaders de descarga
        todus_version = SETTINGS.value("todus_version", type=str)
        self.headers = {"User-Agent":USER_AGENT%todus_version, "Authorization": f"Bearer {SETTINGS.value('token', type=str)}"}
        # lo que se ha descargado del archivo
        self.descargado_archivo = 0
        # tamanno de la descarga
        self.content_size = 0
        # -----------------------------

    def set_idx(self, i):
        self.idx = i

    def signals(self, barra_progreso, info_progreso, estado, tam_total_descarga, error, current_row):
        self.barra_progreso = barra_progreso
        self.info_progreso = info_progreso
        self.estado = estado
        self.tam_total_descarga = tam_total_descarga
        self.error = error
        self.current_row = current_row

    def emit_error(self, retry, msg):
        self.error.emit((str(datetime.now())[:-7], retry, self.nombre_archivo, msg))

    def download(self):
        i = self.idx
        no_retry = 0
        # si no fue detenido totalmente, o sea, fue solo pausado
        if not self.detenido_total:
            # si el archivo aun no ha sido descargado
            if not self.descargado:
                # selecciono el elemtno actual en descarga
                self.current_row.emit(i)
                # la variable de destino final
                destino = os.path.join(self.dir_descarga,self.txt, self.nombre_archivo)
                # itero sobre los intentos configurados por el usuario
                for no_retry in range(self.retries):
                    # compruebo que no se haya deteneido la descarga
                    if self.detenido:
                        break
                    # anuncio el # del intento y cambio el estado a modo FIRMANDO
                    self.estado.emit(i, EstadoDescarga.FIRMANDO, f"Intento {no_retry+1}")
                    try:
                        # si la descarga es valida (no hay error 404 u otro contratiempo critico)
                        if self.valido:
                            # si el archivo no existe tngo que eliminar el header Range
                            if not os.path.exists(destino):
                                self.descargado_archivo = 0
                                try:
                                    self.headers.pop("Range")
                                except:
                                    pass
                            # llamo al hilo de firma de URL
                            thread = ThreadWithReturnValue(target=SIGN_URL, args=(self.link,))
                            thread.start()
                            # espero a q se ejecute y guardo el resultado aki
                            self.link_firmado = thread.join()
                            # request del archivo con la url firmada
                            from contextlib import closing
                            with closing(requests.get(
                                    url=self.link_firmado,
                                    headers=self.headers,
                                    stream=True
                            )) as response:
                                # manejo de posibles errores comunes
                                if response.status_code >= 400:
                                    msg = f"[Error] {response.status_code}"
                                    if response.status_code == 403:
                                        msg = "No se pudo firmar la URL"
                                        continue
                                    elif response.status_code == 401:
                                        msg = "Token vencido"
                                    elif response.status_code == 404:
                                        msg = "El archivo remoto no existe"
                                    self.valido = False
                                    self.errores.append(f"[Error] {msg}")
                                    self.emit_error(no_retry, msg)
                                # si sigue siendo valido
                                if self.valido:
                                    # extraigo el tamanno del archivo
                                    h = response.headers
                                    if not self.content_size:
                                        self.content_size = int(h["content-length"])
                                    # si el archivo existe
                                    if os.path.exists(destino):
                                        # saco su tamanno total
                                        file_tam = os.stat(destino).st_size
                                        # si el archivo que ya existe tiene el tamanno que le corresponde
                                        if file_tam == self.content_size:
                                            # decido que hacer por opciones
                                            s = SETTINGS.value("already_exists", type=int)
                                            # lo omito
                                            if s == 1:
                                                self.descargado = True
                                                self.estado.emit(i, EstadoDescarga.DESCARGADO, "El archivo ya existe y fue omitido")
                                                self.emit_error(no_retry, "El archivo ya existe y fue omitido")
                                                break
                                            # lo renombro
                                            elif s == 2:
                                                destino = os.path.join(self.dir_descarga, self.txt, "Copia de " + self.nombre_archivo)
                                            # si no, lo sobreescribo
                                        # a no ser, que la descarga se haya quedado incompleta
                                        if not "Range" in self.headers:
                                            # si el tamanno del archivo es menor que el del archivo remoto,
                                            # es que no se descargo bien
                                            if file_tam < self.content_size:
                                                # tonces config parametros para reanudar descarga
                                                self.headers["Range"] = f"bytes={file_tam}-{self.content_size}"
                                                self.descargado_archivo = file_tam
                                                continue
                                    # si la carpeta de destino especifico no existe
                                    folder_esp = os.path.join(self.dir_descarga, self.txt)
                                    if not os.path.exists(folder_esp):
                                        try:
                                            # pos la creo mi pana
                                            os.mkdir(folder_esp)
                                        except:
                                            self.emit_error(no_retry, "No se pudo crear el directorio contendor")
                                    # modo de escritura W por defecto
                                    modo = "wb"
                                    # si es una reanudacion, pos metodo Append
                                    if self.descargado_archivo > 0:
                                        modo = "ab"
                                    print(self.headers)
                                    # annado el tamanno del archivo remoto al totaol de la descarga
                                    self.tam_total_descarga.emit(self.content_size)
                                    # cappturo una instancia de tiempo pa calcular velocidad y tiempo aproxim
                                    t = time.time()
                                    # actualziar estado
                                    self.estado.emit(i, EstadoDescarga.DESCARGANDO, "")
                                    # creo el archivo
                                    with open(destino, modo) as file:
                                        # itero sobre el contenido
                                        for data in response.iter_content(chunk_size=self.chunk_size):
                                            # si la descarga fue detenida, detengo el ciclo y dejo el parametro Range
                                            if self.detenido:
                                                self.headers["Range"] = f"bytes={self.descargado_archivo}-{self.content_size}"
                                                break
                                            # si no hay que tirar, detenego el ciclo
                                            if not len(data):
                                                self.detenido = True
                                                break
                                            # escribo sobre el archivo
                                            file.write(data)
                                            # actualizao la var de los bytes descargados
                                            self.descargado_archivo += len(data)
                                            # capturo una instancia de tiempo
                                            demorado = time.time() - t
                                            # datos de la descarga
                                            percent = self.descargado_archivo * 100 // self.content_size
                                            speed = int(self.descargado_archivo // (demorado + 1))
                                            e_time = (self.content_size - self.descargado_archivo) / speed
                                            # sennales para actualizar interfaz
                                            self.barra_progreso.emit(i, percent)
                                            self.info_progreso.emit(i, (self.descargado_archivo, self.content_size, e_time, speed))
                                        # si se detuvo, detiene el ciclo de los reintentos
                                        if self.detenido:
                                            break
                                        # si se descargo bien
                                        if self.descargado_archivo >= self.content_size:
                                            self.descargado = True
                                            self.estado.emit(i, EstadoDescarga.DESCARGADO, f"{nz(self.content_size)} descargados en {str(timedelta(seconds=time.time()-t)).split('.')[0]}")
                                        else:
                                            # si no
                                            self.descargado = False
                                            if not self.detenido:
                                                self.estado.emit(i, EstadoDescarga.NO_DESCARGADO, f"No se descargó")
                                                self.emit_error(no_retry, f"No se descargó correctamente [{nz(self.descargado_archivo)}/{nz(self.content_size)}]")
                                else:
                                    self.estado.emit(i, EstadoDescarga.ERROR, self.errores[0])
                            break
                    except requests.RequestException as exception:
                        msg = f"[Intento {no_retry+1}] {self.nombre_archivo} -> {exception.args}"
                        self.emit_error(no_retry, str(exception.args).replace("(","").replace(")",""))
                        SENT_TO_LOG(f"Archivo {self.nombre_archivo} {exception.args}")
                        self.estado.emit(i, EstadoDescarga.ERROR, str(exception.args))
                        print(msg, file=sys.stderr)
                if not self.descargado and not self.detenido:
                    print(self.errores)
                    self.estado.emit(i, EstadoDescarga.ERROR, " • ".join(self.errores))
                elif self.detenido:
                    self.emit_error(no_retry, "Descarga pausada/detenida por el usuario")
                if self.detenido_total:
                    if self.eliminar_si_se_detiene:
                        try:
                            os.remove(os.path.join(self.dir_descarga, self.txt, self.nombre_archivo))
                        except Exception as e:
                            print(e.args)
                            self.emit_error(no_retry, "No se pudo eliminar el archivo")

    def __str__(self):
        return f"{self.nombre_archivo} {nz(self.content_size)}"

    def __eq__(self, other):
        return self.nombre_archivo == other.nombre_archivo
# >---------------------------------------------------------------------------------------------------------------------<
class DescargarThread(QObject):
    barra_progreso = pyqtSignal(int, int)
    info_progreso = pyqtSignal(int, tuple)
    estado = pyqtSignal(int, object, str)
    terminado = pyqtSignal()
    error = pyqtSignal(tuple)
    tam_total_descarga = pyqtSignal(int)
    detener_finish = pyqtSignal(bool)
    current_row = pyqtSignal(int)

    def __init__(self, max_workers, reintentos, elementos):
        QObject.__init__(self)
        self.max_workers = max_workers
        self.reintentos = reintentos
        self.errores = []
        self.elementos = elementos
        self.detener = False
        self.executor = None

    def run_all(self):
        try:
            for i in range(len(self.elementos)):
                if not self.elementos[i].descargado and not self.elementos[i].detenido_total:
                    self.estado.emit(i, EstadoDescarga.ESPERANDO, "")
            with ThreadPoolExecutor(max_workers=self.max_workers) as self.executor:
                for i in range(len(self.elementos)):
                    if self.detener:
                        break
                    #
                    if not self.elementos[i].descargado:
                        self.elementos[i].retries = self.reintentos
                        self.elementos[i].signals(self.barra_progreso, self.info_progreso, self.estado, self.tam_total_descarga, self.error, self.current_row)
                        self.elementos[i].detenido = False
                        self.executor.submit(self.elementos[i].download)
            self.terminado.emit()
        except Exception as e:
            print("HILO PRINCIPAL", end="")
            print(e.args)
            self.errores.append("ThreadPool -> " + str(e.args))
            SENT_TO_LOG(f"ThreadPool {e.args}")
        try:
            self.detener_finish.emit(True)
        except:
            pass

    def detener_descargas(self):
        try:
            print("Pausando...")
            self.detener = True
            for i in range(len(self.elementos)):
                if not self.elementos[i].descargado:
                    self.elementos[i].detenido = True
                    self.estado.emit(i, EstadoDescarga.PAUSADO, "")
        except Exception as e:
            print("Pausando todo", end="")
            self.errores.append("Pausando todo -> " + str(e.args))
            SENT_TO_LOG(f"Pausando todo {e.args}")

    def detener_totalmente_descargas(self, eliminar):
        try:
            print("Deteniendo...")
            self.detener = True
            for i in range(len(self.elementos)):
                if not self.elementos[i].descargado:
                    if eliminar:
                        self.elementos[i].eliminar_si_se_detiene = True
                    self.elementos[i].detenido_total = True
                    self.elementos[i].detenido = True
                    self.estado.emit(i, EstadoDescarga.NO_DESCARGADO, "")
        except Exception as e:
            print("Detener todo", end="")
            self.errores.append("Detener todo -> " + str(e.args))
            SENT_TO_LOG(f"Detener todo {e.args}")