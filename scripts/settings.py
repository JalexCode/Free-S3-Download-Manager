# user_agent_edit
from PyQt5.QtCore import QSettings
import os
from scripts.constants import APP_ID, USER_PATH
from scripts.logger import SENT_TO_LOG

TODUS_VERSION = "0.39.4"
USER_AGENT = "ToDus %s HTTP-Download"
DEFAULT_SETTINGS = {"paquete_todus":"", "token": "", "download_dir": f"{os.path.join(USER_PATH, 'downloads/Free S3 Download Manager')}", "bajar_misma_carpeta": True,
          "alerta_fin_descarga": True, "sonido_dir": f"{os.getcwd()}/sounds/LULLABY.WAV","eliminar_txt_links": False,
          "inciar_automaticamente": False, "max_descargas":10, "todus_version":TODUS_VERSION,
          "change_ua":False,"txt_dir":f"{os.path.join(USER_PATH, 'downloads/')}", "cant_intentos":5, "already_exists":0,
          "show_f_window":True, "android_ip":"", "accion_detener_descargas":0,
        "auto_scroll":False, "phone_number":"", "uid":"", "password":"", "activation_token":"", "profile_nick":"",
        "profile_description":"", "profile_image":"", "succesfully_token_request":True}
SETTINGS = QSettings(APP_ID, "settings")
try:
    for key in DEFAULT_SETTINGS.keys():
        if SETTINGS.value(key) is None:
            SETTINGS.setValue(key, DEFAULT_SETTINGS[key])
    SETTINGS.sync()
except Exception as e:
    print("ERROR REESTABLECIENDO CONFIGURACION")
    SENT_TO_LOG(f"ERROR REESTABLECIENDO CONFIGURACION {e.args}")