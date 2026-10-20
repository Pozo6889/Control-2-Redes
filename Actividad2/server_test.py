import sys
import SocketTCP

N = int(sys.argv[1])
esperado = bytes((i * 7 + 3) % 256 for i in range(N))

server = SocketTCP.SocketTCP()
server.bind(("127.0.0.1", 8000))

while True:                       # atiende una conexión por corrida
    conn, _ = server.accept()
    datos = b""
    while len(datos) < N:
        datos += conn.recv(64)
    print("INTEGRIDAD:", "OK" if datos == esperado else "FALLÓ", f"({len(datos)} bytes)")
    conn.recv_close()