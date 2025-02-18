#!/usr/bin/python3
import cv2
import numpy as np
import time
import json
import math
import smbus
# import RPi.GPIO as GPIO
from PCA9685 import PCA9685  # 젯슨 오린나노에 맞게 I2C 버스 번호 조정

import sys
sys.path.append()

# -------------------------------
# Global 설정: 회전/주행용 MotorDriver 참조 코드
# -------------------------------
Dir = ['forward', 'backward']
pwm = PCA9685(0x40, debug=True)
pwm.setPWMFreq(50)

# -------------------------------
# 초음파 센서 설정 (GPIO BOARD 모드)
# -------------------------------
# 젯슨 오린나노에서는 cleanup() 호출은 프로그램 종료 시에만 수행합니다.
# GPIO.setmode(GPIO.BOARD)
# TRIG = 7
# ECHO = 15
# try:
#    GPIO.setup(TRIG, GPIO.OUT)
#    GPIO.setup(ECHO, GPIO.IN)
#except Exception as e:
#    print("GPIO 설정 오류:", e)
#    GPIO.cleanup()
#    exit(1)

#def get_distance():
#    """초음파 센서를 이용해 거리를 측정 (cm 단위)"""
#    GPIO.output(TRIG, False)
#    time.sleep(0.1)
#    GPIO.output(TRIG, True)
#    time.sleep(0.00001)
#    GPIO.output(TRIG, False)
#    pulse_start = time.time()
#    pulse_end = time.time()
#    while GPIO.input(ECHO) == 0:
#        pulse_start = time.time()z
#    while GPIO.input(ECHO) == 1:
#        pulse_end = time.time()
#    pulse_duration = pulse_end - pulse_start
#    distance = pulse_duration * 17150
#    distance = round(distance, 2)
#    print(f"[get_distance] 측정된 거리: {distance} cm")
#    return distance

# -------------------------------
# 모터 제어 클래스 (샘플 코드 스타일)
# -------------------------------
class MotorDriver:
    def __init__(self):
        self.PWMA = 0
        self.AIN1 = 1
        self.AIN2 = 2
        self.PWMB = 5
        self.BIN1 = 3
        self.BIN2 = 4

    def MotorRun(self, motor, index, speed):
        print(f"[MotorRun] 호출: motor={motor}, direction={index}, speed={speed}")
        if speed > 100:
            print(f"[MotorRun] speed {speed}가 최대값을 초과합니다. 명령 무시.")
            return
        if motor == 0:
            pwm.setDutycycle(self.PWMA, speed)
            if index == Dir[0]:
                pwm.setLevel(self.AIN1, 0)
                pwm.setLevel(self.AIN2, 1)
                print(f"[MotorRun] 왼쪽 모터 전진")
            else:
                pwm.setLevel(self.AIN1, 1)
                pwm.setLevel(self.AIN2, 0)
                print(f"[MotorRun] 왼쪽 모터 후진")
        else:
            pwm.setDutycycle(self.PWMB, speed)
            if index == Dir[0]:
                pwm.setLevel(self.BIN1, 0)
                pwm.setLevel(self.BIN2, 1)
                print(f"[MotorRun] 오른쪽 모터 전진")
            else:
                pwm.setLevel(self.BIN1, 1)
                pwm.setLevel(self.BIN2, 0)
                print(f"[MotorRun] 오른쪽 모터 후진")

    def MotorStop(self, motor):
        print(f"[MotorStop] 호출: motor={motor}")
        if motor == 0:
            pwm.setDutycycle(self.PWMA, 0)
            print(f"[MotorStop] 왼쪽 모터 정지")
        else:
            pwm.setDutycycle(self.PWMB, 0)
            print(f"[MotorStop] 오른쪽 모터 정지")

# -------------------------------
# 기본 동작 함수: 전진, 회전
# -------------------------------
def move_forward(motor, duration, speed=50):
    print(f"[move_forward] 전진 시작: duration={duration}s, speed={speed}")
    motor.MotorRun(0, 'forward', 100)
    motor.MotorRun(1, 'forward', 100)
    time.sleep(duration)
    motor.MotorStop(0)
    motor.MotorStop(1)
    print("[move_forward] 전진 완료.")

def rotate_right(motor):
    print("[rotate_right] 우회전 90° 시작")
    motor.MotorRun(0, 'forward', 55)
    motor.MotorRun(1, 'backward', 55)
    time.sleep(1)
    motor.MotorStop(0)
    motor.MotorStop(1)
    print("[rotate_right] 우회전 90° 완료")

def rotate_left(motor):
    print("[rotate_left] 좌회전 90° 시작")
    motor.MotorRun(0, 'backward', 55)
    motor.MotorRun(1, 'forward', 55)
    time.sleep(1)
    motor.MotorStop(0)
    motor.MotorStop(1)
    print("[rotate_left] 좌회전 90° 완료")

# -------------------------------
# QR 코드 검출 함수 (OpenCV 사용)
# -------------------------------
def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        print(f"[detect_qr_code] QR 코드 감지됨: {data}")
        return True, data
    return False, None

