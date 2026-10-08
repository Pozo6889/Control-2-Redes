import socket
import SocketTCP

IP_VM = ("127.0.0.1", 8000)

if __name__ == "__main__":
    server_socketTCP = SocketTCP.SocketTCP()
    server_socketTCP.bind(IP_VM)
    connection_socketTCP, new_address = server_socketTCP.accept()
    print("[servidor] handshake completado, nueva dirección:", new_address)
 
    # buff_size = 5 a propósito (distinto de max_paquete = 16) para probar
    # que recv() entrega exactamente lo pedido y guarda el resto.
    mensaje_completo = b""
    while True:
        trozo = connection_socketTCP.recv(5)
        if not trozo:
            break
        mensaje_completo += trozo
 
    print("[servidor] mensaje recibido:", mensaje_completo.decode())