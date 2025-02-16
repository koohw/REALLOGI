import cv2
import numpy as np
from PCA9685 import PCA9685
import time
from pyzbar.pyzbar import decode
import json

# 테이프 색상 범위 설정 (주황색, 노란색 범위)
lower_orange = np.array([5, 150, 150])
upper_orange = np.array([15, 255, 255])
lower_yellow = np.array([20, 150, 150])
upper_yellow = np.array([30, 255, 255])
black = np.array([0, 0, 0])

# QR 코드 데이터 읽기 함수
def read_qr_code_from_frame(frame):
    decoded_objects = decode(frame)
    for obj in decoded_objects:
        qr_data = obj.data.decode("utf-8")
        try:
            data = json.loads(qr_data)
            return data
        except json.JSONDecodeError:
            print("QR 데이터가 JSON 형식이 아닙니다.")
            return None
    return None

# 테이프 색상 감지 함수
def detect_tape(frame):
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
   
    # 주황색/노란색 마스크 생성
    mask_orange = cv2.inRange(hsv_frame, lower_orange, upper_orange)
    mask_yellow = cv2.inRange(hsv_frame, lower_yellow, upper_yellow)
    mask_black = cv2.inRange(hsv_frame, black, black)
   
    # 주황색 또는 노란색 영역을 합친 마스크
    mask = cv2.bitwise_or(mask_orange, mask_yellow)
   
    # 마스크에서 윤곽선 찾기
    contours, _ = cv2.findContours(mask_black, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   
    if contours:
        return True  # 테이프가 감지됨
    return False  # 테이프가 감지되지 않음

# 주행 코드
class MotorDriver():
    def __init__(self):
        self.PWMA = 0
        self.AIN1 = 1
        self.AIN2 = 2
        self.PWMB = 5
        self.BIN1 = 3
        self.BIN2 = 4
        self.pwm = PCA9685(0x40, debug=True)
        self.pwm.setPWMFreq(50)

    def MotorRun(self, motor, direction, speed):
        if speed > 100:
            return
        if motor == 0:
            self.pwm.setDutycycle(self.PWMA, speed)
            if direction == 'forward':
                self.pwm.setLevel(self.AIN1, 0)
                self.pwm.setLevel(self.AIN2, 1)
            else:
                self.pwm.setLevel(self.AIN1, 1)
                self.pwm.setLevel(self.AIN2, 0)
        else:
            self.pwm.setDutycycle(self.PWMB, speed)
            if direction == 'forward':
                self.pwm.setLevel(self.BIN1, 0)
                self.pwm.setLevel(self.BIN2, 1)
            else:
                self.pwm.setLevel(self.BIN1, 1)
                self.pwm.setLevel(self.BIN2, 0)

    def MotorStop(self, motor):
        if motor == 0:
            self.pwm.setDutycycle(self.PWMA, 0)
        else:
            self.pwm.setDutycycle(self.PWMB, 0)

# QR 코드 읽기 후 위치 출력 함수
def read_qr_from_camera():
    cap = cv2.VideoCapture(0)
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
            cap.release()
            cv2.destroyAllWindows()
            return data
        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

# 주행 및 테이프 감지 주기적으로 확인
def drive_with_tape_and_qr():
    motor = MotorDriver()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("프레임을 읽을 수 없습니다.")
            break
       
        if detect_tape(frame):  # 테이프가 감지되면 주행
            motor.MotorRun(0, 'forward', 30)
            motor.MotorRun(1, 'forward', 30)
            print("테이프 감지, 주행 중...")
        else:  # 테이프가 감지되지 않으면 멈춤
            motor.MotorStop(0)
            motor.MotorStop(1)
            print("테이프 미감지, 주행 멈춤")
       
        data = read_qr_code_from_frame(frame)
        if data:  # QR 코드가 감지되면
            print(f"QR 코드 데이터: {data}")
            position = data.get("position", "알 수 없음")
            print(f"현재 위치: {position}")
            motor.MotorStop(0)
            motor.MotorStop(1)
            break

        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
   
    cap.release()
    cv2.destroyAllWindows()

# 주행 시작
drive_with_tape_and_qr()


