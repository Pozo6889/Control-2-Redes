import socket
import SocketTCP

IP_VM = ("127.0.0.1", 8000)

if __name__ == "__main__":
    server_socketTCP = SocketTCP.SocketTCP()
    server_socketTCP.bind(IP_VM)
    connection_socketTCP, new_address = server_socketTCP.accept()
    
    print("[servidor] handshake completado")
    print("[servidor] nueva dirección de la conexión:", new_address)
    print("[servidor] num_secuencia:", connection_socketTCP.num_secuencia)
    print("[servidor] destino (cliente):", connection_socketTCP.destino)