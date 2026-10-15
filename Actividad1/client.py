import sys
import SocketTCP

# Uso: python3 client.py <host> <puerto> [--debug] < archivo.txt


def main():
    args = [a for a in sys.argv[1:] if a != "--debug"]
    if len(args) < 2:
        print("Uso: python3 client.py <host> <puerto> [--debug] < archivo.txt", file=sys.stderr)
        sys.exit(1)
    host = args[0]
    puerto = int(args[1])

    # El archivo llega por entrada estándar (redirección "< archivo.txt").
    contenido = sys.stdin.buffer.read()

    client_socketTCP = SocketTCP.SocketTCP()
    client_socketTCP.connect((host, puerto))

    # Primero avisamos el tamaño del archivo (para que el servidor sepa
    # cuándo dejar de llamar a recv) y luego mandamos el contenido.
    client_socketTCP.send(str(len(contenido)).encode())
    if contenido:
        client_socketTCP.send(contenido)

    client_socketTCP.close()


if __name__ == "__main__":
    main()
