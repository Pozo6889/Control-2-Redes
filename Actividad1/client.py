import socket

max_paquete = 16 


def main():
    host = input("Ingrese el host del servidor: ")
    puerto = int(input("Ingrese el puerto del servidor: "))
    ruta_archivo = input("Ingrese la ruta del archivo a enviar: ")

    with open(ruta_archivo, "rb") as f:
        contenido = f.read()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for i in range(0, len(contenido), max_paquete):
        trozo = contenido[i:i + max_paquete]
        sock.sendto(trozo, (host, puerto))

    print(f"[cliente] archivo enviado ({len(contenido)} bytes en "
          f"{-(-len(contenido)//max_paquete)} paquetes).")

    sock.close()


if __name__ == "__main__":
    main()