import sys
import SocketTCP

# Uso: python3 server.py [host] [puerto] [buff_size] [--debug]
# Por defecto: 127.0.0.1 8000 1024. El archivo recibido se imprime por stdout.


def main():
    args = [a for a in sys.argv[1:] if a != "--debug"]
    host = args[0] if len(args) > 0 else "127.0.0.1"
    puerto = int(args[1]) if len(args) > 1 else 8000
    buff_size = int(args[2]) if len(args) > 2 else 1024

    server_socketTCP = SocketTCP.SocketTCP()
    server_socketTCP.bind((host, puerto))
    connection_socketTCP, new_address = server_socketTCP.accept()

    # El primer mensaje es el tamaño del archivo (a lo más 16 bytes).
    tam = int(connection_socketTCP.recv(16))

    recibidos = 0
    while recibidos < tam:
        trozo = connection_socketTCP.recv(buff_size)
        if SocketTCP.SocketTCP.DEBUG:
            print(f"[debug] recv({buff_size}) devolvió {len(trozo)} bytes", file=sys.stderr, flush=True)
        sys.stdout.buffer.write(trozo)
        sys.stdout.buffer.flush()
        recibidos += len(trozo)

    connection_socketTCP.recv_close()


if __name__ == "__main__":
    main()
