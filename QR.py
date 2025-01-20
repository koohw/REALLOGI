import qrcode
import json

# QR 코드에 넣을 데이터 정의
qr_data = {
    "position": (1, 1),  # 현재 위치
    "command": "stop",  # 명령
    "duration": 10  # 멈추는 시간 (초)
}

# JSON 형식으로 변환
qr_data_json = json.dumps(qr_data)

# QR 코드 생성
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(qr_data_json)
qr.make(fit=True)

# QR 코드 이미지 생성 및 저장
img = qr.make_image(fill_color="black", back_color="white")
img.save("command_qr.png")

print("QR 코드가 'command_qr.png'로 저장되었습니다.")
