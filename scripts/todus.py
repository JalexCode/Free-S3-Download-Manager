import base64
import binascii
import random

import requests
from dateutil.relativedelta import relativedelta
from jwcrypto import jwa

from scripts.logger import SENT_TO_LOG
from scripts.settings import SETTINGS

POST_HEADERS = {
  "Host": "auth.todus.cu",
  "user-agent": "ToDus 0.38.34 Auth",
  "content-type": "application/x-protobuf",
  "accept-encoding": "gzip"
}
VERSION = "21800"
def UID():
  charset = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
             "U", "V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n",
             "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "0", "1", "2", "3", "4", "5", "6", "7",
             "8", "9"]
  _uid = ""
  for i in range(150):
    _uid += charset[random.randrange(0, len(charset)-1)]
  return _uid
def REQUEST_PIN(phone):
    # PEDIR EL PIN
    uid = UID()
    data_4_PIN = f'0A0A{phone.encode("utf-8").hex()}129601{uid.encode("utf-8").hex()}'.encode("utf-8")
    data_4_PIN = binascii.unhexlify(data_4_PIN)
    # request
    a = requests.post('https://auth.todus.cu/v2/auth/users.reserve',
                      headers=POST_HEADERS, data=data_4_PIN)
    print(a.status_code, a.content)
    # compruebo q haya sido exitoso el request
    assert a.status_code == 200, f"Error solicitando PIN {a.content}"
    # guardo valores en el registro
    SETTINGS.setValue("uid", uid)
    return a.status_code, a.content
def REQUEST_PASSWORD(phone, pin):
    # CONSEGUIR EL PASSW PARA PDEIR EL TOKEN
    data_4_passw = f'0A0A{phone.encode("utf-8").hex()}129601{UID().encode("utf-8").hex()}1A06{pin.encode("utf-8").hex()}'.encode(
        "utf-8")
    data_4_passw = binascii.unhexlify(data_4_passw)
    a = requests.post('https://auth.todus.cu/v2/auth/users.register',
                      headers=POST_HEADERS, data=data_4_passw)
    print(a.status_code, a.content, a.text)
    assert a.status_code == 200, f"Error solicitando Password {a.content}"
    return a.status_code, a.content
def REQUEST_TOKEN(phone, passw):
    # PEDIR EL TOKEN
    data_4_token = f'0A0A{phone.encode("utf-8").hex()}1260{passw.encode("utf-8").hex()}1A053231383036'.encode("utf-8")
    data_4_token = binascii.unhexlify(data_4_token)
    a = requests.post('https://auth.todus.cu/v2/auth/token',
                      headers=POST_HEADERS, data=data_4_token)
    print(a.status_code, a.content)
    assert a.status_code == 200, f"Error solicitando Token {a.content}"
    return a.status_code, a.content
# >-------------------------------------------------------------------------------------------------------------------<
def JWP_AUTH(bearer):
    from datetime import datetime
    if "." in bearer and bearer.count(".") == 2:

        bearer = bearer.split(".")
        payload = bearer[1]
        payload_json = jwa.base64url_decode(payload)
        valores = []
        p = jwa.json_decode(payload_json)
        valores.append(p['username'])
        exp = datetime.fromtimestamp(p['exp'])
        #
        dif = relativedelta(datetime.now(), exp)
        dias = dif.days
        horas = dif.hours
        minutos = dif.minutes
        if datetime.now() < exp:
            falta_str = f"[faltan {dias} día(s), {horas} hora(s), {minutos} minuto(s)]"
        else:
            falta_str = "Ya venció"
        str_exp = f"{exp} {falta_str}"
        valores.append(str_exp)
        #
        SETTINGS.setValue('phone_number', p['username'])
        SETTINGS.setValue("token_expiration", p['exp'])
        return valores
    return
# >-------------------------------------------------------------------------------------------------------------------<
def AUTH_BASE64():
    auth_im_todus = chr(0) + SETTINGS.value('phone_number', type=str) + chr(0) + SETTINGS.value('token', type=str)
    auth_im_todus = bytes(auth_im_todus, encoding='utf-8')
    encoded_auth_im_todus = base64.encodebytes(auth_im_todus)
    encoded_auth_im_todus = encoded_auth_im_todus.decode('utf-8')
    return encoded_auth_im_todus
def ID_SESION():
    # ID-SESION
    charset = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
               "U", "V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n",
               "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "0", "1", "2", "3", "4", "5", "6", "7",
               "8", "9"]
    ids = ""
    for i in range(5):
        ids += charset[random.randrange(0, len(charset)-1)]
    return ids
def SIGN_URL(url):
    id_sesion = ID_SESION()
    encoded_auth_im_todus = AUTH_BASE64()
    if url:
        try:
            # SOCKET
            import socket
            from OpenSSL import SSL
            # print("= SOCKET SSL =")
            ctx = SSL.Context(SSL.SSLv23_METHOD)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ssl = SSL.Connection(ctx, s)
            # print("= CONECTANDO =")
            ssl.connect(("im.todus.cu", 1756))  # 5000

            # esperando a recibir respuesta
            def waiting(expected):
                for i in range(5):
                    try:
                        new = ssl.recv(4096)
                    except:
                        s.close()
                        break
                    new = new.decode("utf-8")
                    if expected in new:
                        return new
                return ""
            ssl.sendall("<stream:stream xmlns='jc' o='im.todus.cu' xmlns:stream='x1' v='1.0'>")
            waiting(
                "<stream:features><es xmlns='x2'><e>PLAIN</e><e>X-OAUTH2</e></es><register xmlns='http://jabber.org/features/iq-register'/></stream:features>")
            ssl.sendall(f"<ah xmlns='ah:ns' e='PLAIN'>{encoded_auth_im_todus}</ah>")
            waiting("<ok xmlns='x2'/>")
            ssl.sendall("<stream:stream xmlns='jc' o='im.todus.cu' xmlns:stream='x1' v='1.0'>")
            waiting("<stream:features><b1 xmlns='x4'/>")
            ssl.sendall(f"<iq i='{id_sesion}-1' t='set'><b1 xmlns='x4'></b1></iq>")
            waiting(f"t='result' i='{id_sesion}-1'>")
            ssl.sendall(f"<iq i='{id_sesion}-2' t='get'><query xmlns='todus:gurl' url='{url}'></query></iq>")
            url_firmada = waiting("status='200'")
            url_firmada = url_firmada.split("du='")
            if len(url_firmada) > 1:
                url_firmada = url_firmada[1].replace("' status='200'/></iq>", "")
                url_firmada = url_firmada.replace("&amp", "&")
                return url_firmada
        except Exception as e:
            print("Error firmando URL")
            SENT_TO_LOG(f"[Error] Firmando URL {e.args}", "ERROR")
        return url
# >--------------------------------------------------------------------------------------------------------------------<