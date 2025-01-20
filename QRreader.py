import cv2
from pyzbar.pyzbar import decode
import json

# QR 코드 이미지 읽기
def read_qr_code(file_path):
    # 이미지 로드
    img = cv2.imread(file_path)
    # QR 코드 디코딩
    decoded_objects = decode(img)
    
    for obj in decoded_objects:
        qr_data = obj.data.decode("utf-8")  # QR 코드 데이터
        # JSON 데이터를 Python 딕셔너리로 변환
        data = json.loads(qr_data)
        return data

    return None

# QR 코드 읽기
qr_file = "command_qr.png"
data = read_qr_code(qr_file)

if data:
    print(f"QR 코드 데이터: {data}")
    position = data["position"]
    command = data["command"]
    duration = data["duration"]
    
    print(f"현재 위치: {position}")
    print(f"명령: {command}")
    print(f"주행 멈춤 시간: {duration}초")
else:
    print("QR 코드를 읽을 수 없습니다.")
