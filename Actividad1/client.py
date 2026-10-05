import socket
import SocketTCP

IP_VM = ("127.0.0.1", 8000)

if __name__ == "__main__":
    client_socketTCP = SocketTCP.SocketTCP()
    client_socketTCP.connect(IP_VM)
    
    print("[cliente] handshake completado")
    print("[cliente] num_secuencia:", client_socketTCP.num_secuencia)
    print("[cliente] destino (nueva conexión del servidor):", client_socketTCP.destino)