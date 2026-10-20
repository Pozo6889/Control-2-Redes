import random
import socket
import sys
from socketUDP import SocketUDP
from slidingWindowCC import SlidingWindowCC
from CongestionControl import CongestionControl
class SocketTCP:
    # valores en binarios utilizados para flags
    # primera cifra indica syn
    # segunda cifra indica ack
    # tercera cifra indica fin
    SYN = 0b001
    ACK = 0b010
    FIN = 0b100
    # Header de tamaño de 5 bytes 1 para las flags y 4 para el seq
    HEADER_SIZE = 5
    DEBUG = "--debug" in sys.argv

    @staticmethod
    def _debug(mensaje):
        if SocketTCP.DEBUG:
            print(f"[debug] {mensaje}", file=sys.stderr, flush=True)

    def __init__(self):
        # variables iniciales del socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.destino = None
        self.num_secuencia = 0
        self.max_paquete = 16
        self.timeout = 0.5
        self.message_length = None
        self.bytes_recibidos = 0
        self.buffer_pendiente = b""
        self.window_size = 8
        self.congestion_controler = CongestionControl(8)
        self.congestion_control_on = True
        self.number_of_sent_segments = 0

    def change_congestion_control(self,value):
        self.congestion_control_on = value
            

    # se crea segmento con flag, la cual indica si lleva syn, ack o fin segun la cifra del binario
    @staticmethod
    def create_segment(seq, datos=b"", syn=False, ack=False, fin=False):
        flags = 0
        if syn:
            flags |= SocketTCP.SYN
        if ack:
            flags |= SocketTCP.ACK
        if fin:
            flags |= SocketTCP.FIN

        header = bytes([flags]) + (seq % 2**32).to_bytes(4, "big")
        return header + datos

    # se parsea el segmento para chequear valores de syn, ack, fin
    # los cuales se chequean mediante un & en binario
    # ademas de separar el seq actual y los datos
    @staticmethod
    def parse_segment(segmento):
        flags = segmento[0]
        seq = int.from_bytes(segmento[1:5], "big")
        datos = segmento[SocketTCP.HEADER_SIZE:]

        return {
            "syn": bool(flags & SocketTCP.SYN),
            "ack": bool(flags & SocketTCP.ACK),
            "fin": bool(flags & SocketTCP.FIN),
            "seq": seq,
            "datos": datos,
        }

    def _tam_buffer(self):
        return SocketTCP.HEADER_SIZE + self.max_paquete

    # crea el bind para el socket de servidor/emisor
    def bind(self, address):
        self.sock.bind(address)

    # receptor/cliente establece la conexion con el servidor/emisor
    def connect(self, address):
        self.destino = address
        num_secuencia = random.randint(0, 100)
        syn = SocketTCP.create_segment(num_secuencia, syn=True)
        info, direccion_servidor = self._enviar_hasta_respuesta(syn, lambda i: i["syn"] and i["ack"] and i["seq"] == num_secuencia + 1)    
        self.destino = direccion_servidor
        self.num_secuencia = (num_secuencia + 2) % 2**32
        ack = SocketTCP.create_segment(self.num_secuencia, ack=True)
        self.sock.sendto(ack, self.destino)

    # servidor/emisor acpeta la conexion a receptor/cliente
    def accept(self):
        
        while True:
            segmento, direccion_cliente = self.sock.recvfrom(self._tam_buffer())
            info = SocketTCP.parse_segment(segmento)
            if info["syn"]:
                break

        conexion = SocketTCP()
        conexion.bind(("", 0))
        conexion.destino = direccion_cliente
        num_secuencia = info["seq"] + 1

        
        syn_ack = SocketTCP.create_segment(num_secuencia, syn=True, ack=True)

        
        while True:
            conexion.sock.sendto(syn_ack, direccion_cliente)
            conexion.sock.settimeout(conexion.timeout)
            try:
                seg, _ = conexion.sock.recvfrom(conexion._tam_buffer())
            except socket.timeout:
                SocketTCP._debug("accept: timeout esperando el ACK final, reenvío SYN+ACK")
                continue                            
            finally:
                conexion.sock.settimeout(None)

            i = SocketTCP.parse_segment(seg)
            if i["syn"] or i["seq"] != num_secuencia + 1:
                SocketTCP._debug("accept: llegó algo que no es el ACK final, reenvío SYN+ACK")
                continue
            break

        if not i["ack"]:
            SocketTCP._debug("accept: se perdió el ACK final, pero llegó un dato con seq=x+2: "
                             "handshake completo; el dato se descarta y el cliente lo reenvía")
        conexion.num_secuencia = num_secuencia + 1             
        return conexion, conexion.sock.getsockname()

    # envia segmento  al destino guardado, al recibir respuesta, si se envia el ack y llega el numero de seq correcto
    # se avanza len(datos) en el numero de secuencia
    # en caso contrario se espera el timer y reenvia los datos
    def _enviar_segmento(self, datos):
        segmento = SocketTCP.create_segment(self.num_secuencia, datos)

        while True:
            self.sock.sendto(segmento, self.destino)
            self.sock.settimeout(self.timeout)
            try:
                segmento_ack, _ = self.sock.recvfrom(self._tam_buffer())
            except socket.timeout:
                
                SocketTCP._debug(f"send: timeout esperando el ACK de seq={self.num_secuencia}, reenvío")
                continue
            finally:
                self.sock.settimeout(None)

            info_ack = SocketTCP.parse_segment(segmento_ack)
            if info_ack["ack"] and info_ack["seq"] == self.num_secuencia + len(datos):
                break
            SocketTCP._debug(f"send: llegó ACK seq={self.num_secuencia + len(datos)} pero esperaba seq={self.num_secuencia}, "
                             "se ignora (ACK viejo)")

        self.num_secuencia = (self.num_secuencia + len(datos)) % 2**32

    # se recibe segmento, se envia segmento con seq + len(datos)
    def _recibir_segmento(self):
        while True:
            segmento, _ = self.sock.recvfrom(self._tam_buffer())
            info = SocketTCP.parse_segment(segmento)

            # Si llega un mensaje futuro (se perdio el que se esperaba), se rechaza sin enviar ack
            if info["seq"] > self.num_secuencia:
                SocketTCP._debug(f"recv: seq={info['seq']} adelantado (esperaba {self.num_secuencia}), lo rechazo")
                continue

            fin_segmento = info["seq"] + len(info["datos"])        
            ack = SocketTCP.create_segment(fin_segmento, ack=True)
            self.sock.sendto(ack, self.destino)

            
            if info["seq"] == self.num_secuencia:
                
                self.num_secuencia = fin_segmento % 2**32

                return info["datos"]

            SocketTCP._debug(f"recv: duplicado seq={info['seq']} (esperaba seq={self.num_secuencia}), "
                             "reenvío su ACK y lo descarto")

    def send(self, message, mode="go_back_n"):
        if mode == "stop_and_wait":
            self.send_using_stop_and_wait(message)
        elif mode == "go_back_n":
            self.send_using_go_back_n(message)
    def recv(self, buff_size, mode="stop_and_wait"):
        if mode == "stop_and_wait":
            return self.recv_using_stop_and_wait(buff_size)
        elif mode == "go_back_n":
            return self.recv_using_go_back_n(buff_size)
    def recv_using_stop_and_wait(self, buff_size):
        if self.message_length is None:
            largo_en_bytes = self._recibir_segmento()
            self.message_length = int.from_bytes(largo_en_bytes, byteorder="big")

        restante = self.message_length - self.bytes_recibidos
        objetivo = min(restante, buff_size)

        while len(self.buffer_pendiente) < objetivo:
            self.buffer_pendiente += self._recibir_segmento()
      
        resultado = self.buffer_pendiente[:objetivo]
        self.buffer_pendiente = self.buffer_pendiente[objetivo:]
        self.bytes_recibidos += len(resultado)
        
        if self.bytes_recibidos == self.message_length:
            self.message_length = None
            self.bytes_recibidos = 0

        return resultado
    def send_using_stop_and_wait(self,message):
        message_length = len(message)
        
        largo_en_bytes = message_length.to_bytes(4, byteorder="big")
        self._enviar_segmento(largo_en_bytes)

        
        for i in range(0, message_length, self.max_paquete):
            trozo = message[i:i + self.max_paquete]
            self._enviar_segmento(trozo)
    def recv_using_go_back_n(self, buff_size):
        self.recv_using_stop_and_wait(buff_size)
    def send_using_go_back_n(self,message):
        message_length = len(message)
        largo_en_bytes = message_length.to_bytes(4, byteorder="big")

        MSS = self.congestion_controler.MSS
        data_list = [largo_en_bytes] + [message[i:i + MSS] for i in range(0, message_length, MSS)]

        seq_final = self.num_secuencia + sum(len(d) for d in data_list)

        # creamos socket udp y vinculamos con esta clase
        udp = SocketUDP()
        udp.socket_udp.close()
        udp.socket_udp = self.sock
        self.sock.setblocking(False)
        udp.settimeout(self.timeout)

        con_control = self.congestion_controler
        con_controlON = self.congestion_control_on
        next_seq = self.num_secuencia
        n_acks = 0
        n_timeouts = 0

        if con_controlON:
            window_size = con_control.get_MSS_in_cwnd()
        else:
            window_size = self.window_size
        data_window = SlidingWindowCC(window_size, data_list, next_seq)
        if con_controlON:
            SocketTCP._debug(f"CC inicio: estado={con_control.current_state} "
                             f"cwnd={con_control.get_cwnd()} ssthresh={con_control.get_ssthresh()} "
                             f"window_size={window_size}")      

        current_data = data_window.get_data(0)


        while current_data is not None:

            envios = 0
            for i in range(data_window.window_size):
                data = data_window.get_data(i)
                if data == None:
                    break
                seq = data_window.get_sequence_number(i)
                seg = SocketTCP.create_segment(seq, data)
                udp.sendto(seg, self.destino, 0)
                self.number_of_sent_segments += 1
                envios += 1
                fin_ventana = seq + len(data)

            try:
                mayor_ack = data_window.get_sequence_number(0)
                for i in range(envios):
                    respuesta, _ = udp.recvfrom(self._tam_buffer())
                    info = SocketTCP.parse_segment(respuesta)
                    if info["ack"] and info["seq"] > mayor_ack:
                        mayor_ack = info["seq"]

                        if con_controlON:
                            con_control.event_ack_received()
                    # En este caso ya llego todo
                    if mayor_ack >= fin_ventana:      
                        break                            
            except TimeoutError:
                SocketTCP._debug("send: timeout, reenvío desde el primer segmento sin confirmar")

                if con_controlON:
                    con_control.event_timeout()
                
            udp.stop_timer(0)

            pasos = 0
            for i in range(data_window.window_size):
                data = data_window.get_data(i)
                if data is None:
                    break
                if data_window.get_sequence_number(i) + len(data) <= mayor_ack:
                    pasos += 1
                else:
                    break
            data_window.move_window(pasos)

            if con_controlON:
                window_size = con_control.get_MSS_in_cwnd()
                data_window.update_window_size(window_size)
                SocketTCP._debug(f"CC: estado={con_control.current_state} "
                                 f"cwnd={con_control.get_cwnd():.2f} ssthresh={con_control.get_ssthresh()} "
                                 f"window_size={window_size}")




            current_data = data_window.get_data(0)
        self.sock.setblocking(True)
        self.num_secuencia = seq_final % 2**32  

    def _enviar_hasta_respuesta(self, segmento, es_respuesta_esperada, max_timeouts=None):
        timeouts = 0
        while True:
            self.sock.sendto(segmento, self.destino)
            self.sock.settimeout(self.timeout)
            try:
                respuesta, direccion = self.sock.recvfrom(self._tam_buffer())
            except socket.timeout:
                timeouts += 1
                SocketTCP._debug(f"timeout {timeouts}: no llegó la respuesta esperada, reenvío")
                if max_timeouts is not None and timeouts >= max_timeouts:
                    SocketTCP._debug(f"se cumplieron {timeouts} timeouts sin respuesta, me rindo")
                    return None
                continue
            finally:
                self.sock.settimeout(None)

            info = SocketTCP.parse_segment(respuesta)
            if es_respuesta_esperada(info):
                return info,direccion

    def close(self):
        fin = SocketTCP.create_segment(self.num_secuencia, fin=True)
        resultado= self._enviar_hasta_respuesta(fin, lambda i: i["fin"] and i["ack"], max_timeouts=3)
        if resultado is None:
            SocketTCP._debug("close: no llegó el FIN+ACK tras 3 timeouts, asumo que la contraparte cerró")
            self.sock.close()
            return
        info, _ = resultado
        SocketTCP._debug("close: recibí FIN+ACK, envío el ACK final 3 veces")
        
        self.num_secuencia = (info["seq"] + 1) % 2**32
        
        ack = SocketTCP.create_segment(self.num_secuencia, ack=True)
        
        for _ in range(3):                          
            self.sock.sendto(ack, self.destino)
            self.sock.settimeout(self.timeout)
            try:
                self.sock.recvfrom(self._tam_buffer())
            except socket.timeout:
                pass
            finally:
                self.sock.settimeout(None)

        self.sock.close()

    def recv_close(self):
        while True:
            segmento, _ = self.sock.recvfrom(self._tam_buffer())
            info = SocketTCP.parse_segment(segmento)
            if info["fin"]:
                break
            
            SocketTCP._debug(f"recv_close: dato duplicado seq={info['seq']}, reenvío su ACK")
            self.sock.sendto(SocketTCP.create_segment(info["seq"] + len(info["datos"]), ack=True), self.destino)

        SocketTCP._debug("recv_close: recibí FIN, el cierre debe completarse")

        
        self.num_secuencia = (info["seq"] + 1) % 2**32
        fin_ack = SocketTCP.create_segment(self.num_secuencia, fin=True, ack=True)
        resultado = self._enviar_hasta_respuesta(fin_ack, lambda i: i["ack"] and not i["fin"], max_timeouts=3)
        if resultado is None:
            SocketTCP._debug("recv_close: no llegó el ACK final tras 3 timeouts, asumo que la contraparte cerró")
        self.sock.close()


if __name__ == "__main__":
    mi_socket = SocketTCP()
    print("SocketTCP creado correctamente.")
    print("num_secuencia inicial:", mi_socket.num_secuencia)
    print("destino inicial:", mi_socket.destino)

    segmento = SocketTCP.create_segment(seq=1, datos=b"hola", ack=True)
    info = SocketTCP.parse_segment(segmento)
    print("segmento parseado:", info)