import sys, time
import SocketTCP

N = int(sys.argv[1])
usar_cc = sys.argv[2] == "cc"
datos = bytes((i * 7 + 3) % 256 for i in range(N))

c = SocketTCP.SocketTCP()
c.change_congestion_control(usar_cc)
c.connect(("127.0.0.1", 8000))

t0 = time.time()
c.send(datos, mode="go_back_n")
t = time.time() - t0

print(f"N={N} cc={usar_cc} tiempo={t:.3f}s segmentos_enviados={c.number_of_sent_segments}")
c.close()