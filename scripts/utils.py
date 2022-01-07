import math
from PyQt5.QtCore import QObject


def nz(size_bytes):
    if size_bytes == 0:
        return "0.0 B"
    size_name = ("B", "KB", "MB", "GB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])
# >---------------------------------------------------------------------------------------------------------------------<

def nd(segundos:'int'):
    horas = int(segundos // 3600)
    segundos -= horas * 3600
    minutos = int(segundos // 60)
    segundos -= minutos * 60
    return "%02d:%02d:%02d" % (horas, minutos, segundos)
# >---------------------------------------------------------------------------------------------------------------------<
import pyaudio
import wave
chunk = 1024
class ReproducirSonido(QObject):
    def __init__(self, parent=None):
        super(ReproducirSonido, self).__init__(parent)

    def run(self, sonido_dir):
        # ABRIMOS UBICACIÓN DEL AUDIO.
        f = wave.open(sonido_dir, "rb")

        # INICIAMOS PyAudio.
        p = pyaudio.PyAudio()

        # ABRIMOS STREAM
        stream = p.open(format=p.get_format_from_width(f.getsampwidth()),
                        channels=f.getnchannels(),
                        rate=f.getframerate(),
                        output=True)

        # LEEMOS INFORMACIÓN
        data = f.readframes(chunk)

        # REPRODUCIMOS "stream"
        while data:
            stream.write(data)
            data = f.readframes(chunk)

        # PARAMOS "stream".
        stream.stop_stream()
        stream.close()

        # FINALIZAMOS PyAudio
        p.terminate()
# >---------------------------------------------------------------------------------------------------------------------<
from threading import Thread
class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        Thread.join(self, *args)
        return self._return