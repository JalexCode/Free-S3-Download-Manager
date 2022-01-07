# >---------------------------------------------------------------------------------------------------------------------<
import base64
import binascii
import random
from datetime import datetime, date

import requests

from scripts.todus import SIGN_URL


def generate_folder_file():
    charset = ["a", "b", "c", "d", "e", "f", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    folder = ""
    for i in range(3):
        folder += charset[random.randrange(0, len(charset) - 1)]
    file = ""
    for i in range(64):
        file += charset[random.randrange(0, len(charset) - 1)]
    return f"{folder}/{file}"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MjQxMjY4NTUsInVzZXJuYW1lIjoiNTM1NDY1NTkwOSIsInZlcnNpb24iOiIyMTgwOCJ9.iMuEKKaPOYCasSocJz0WsNcamsiQmJPWwcCVZxC4vUs"
url = f"https://s3.todus.cu/todus/file/%s/%s"
# PEDIR EL TOKEN
with open("icono_50x50.png", "rb") as file:
    content = file.read()
    #
    header = {"Host": "s3.todus.cu", "user-agent": "ToDus 0.39.4 HTTP-Upload", "authorization": f"Bearer {TOKEN}",
            "content-type": "application/octet-stream", "accept-encoding": "gzip"}

    url = url%(date.today(), generate_folder_file())
    print(url)
    signed_url = SIGN_URL(url)
    signed_url = signed_url.replace(";", "")
    print(signed_url)
    put = requests.put(signed_url, data=content, headers=header)
    print(put.status_code)
    print(put.text)

#todus/file/2021-04-09/85b/85bb8a9a515a5903f5a5811ad5e827f1fe2f5facb58fdc6abd4664ce0b3794b0?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=YICSWAWTA0DXZ7C4K7WJ%2F20210409%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20210409T182103Z&X-Amz-Expires=120&X-Amz-SignedHeaders=host&X-Amz-Signature=1766c214d0df6e125a9bf193f37b46031826987979acd5185f1f255c0d9987d8 h2
#todus/file/2021-06-18/cc4/7efedac1c417b2c858e5d816dd4d5373d22aba0a1b27ffad251661a54547b734?X-Amz-Algorithm=AWS4-HMAC-SHA256&;X-Amz-Credential=YICSWAWTA0DXZ7C4K7WJ%2F20210619%2Fus-east-1%2Fs3%2Faws4_request&;X-Amz-Date=20210619T011626Z&;X-Amz-Expires=60&;X-Amz-SignedHeaders=host&;X-Amz-Signature=0795bcf4c4718736fe4c3bf997ef2448288cd96c0c8a22afd628a66f6d4db56f