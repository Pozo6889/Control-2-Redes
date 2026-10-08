import socket
import SocketTCP

IP_VM = ("127.0.0.1", 8000)

if __name__ == "__main__":
    client_socketTCP = SocketTCP.SocketTCP()
    client_socketTCP.connect(IP_VM)
    print("[cliente] handshake completado")
    
    mensaje = b"Mensaje de prueba para ver si sirve el Stop & Wait"
    client_socketTCP.send(mensaje)
    print("[cliente] mensaje enviado:", mensaje.decode())