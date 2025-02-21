import cv2
import numpy as np
import time
import json
from PCA9685 import PCA9685
import RPi.GPIO as GPIO

Dir = ['forward', 'backward']
pwm = PCA9685(0x40, debug=True)
pwm.setPWMFreq(50)

class MotorDriver():
    def __init__(self):
        self.PWMA = 0
        self.AIN1 = 1
        self.AIN2 = 2
        self.PWMB = 5
        self.BIN1 = 3
        self.BIN2 = 4

    def MotorRun(self, motor, index, speed):
        speed = max(0, min(speed, 100))  # 속도 제한 (0~100)
        if motor == 0:
            pwm.setDutycycle(self.PWMA, speed)
            pwm.setLevel(self.AIN1, 0 if index == 'forward' else 1)
            pwm.setLevel(self.AIN2, 1 if index == 'forward' else 0)
        else:
            pwm.setDutycycle(self.PWMB, speed)
            pwm.setLevel(self.BIN1, 0 if index == 'forward' else 1)
            pwm.setLevel(self.BIN2, 1 if index == 'forward' else 0)

    def MotorStop(self, motor):
        pwm.setDutycycle(self.PWMA if motor == 0 else self.PWMB, 0)


# --- QR 코드 검출 및 JSON 데이터 파싱 ---
def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    
    if points is not None and data:
        try:
            qr_data = json.loads(data)  # JSON 데이터로 변환
            if "type" in qr_data:
                qr_type = qr_data["type"].strip().lower()  # 공백 제거 + 소문자로 변환
                return True, qr_type
        except json.JSONDecodeError:
            print("QR 코드 데이터 JSON 디코딩 실패:", data)
    
    return False, None


def line_following_with_qr():
    motor = MotorDriver()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.2)

    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return
    
    ret, frame = cap.read()

    if not ret:
        print("프레임을 읽을 수 없습니다.")
        return
    
    try:
        while True:
            qr_detected, qr_type = detect_qr_code(frame)

            if qr_detected:  
                print(f"QR 코드 인식: [{qr_type}]")  # ✅ 값을 []로 감싸서 디버깅 확인
                print(f"qr_type 데이터 타입: {type(qr_type)}")  # ✅ 타입 확인

                if qr_type == 'start':
                    print("🚀 Start 명령 실행")
                    motor.MotorRun(0, 'forward', 50)
                    motor.MotorRun(1, 'forward', 50)
                    time.sleep(3)
                    motor.MotorRun(0, 'forward', 10)
                    motor.MotorRun(1, 'forward', 10)

                elif qr_type == 'stop':
                    print("🛑 Stop 명령 실행")
                    motor.MotorStop(0)
                    motor.MotorStop(1)

                elif qr_type == 'turn right':
                    print("➡️ Turn Right 실행")
                    motor.MotorRun(0, 'forward', 50)
                    motor.MotorRun(1, 'backward', 50)
                    time.sleep(2)
                    motor.MotorRun(0, 'forward', 50)
                    motor.MotorRun(1, 'forward', 50)
                    time.sleep(3)
                    motor.MotorRun(0, 'forward', 10)
                    motor.MotorRun(1, 'forward', 10)

                elif qr_type == 'turn left':
                    print("⬅️ Turn Left 실행")
                    motor.MotorRun(0, 'backward', 50)
                    motor.MotorRun(1, 'forward', 50)
                    time.sleep(2)
                    motor.MotorRun(0, 'forward', 50)
                    motor.MotorRun(1, 'forward', 50)
                    time.sleep(3)
                    motor.MotorRun(0, 'forward', 10)
                    motor.MotorRun(1, 'forward', 10)

                elif qr_type == 'obstacle':
                    print("⚠️ 장애물 감지 - 정지")
                    motor.MotorStop(0)
                    motor.MotorStop(1)
                
                elif qr_type == 'loading and turn right':
                    print("📦 로딩 후 우회전")
                    motor.MotorStop(0)
                    motor.MotorStop(1)
                    time.sleep(10)
                    motor.MotorRun(0, 'forward', 50)
                    motor.MotorRun(1, 'backward', 50)
                    time.sleep(2)
                    motor.MotorRun(0, 'forward', 50)
                    motor.MotorRun(1, 'forward', 50)
                    time.sleep(3)
                    motor.MotorRun(0, 'forward', 10)
                    motor.MotorRun(1, 'forward', 10)

                elif qr_type == 'unloading':
                    print("📦 언로딩 완료")
                    motor.MotorStop(0)
                    motor.MotorStop(1)
                    break
                
                else:
                    print(f"⚠️ 알 수 없는 명령: [{qr_type}]")

            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Ctrl+C 입력, 모터를 정지합니다.")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    line_following_with_qr()
