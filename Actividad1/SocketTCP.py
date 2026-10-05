import random
import socket


class SocketTCP:
    # --- Banderas del header, cada una ocupa un bit distinto del byte 0 ---
    SYN = 0b001
    ACK = 0b010
    FIN = 0b100

    # Tamaño fijo del header en bytes: 1 byte de flags + 1 byte de secuencia.
    HEADER_SIZE = 2

    def __init__(self):
        # Socket UDP real que usaremos por debajo para enviar y recibir bytes.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Dirección (host, puerto) del otro extremo de la comunicación.
        # Se define en connect() (lado cliente) o en accept() (lado servidor).
        self.destino = None

        # Número de secuencia para Stop & Wait.
        self.num_secuencia = 0

        # Tamaño máximo de payload por paquete (sin headers).
        self.max_paquete = 16

        # Tiempo (en segundos) que esperamos un ACK antes de reenviar.
        self.timeout = 0.5

    # ------------------------------------------------------------------
    # Parte 3
    # ------------------------------------------------------------------
    @staticmethod
    def create_segment(seq, datos=b"", syn=False, ack=False, fin=False):
        flags = 0
        if syn:
            flags |= SocketTCP.SYN
        if ack:
            flags |= SocketTCP.ACK
        if fin:
            flags |= SocketTCP.FIN

        header = bytes([flags, seq])
        return header + datos

    @staticmethod
    def parse_segment(segmento):
        flags = segmento[0]
        seq = segmento[1]
        datos = segmento[SocketTCP.HEADER_SIZE:]

        return {
            "syn": bool(flags & SocketTCP.SYN),
            "ack": bool(flags & SocketTCP.ACK),
            "fin": bool(flags & SocketTCP.FIN),
            "seq": seq,
            "datos": datos,
        }

    # Tamaño de buffer que usamos para recvfrom (header + contenido máximo).
    def _tam_buffer(self):
        return SocketTCP.HEADER_SIZE + self.max_paquete

    # ------------------------------------------------------------------
    # Parte 4
    # ------------------------------------------------------------------
    def bind(self, address):
        self.sock.bind(address)

    def connect(self, address):
        self.destino = address
        self.num_secuencia = random.randint(0, 100)

        # 1) SYN ->
        syn = SocketTCP.create_segment(self.num_secuencia, syn=True)
        self.sock.sendto(syn, self.destino)

        # 2) <- SYN+ACK
        # (todavía no manejamos pérdidas, así que no hay timeout/reintento)
        segmento, direccion_servidor = self.sock.recvfrom(self._tam_buffer())
        info = SocketTCP.parse_segment(segmento)
        # info["syn"] e info["ack"] deberían ser True en este punto.

        # El servidor respondió desde un socket nuevo (distinto al que
        # escuchaba originalmente), así que actualizamos el destino.
        self.destino = direccion_servidor

        # 3) ACK ->
        self.num_secuencia += 1
        ack = SocketTCP.create_segment(self.num_secuencia, ack=True)
        self.sock.sendto(ack, self.destino)

    def accept(self):
        # Esperamos un segmento que tenga la bandera SYN prendida.
        while True:
            segmento, direccion_cliente = self.sock.recvfrom(self._tam_buffer())
            info = SocketTCP.parse_segment(segmento)
            if info["syn"]:
                break

        # Creamos el socketTCP "de conexión", con su propio socket UDP
        # escuchando en una dirección distinta (puerto libre asignado por
        # el sistema operativo, usando nuestra propia función bind).
        conexion = SocketTCP()
        conexion.bind(("", 0))
        conexion.destino = direccion_cliente
        conexion.num_secuencia = random.randint(0, 100)

        # Respondemos con SYN+ACK desde el socket nuevo.
        syn_ack = SocketTCP.create_segment(conexion.num_secuencia, syn=True, ack=True)
        conexion.sock.sendto(syn_ack, direccion_cliente)

        # Esperamos el ACK final del cliente (sin manejar pérdidas por ahora).
        segmento_ack, _ = conexion.sock.recvfrom(conexion._tam_buffer())
        info_ack = SocketTCP.parse_segment(segmento_ack)
        # info_ack["ack"] debería ser True en este punto.

        nueva_direccion = conexion.sock.getsockname()
        return conexion, nueva_direccion


if __name__ == "__main__":
    mi_socket = SocketTCP()
    print("SocketTCP creado correctamente.")
    print("num_secuencia inicial:", mi_socket.num_secuencia)
    print("destino inicial:", mi_socket.destino)

    segmento = SocketTCP.create_segment(seq=1, datos=b"hola", ack=True)
    info = SocketTCP.parse_segment(segmento)
    print("segmento parseado:", info)