# -------------------------------
# 메인 시나리오 루프 (QR 명령 + 초음파 장애물)
# -------------------------------
def scenario_loop():
    motor = MotorDriver()
    cap = cv2.VideoCapture(0)  # 아래쪽 카메라 사용 (device index 0)
    cap.set(cv2.CAP_PROP_FPS, 30)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    last_qr_time = 0
    started = False  # 시작 QR 처리 여부

    print("시나리오 실행 시작...")
    while True:
        current_time = time.time()

        ## 초음파 센서 검사 (장애물이 30cm 미만이면 정지)
        #distance = get_distance()
        #if distance < 30:
        #    print(f"[시나리오] 초음파: 장애물 감지 (거리: {distance} cm) → 정지")
        #   motor.MotorStop(0)
        #    motor.MotorStop(1)
        #    time.sleep(1)
        #    continue

        ret, frame = cap.read()
        if not ret:
            print("카메라 프레임 읽기 실패")
            break

        # QR 코드 우선 검사 (1초 이상 후 처리)
        qr_found, qr_data = detect_qr_code(frame)
        if qr_found and (current_time - last_qr_time) >= 1:
            try:
                data = json.loads(qr_data)
            except Exception as e:
                print("QR 데이터 파싱 오류:", e)
                data = {}
            command = data.get("type", "").lower()
            location = data.get("location", "")
            print(f"[시나리오] QR 감지됨: type='{command}', location='{location}'")
            
            # 각 명령에 따른 동작 (이동 시간은 좌표 간 2초, 회전은 1초 등으로 계산)
            if command == "start":
                if not started:
                    # (7,0) -> (6,0): 2초 전진
                    print("[시나리오] 동작: start → (7,0)에서 (6,0)까지 2초 전진")
                    move_forward(motor, duration=4, speed=50)
                    started = True
                else:
                    print("[시나리오] 이미 시작됨. 'start' 명령 무시")
            elif command == "stop":
                print("[시나리오] 동작: stop → 정지 후 재가동 대기")
                motor.MotorStop(0)
                motor.MotorStop(1)
                input("재가동(엔터) 신호 대기...")
            elif command == "turn Right":
                # (4,0)에서 turn right 명령 → 우회전 1초 후, (4,0)에서 (4,3)까지 6초 전진
                print("[시나리오] 동작: turn right → 우회전 1초, 후 6초 전진 (4,0)에서 (4,3)까지")
                rotate_right(motor)
                move_forward(motor, duration=1000, speed=50)
            elif command == "turn left":
                # turn left 명령은 위치에 따라 다르게 처리:
                if location == "(4,3)":
                    # (4,3)에서 turn left → 좌회전 1초 후, (4,3)에서 (3,3)까지 2초 전진
                    print("[시나리오] 동작: turn left at (4,3) → 좌회전 1초, 후 2초 전진 (4,3)에서 (3,3)까지")
                    rotate_left(motor)
                    move_forward(motor, duration=6, speed=50)
                elif location == "(3,4)":
                    # (3,4)에서 turn left → 좌회전 1초 후, (3,4)에서 (2,4)까지 2초 전진
                    print("[시나리오] 동작: turn left at (3,4) → 좌회전 1초, 후 2초 전진 (3,4)에서 (2,4)까지")
                    rotate_left(motor)
                    move_forward(motor, duration=6, speed=50)
                else:
                    print("[시나리오] 위치 정보에 따른 turn left 명령 처리 불가")
            elif command == "loading and turn right":
                # (3,3)에서 적재 및 우회전:
                # 10초 대기 (적재), 우회전 1초, (3,3)에서 (3,4)까지 2초 전진
                print("[시나리오] 동작: loading and turn right → (3,3)에서 10초 대기, 우회전 1초, 후 2초 전진")
                motor.MotorStop(0)
                motor.MotorStop(1)
                time.sleep(10)
                rotate_right(motor)
                move_forward(motor, duration=2, speed=50)
            elif command == "obstacle":
                # (2,4)에서 장애물 감지: 장애물 제거될 때까지 정지
                print("[시나리오] 동작: obstacle → (2,4)에서 장애물 감지, 장애물 제거될 때까지 정지")
                motor.MotorStop(0)
                motor.MotorStop(1)
                #while True:
                    # d = get_distance()
                    # print(f"[시나리오] 초음파 센서: {d} cm")
                    # if d > 30:
                    #    print("[시나리오] 장애물 제거됨.")
                    #    break
                    # time.sleep(1)
            elif command == "unloading":
                # (0,4)에서 하역: (1,4)에서 (0,4)까지 2초 전진 후 10초 대기
                print("[시나리오] 동작: unloading → (1,4)에서 (0,4)까지 2초 전진 후 10초 대기 (하역)")
                move_forward(motor, duration=2, speed=50)
                time.sleep(10)
            else:
                print(f"[시나리오] 알 수 없는 명령: {command}")
            last_qr_time = current_time
            time.sleep(1)  # 디바운스 1초 대기
        else:
            # QR이 없으면 모터 정지 (Idle 상태 유지)
            motor.MotorStop(0)
            motor.MotorStop(1)

        cv2.imshow("Bottom Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()  
    cv2.destroyAllWindows()
    GPIO.cleanup()

# -------------------------------
# 메인 함수
# -------------------------------
def main():
    try:
        scenario_loop()
    except KeyboardInterrupt:
        print("사용자에 의해 중단되었습니다.")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
