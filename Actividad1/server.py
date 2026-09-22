import socket
 
max_paquete = 16 
 
 
def main():
    puerto = int(input("Ingrese el puerto en el que escuchará el servidor: "))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", puerto))
 
    print(f"[servidor] escuchando en el puerto {puerto}...")
 
    while True:
        datos, direccion_origen = sock.recvfrom(max_paquete)
        print(datos.decode(), end="", flush=True)
 
 
if __name__ == "__main__":
    main()
