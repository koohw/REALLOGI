import socket

# 서버 설정
HOST = '0.0.0.0'  # 모든 IP 주소에서 연결 허용
PORT = 1234      # 클라이언트와 동일한 포트 번호

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"Server listening on {HOST}:{PORT}")

    conn, addr = s.accept()
    with conn:
        print(f"Connected by {addr}")
        while True:
            # 클라이언트로부터 메시지 수신
            data = conn.recv(1024)
            if not data:
                break

            # 수신한 메시지를 문자열로 변환
            message = data.decode()
            print(f"Received from client: {message}")

            # 사용자 입력을 받아서 클라이언트로 전송
            response = input("Enter response to send to client: ")
           
            if response.lower() == 'quit':
                print("Closing connection.")
                break
           
            # 사용자 입력을 문자열에서 bytes로 변환하여 전송
            conn.sendall(response.encode())

print("Server has been shut down.")
