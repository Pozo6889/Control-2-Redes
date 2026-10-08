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

        # --- Estado para recv() (paso 5) ---
        # Largo total (en bytes) del mensaje que estamos recibiendo. None
        # significa "todavía no sabemos, hay que recibir el primer segmento".
        self.message_length = None

        # Cuántos bytes de DATOS (sin contar headers) ya le hemos entregado
        # al que llama a recv().
        self.bytes_recibidos = 0

        # Datos que ya llegaron de la red pero que no le hemos entregado
        # todavía a quien llama a recv() (porque pidió menos de lo que
        # traía el segmento). Se guardan acá para la próxima llamada.
        self.buffer_pendiente = b""

    # ------------------------------------------------------------------
    # Funciones estáticas para armar/leer segmentos (paso 3)
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
    # 3-way handshake (paso 4)
    # ------------------------------------------------------------------
    def bind(self, address):
        """Hace que este socketTCP escuche en la dirección 'address'."""
        self.sock.bind(address)

    def connect(self, address):
        """Lado CLIENTE del 3-way handshake.

        1. Mandamos un segmento SYN con un número de secuencia inicial
           elegido al azar entre 0 y 100.
        2. Esperamos la respuesta SYN+ACK del servidor.
        3. Mandamos el ACK final para terminar el handshake.
        """
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
        # Cada mensaje suma 1 sobre el anterior: SYN lleva x, SYN+ACK lleva
        # x+1 y este ACK final lleva x+2. Desde aquí ambos lados parten de x+2.
        self.num_secuencia = (info["seq"] + 1) % 256
        ack = SocketTCP.create_segment(self.num_secuencia, ack=True)
        self.sock.sendto(ack, self.destino)

    def accept(self):
        """Lado SERVIDOR del 3-way handshake.

        Se queda esperando un SYN. Cuando llega, crea un socketTCP nuevo
        (con su propia dirección, distinta a la del socket que escuchaba),
        responde con SYN+ACK desde ese nuevo socket, y espera el ACK final.
        Retorna (nuevo_socketTCP, nueva_direccion).
        """
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

        # No inventamos un número propio al azar: confirmamos el número
        # que mandó el cliente sumándole 1 (igual que TCP real), para que
        # ambos lados terminen de acuerdo en el mismo valor.
        conexion.num_secuencia = info["seq"] + 1

        # Respondemos con SYN+ACK desde el socket nuevo.
        syn_ack = SocketTCP.create_segment(conexion.num_secuencia, syn=True, ack=True)
        conexion.sock.sendto(syn_ack, direccion_cliente)

        # Esperamos el ACK final del cliente (sin manejar pérdidas por ahora).
        segmento_ack, _ = conexion.sock.recvfrom(conexion._tam_buffer())
        info_ack = SocketTCP.parse_segment(segmento_ack)
        # info_ack["ack"] debería ser True. El ACK final trae x+2, así que
        # avanzamos nuestro número al mismo valor que ya tiene el cliente.
        conexion.num_secuencia = (conexion.num_secuencia + 1) % 256

        nueva_direccion = conexion.sock.getsockname()
        return conexion, nueva_direccion

    # ------------------------------------------------------------------
    # Stop & Wait, usado tanto por send() como por recv() (paso 5)
    # ------------------------------------------------------------------
    def _enviar_segmento(self, datos):
        """Manda un segmento con 'datos' y no retorna hasta recibir su ACK.

        Usa self.num_secuencia como número de secuencia del segmento, y lo
        avanza en 1 (módulo 256, porque el header solo tiene 1 byte para
        esto) una vez que el ACK llega. Si el timeout salta, reintenta.
        """
        segmento = SocketTCP.create_segment(self.num_secuencia, datos)

        while True:
            self.sock.sendto(segmento, self.destino)
            self.sock.settimeout(self.timeout)
            try:
                segmento_ack, _ = self.sock.recvfrom(self._tam_buffer())
            except socket.timeout:
                # No llegó el ACK a tiempo: reenviamos el mismo segmento.
                continue
            finally:
                # Volvemos a modo bloqueante para no dejar el socket con
                # timeout activo fuera de esta función.
                self.sock.settimeout(None)

            info_ack = SocketTCP.parse_segment(segmento_ack)
            if info_ack["ack"] and info_ack["seq"] == self.num_secuencia:
                break
            # Si llegó otra cosa (por ejemplo un ACK viejo), lo ignoramos
            # y seguimos esperando/reintentando.

        self.num_secuencia = (self.num_secuencia + 1) % 256

    def _recibir_segmento_confiable(self):
        """Espera un segmento de datos y responde con su ACK.

        Retorna solo los datos (sin el header). Por ahora no manejamos
        duplicados ni pérdidas en este lado: eso queda para un paso
        posterior donde sí probemos con pérdidas reales.
        """
        segmento, _ = self.sock.recvfrom(self._tam_buffer())
        info = SocketTCP.parse_segment(segmento)

        ack = SocketTCP.create_segment(info["seq"], ack=True)
        self.sock.sendto(ack, self.destino)

        # Avanzamos la secuencia esperada para el siguiente segmento.
        self.num_secuencia = (info["seq"] + 1) % 256

        return info["datos"]

    def send(self, message):
        """Envía 'message' (bytes) completo usando Stop & Wait.

        El primer segmento no lleva datos del mensaje: lleva su largo en
        bytes, para que el receptor sepa cuándo detenerse. Luego se manda
        el contenido trozado de a lo más self.max_paquete bytes.
        """
        message_length = len(message)

        # 1) Avisamos el largo total (como entero de 4 bytes).
        largo_en_bytes = message_length.to_bytes(4, byteorder="big")
        self._enviar_segmento(largo_en_bytes)

        # 2) Mandamos el contenido real, trozado de a lo más max_paquete bytes.
        for i in range(0, message_length, self.max_paquete):
            trozo = message[i:i + self.max_paquete]
            self._enviar_segmento(trozo)

    def recv(self, buff_size):
        """Retorna hasta min(message_length restante, buff_size) bytes.

        Si message_length > buff_size, hay que llamar a recv() varias
        veces para ir recibiendo el resto del mensaje.
        """
        # Primera llamada: todavía no sabemos el largo del mensaje.
        if self.message_length is None:
            largo_en_bytes = self._recibir_segmento_confiable()
            self.message_length = int.from_bytes(largo_en_bytes, byteorder="big")

        restante = self.message_length - self.bytes_recibidos
        objetivo = min(restante, buff_size)

        # Mientras no tengamos suficientes datos ya guardados, seguimos
        # pidiendo más segmentos a la red.
        while len(self.buffer_pendiente) < objetivo:
            self.buffer_pendiente += self._recibir_segmento_confiable()

        # Entregamos como máximo 'objetivo' bytes; el resto (si el último
        # segmento traía más de lo pedido) se queda guardado para la
        # próxima llamada, sin perder datos.
        resultado = self.buffer_pendiente[:objetivo]
        self.buffer_pendiente = self.buffer_pendiente[objetivo:]
        self.bytes_recibidos += len(resultado)

        # Si ya entregamos el mensaje completo, reiniciamos el estado para
        # que la próxima llamada a recv() espere el largo de un mensaje nuevo.
        if self.bytes_recibidos == self.message_length:
            self.message_length = None
            self.bytes_recibidos = 0

        return resultado

    # ------------------------------------------------------------------
    # Fin de conexión (paso 6)
    # ------------------------------------------------------------------
    def _enviar_hasta_respuesta(self, segmento, es_respuesta_esperada):
        """Manda 'segmento' y lo reenvía cada vez que salta el timeout,
        hasta que llegue un segmento que cumpla es_respuesta_esperada(info).
        Retorna el segmento recibido ya parseado."""
        while True:
            self.sock.sendto(segmento, self.destino)
            self.sock.settimeout(self.timeout)
            try:
                respuesta, _ = self.sock.recvfrom(self._tam_buffer())
            except socket.timeout:
                continue
            finally:
                self.sock.settimeout(None)

            info = SocketTCP.parse_segment(respuesta)
            if es_respuesta_esperada(info):
                return info

    def close(self):
        """Lado "Host A" del cierre: el que inicia.

        1. Manda FIN.
        2. Espera FIN+ACK del otro lado (reenvía el FIN si hay timeout).
        3. Manda el ACK final y libera el socket.
        """
        # 1) FIN -> y 2) <- FIN+ACK
        fin = SocketTCP.create_segment(self.num_secuencia, fin=True)
        info = self._enviar_hasta_respuesta(fin, lambda i: i["fin"] and i["ack"])

        # Como en el video: FIN lleva seq=z, FIN+ACK lleva z+1 y el ACK
        # final lleva z+2 (cada mensaje suma 1 sobre el anterior).
        self.num_secuencia = (info["seq"] + 1) % 256

        # 3) ACK ->
        ack = SocketTCP.create_segment(self.num_secuencia, ack=True)
        self.sock.sendto(ack, self.destino)

        self.sock.close()

    def recv_close(self):
        """Lado "Host B" del cierre: el que responde.

        1. Espera un FIN (ignora cualquier otro segmento).
        2. Responde FIN+ACK y espera el ACK final (reenvía si hay timeout).
        3. Libera el socket.
        """
        # 1) <- FIN
        while True:
            segmento, _ = self.sock.recvfrom(self._tam_buffer())
            info = SocketTCP.parse_segment(segmento)
            if info["fin"]:
                break

        # 2) FIN+ACK -> y <- ACK
        self.num_secuencia = (info["seq"] + 1) % 256
        fin_ack = SocketTCP.create_segment(self.num_secuencia, fin=True, ack=True)
        self._enviar_hasta_respuesta(fin_ack, lambda i: i["ack"] and not i["fin"])

        # 3) Cerramos el socket.
        self.sock.close()


if __name__ == "__main__":
    mi_socket = SocketTCP()
    print("SocketTCP creado correctamente.")
    print("num_secuencia inicial:", mi_socket.num_secuencia)
    print("destino inicial:", mi_socket.destino)

    segmento = SocketTCP.create_segment(seq=1, datos=b"hola", ack=True)
    info = SocketTCP.parse_segment(segmento)
    print("segmento parseado:", info)