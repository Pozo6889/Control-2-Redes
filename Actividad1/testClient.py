import SocketTCP

# TEST DEL ENUNCIADO

IP_VM = ("127.0.0.1", 8000)

client_socketTCP = SocketTCP.SocketTCP()
client_socketTCP.connect(IP_VM)
# test 1
message = "Mensje de len=16".encode()
client_socketTCP.send(message)
# test 2
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message)
# test 3
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message)