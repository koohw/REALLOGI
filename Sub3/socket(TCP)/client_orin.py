import socket
HOST = '192.168.0.2'  # 서버의 IP 주소
PORT = 1234          # 서버와 동일한 포트 번호
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    while True:
        message = input("Enter message to server: ")
        s.sendall(message.encode())
        if message.lower() == 'quit':
            print("Closing connection.")
            break
        data = s.recv(1024)
        print(f"Received from server: {data.decode()}")
