#!/usr/bin/python3
import cv2
import numpy as np
import time
import json
import math
import threading
import smbus
from PCA9685 import PCA9685  # 젯슨나노오린에 맞게 I2C 버스 번호 조정
import torch

# ------------------------------------------------
# Global 변수 및 MQTT 설정
# ------------------------------------------------
# (여기서는 MQTT 설정은 생략했으나, 필요 시 추가 가능)
# 예시에서는 obstacle 이벤트가 발생하면 바로 동작하도록 처리

# 전역 변수: 전면 카메라에서 측정한 중앙 깊이 값
global_front_depth = None
# 전역 변수: 장애물 이벤트가 발생했는지 플래그
obstacle_event = False

# ------------------------------------------------
# Motor 제어 설정 및 클래스
# ------------------------------------------------
Dir = ['forward', 'backward']
pwm = PCA9685(0x40, debug=True)
pwm.setPWMFreq(50)

class MotorDriver:
    def __init__(self):
        self.PWMA = 0
        self.AIN1 = 1
        self.AIN2 = 2
        self.PWMB = 5
        self.BIN1 = 3
        self.BIN2 = 4

    def MotorRun(self, motor, direction, speed):
        print(f"[MotorRun] 호출: motor={motor}, direction={direction}, speed={speed}")
        if speed > 100:
            print(f"[MotorRun] speed {speed}가 최대값을 초과합니다. 명령 무시.")
            return
        if motor == 0:
            pwm.setDutycycle(self.PWMA, speed)
            if direction == Dir[0]:
                pwm.setLevel(self.AIN1, 0)
                pwm.setLevel(self.AIN2, 1)
                print(f"[MotorRun] 왼쪽 모터 전진")
            else:
                pwm.setLevel(self.AIN1, 1)
                pwm.setLevel(self.AIN2, 0)
                print(f"[MotorRun] 왼쪽 모터 후진")
        else:
            pwm.setDutycycle(self.PWMB, speed)
            if direction == Dir[0]:
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

# ------------------------------------------------
# QR 코드 검출 함수 (하단 카메라, 0번)
# ------------------------------------------------
def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        print(f"[detect_qr_code] QR 코드 감지됨: {data}")
        return True, data
    return False, None

# ------------------------------------------------
# 카메라 설정 (하단: index 0, 전면: index 2)
# ------------------------------------------------
# 하단 카메라는 QR/경로 주행용, 전면 카메라는 깊이 모니터링용

# ------------------------------------------------
# 전면 카메라를 위한 MiDaS 모델 초기화
# ------------------------------------------------
model_type = "MiDaS_small"
midas = torch.hub.load("intel-isl/MiDaS", model_type)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
midas.to(device)
midas.eval()
midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
if model_type in ["DPT_Large", "DPT_Hybrid"]:
    transform = midas_transforms.dpt_transform
else:
    transform = midas_transforms.small_transform

# ------------------------------------------------
# 하단 카메라 기반 시나리오 루프 (경로 주행 및 QR 명령 처리)
# ------------------------------------------------
def scenario_loop():
    motor = MotorDriver()
    cap_bottom = cv2.VideoCapture(0)  # 하단 카메라
    cap_bottom.set(cv2.CAP_PROP_FPS, 30)
    if not cap_bottom.isOpened():
        print("하단 카메라(0번)를 열 수 없습니다.")
        return

    last_qr_time = 0
    started = False

    print("시나리오 실행 시작...")
    while True:
        current_time = time.time()

        ret, frame = cap_bottom.read()
        if not ret:
            print("하단 카메라 프레임 읽기 실패")
            break

        # 우선 전면에서 장애물 이벤트가 발생했는지 확인
        global obstacle_event
        if obstacle_event:
            print("[시나리오] 장애물 이벤트 발생 → 3초 정지 후 주행 재개")
            motor.MotorStop(0)
            motor.MotorStop(1)
            time.sleep(3)
            obstacle_event = False
            # 이후 루프에서 재가동
            continue

        # QR 코드 검사 (1초 간격)
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
                # 전면 카메라에서 측정한 깊이 값(global_front_depth)이 750 이하이면 장애물로 간주
                print("[시나리오] 동작: obstacle → 전면 카메라의 깊이 값이 750 이하임")
                motor.MotorStop(0)
                motor.MotorStop(1)
                # 장애물이 제거될 때까지(즉, 전면 카메라 깊이 값이 750 이상이 될 때까지) 대기
                while global_front_depth is not None and global_front_depth < 750:
                    print(f"[시나리오] 장애물 대기 중: 현재 깊이 값 = {global_front_depth:.2f}")
                    time.sleep(0.5)
                print("[시나리오] 장애물 제거 확인, 주행 재개")

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

        # 영상 창에 하단 카메라 출력
        cv2.imshow("Bottom Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap_bottom.release()
    cv2.destroyWindow("Bottom Camera")

# ------------------------------------------------
# 전면 카메라 기반 장애물 감지 쓰레드 (MiDaS 깊이 추정)
# ------------------------------------------------
def front_monitoring_thread():
    global global_front_depth, obstacle_event
    cap_front = cv2.VideoCapture(2)  # 전면 카메라
    if not cap_front.isOpened():
        print("전면 카메라(2번)를 열 수 없습니다.")
        return
    while True:
        ret, frame = cap_front.read()
        if not ret:
            print("전면 카메라 프레임 읽기 실패")
            break
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        input_batch = transform(img_rgb).to(device)
        with torch.no_grad():
            prediction = midas(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=img_rgb.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()
        depth_map = prediction.cpu().numpy()
        center_y = depth_map.shape[0] // 2
        center_x = depth_map.shape[1] // 2
        global_front_depth = depth_map[center_y, center_x]
        print(f"[Front Monitor] 중앙 깊이 값: {global_front_depth:.2f}")
        # 만약 깊이 값이 750 이하이면 장애물 이벤트 발생 처리
        if global_front_depth < 750:
            print("[Front Monitor] 장애물 감지됨!")
            obstacle_event = True

        # 전면 카메라 영상 및 깊이 맵 출력
        depth_map_normalized = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
        depth_map_uint8 = (depth_map_normalized * 255).astype(np.uint8)
        depth_colormap = cv2.applyColorMap(depth_map_uint8, cv2.COLORMAP_JET)
        cv2.imshow("Front Camera - Depth Map", depth_colormap)
        cv2.imshow("Front Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        time.sleep(0.1)
    cap_front.release()
    cv2.destroyWindow("Front Camera")
    cv2.destroyWindow("Front Camera - Depth Map")

# ------------------------------------------------
# 메인 함수: 두 쓰레드 실행 (하단 시나리오 + 전면 모니터링)
# ------------------------------------------------
def main():
    try:
        t1 = threading.Thread(target=scenario_loop, daemon=True)
        t2 = threading.Thread(target=front_monitoring_thread, daemon=True)
        t1.start()
        t2.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("프로그램 종료")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
