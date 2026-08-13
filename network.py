import socket
import qrcode
import os
from settings import settings

def get_local_ip():

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if settings.host != "127.0.0.1":
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]

        except Exception:
            ip = "127.0.0.1"

        finally:
            s.close()

        
    else:
        ip = "127.0.0.1"

    return ip

def create_qr():

    ip = get_local_ip()

    url = f"http://{ip}:{settings.get("port")}"


    img = qrcode.make(url)


    path = "static/network_qr.png"


    img.save(path)


    return url