import cv2
from pyzbar.pyzbar import decode
import json

# QR 코드 데이터 읽기
def read_qr_code_from_frame(frame):
    # QR 코드 디코딩
    decoded_objects = decode(frame)
   
    for obj in decoded_objects:
        qr_data = obj.data.decode("utf-8")  # QR 코드 데이터
        # JSON 데이터를 Python 딕셔너리로 변환
        try:
            data = json.loads(qr_data)
            return data
        except json.JSONDecodeError:
            print("QR 데이터가 JSON 형식이 아닙니다.")
            return None

    return None

# 라즈베리파이 카메라로 QR 코드 읽기
def read_qr_from_camera():
    cap = cv2.VideoCapture(0)  # 0번 카메라 사용 (USB 카메라 또는 Pi 카메라)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return None
   
    print("QR 코드를 카메라에 보여주세요.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("프레임을 읽을 수 없습니다.")
            break
       
        data = read_qr_code_from_frame(frame)
        if data:
            print(f"QR 코드 데이터: {data}")
            position = data.get("position", "알 수 없음")
            command = data.get("command", "알 수 없음")
            duration = data.get("duration", "알 수 없음")
           
            print(f"현재 위치: {position}")
            print(f"명령: {command}")
            print(f"주행 멈춤 시간: {duration}초")
            break
       
        # 디버깅용: 화면 출력
        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# 실행
read_qr_from_camera()