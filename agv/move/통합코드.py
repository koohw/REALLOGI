import cv2
import numpy as np
import time
import math
import json
import threading

# MQTT 관련 라이브러리
import paho.mqtt.client as mqtt

# 모터 제어 및 I2C 통신 관련 라이브러리
from PCA9685 import PCA9685
try:
    import smbus
except ImportError:
    from smbus2 import SMBus
import RPi.GPIO as GPIO

# PyTorch (MiDaS 모델 로드를 위해)
import torch

########################################
# [공통 MQTT 설정]
########################################
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_QR_INFO = "agv/qr_info"         # QR 감지 시 정보 전송
TOPIC_SIMPY_TO_AGV = "simpy/commands"  # 원격 명령 (STOP, RESUME, TURN, PATH 등)
TOPIC_OBSTACLE = "agv/obstacle"        # 돌발 상황(장애물, 깊이 임계치, 위치 불일치 등) 전송
TOPIC_AGV_TO_SIMPY = "agv/status"        # 가속도계 측위 정보 전송

# MQTT 전역 변수
mqtt_received_command = None      # 원격 명령 (STOP, RESUME, TURN 등)
mqtt_received_path = []           # (필요 시)
mqtt_path_received = False

def on_connect(client, userdata, flags, rc):
    print("[MQTT] on_connect rc =", rc)
    client.subscribe(TOPIC_SIMPY_TO_AGV)
    print(f"[MQTT] Subscribed to topic: {TOPIC_SIMPY_TO_AGV}")

def on_message(client, userdata, msg):
    global mqtt_received_command, mqtt_received_path, mqtt_path_received
    try:
        payload = json.loads(msg.payload.decode())
        cmd = payload.get('command')
        if cmd == 'STOP':
            print("[MQTT] AGV 정지 명령 수신")
            mqtt_received_command = 'STOP'
        elif cmd == 'RESUME':
            print("[MQTT] AGV 재시작 명령 수신")
            mqtt_received_command = 'RESUME'
        elif cmd == 'TURN':
            print("[MQTT] AGV 회전 명령 수신")
            mqtt_received_command = 'TURN'
        elif cmd == 'PATH':
            full_path = payload.get('data', {}).get('full_path', [])
            print("[MQTT] PATH 명령 수신 =", full_path)
            mqtt_received_path = full_path
            mqtt_path_received = True
        else:
            print("[MQTT] 알 수 없는 명령 수신:", cmd)
    except Exception as e:
        print("[MQTT] on_message 오류:", e)

mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

########################################
# [GPIO 및 초음파 센서 설정]
########################################
GPIO.setmode(GPIO.BOARD)
TRIG = 7
ECHO = 15
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.1)
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    pulse_start = time.time()
    pulse_end = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    distance = round(distance, 2)
    return distance

########################################
# [모터 제어 클래스]
########################################
class MotorDriver:
    def __init__(self):
        self.PWMA = 0
        self.AIN1 = 1
        self.AIN2 = 2
        self.PWMB = 5
        self.BIN1 = 3
        self.BIN2 = 4
        self.pwm = PCA9685(0x40, debug=False)
        self.pwm.setPWMFreq(50)

    def MotorRun(self, motor, direction, speed):
        speed = min(speed, 100)
        if motor == 0:  # 왼쪽 모터
            self.pwm.setDutycycle(self.PWMA, int(speed))
            if direction == 'forward':
                self.pwm.setLevel(self.AIN1, 0)
                self.pwm.setLevel(self.AIN2, 1)
            else:
                self.pwm.setLevel(self.AIN1, 1)
                self.pwm.setLevel(self.AIN2, 0)
        else:  # 오른쪽 모터
            self.pwm.setDutycycle(self.PWMB, int(speed))
            if direction == 'forward':
                self.pwm.setLevel(self.BIN1, 0)
                self.pwm.setLevel(self.BIN2, 1)
            else:
                self.pwm.setLevel(self.BIN1, 1)
                self.pwm.setLevel(self.BIN2, 0)

    def MotorStop(self, motor=None):
        if motor is None:
            self.pwm.setDutycycle(self.PWMA, 0)
            self.pwm.setDutycycle(self.PWMB, 0)
        elif motor == 0:
            self.pwm.setDutycycle(self.PWMA, 0)
        else:
            self.pwm.setDutycycle(self.PWMB, 0)

########################################
# [PID 컨트롤러 클래스 (라인 트래킹용)]
########################################
class PID:
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.prev_error = 0
        self.integral = 0

    def update(self, error, dt):
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return output

########################################
# [빨간색 라인 및 QR 코드 검출 함수]
########################################
# 빨간색 라인 검출
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 100, 100])
upper_red2 = np.array([180, 255, 255])

def detect_red_line(frame):
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    cv2.imshow("Red Mask", mask)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return True, (cx, cy), mask
    return False, None, mask

# QR 코드 검출
def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        pts = points[0]
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        return True, (cx, cy), data
    return False, None, None

########################################
# [MiDaS (YOLO 기반) 모델 초기화 – 전면 카메라용]
########################################
# MiDaS_small 모델 사용 (실시간 성능 고려)
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

########################################
# [회전 함수]
########################################
def right_rotate_90_degrees(motor):
    motor.MotorRun(0, 'forward', 80)
    motor.MotorRun(1, 'backward', 80)
    time.sleep(1)
    motor.MotorStop()

def left_rotate_90_degrees(motor):
    motor.MotorRun(0, 'backward', 80)
    motor.MotorRun(1, 'forward', 80)
    time.sleep(1)
    motor.MotorStop()

########################################
# [가속도계 및 칼만 필터 관련 클래스 및 함수]
########################################
class KalmanFilter:
    def __init__(self, Q=0.001, R=0.1):
        self.Q = Q
        self.R = R
        self.P = 1.0
        self.X = 0.0
        self.velocity = 0.0

    def update(self, measurement, dt):
        predicted_position = self.X + self.velocity * dt
        self.P = self.P + self.Q
        K = self.P / (self.P + self.R)
        position_error = measurement - predicted_position
        self.X = predicted_position + K * position_error
        if dt > 0:
            self.velocity += K * (position_error / dt)
        self.P = (1 - K) * self.P
        return self.velocity

class MPU6050:
    def __init__(self, bus, address=0x68):
        self.bus = bus
        self.address = address
        self.gyro_scale = 131.0
        self.accel_scale = 16384.0
        self.init_sensor()
        self.calibrate_sensor()

    def init_sensor(self):
        self.bus.write_byte_data(self.address, 0x6B, 0x00)
        self.bus.write_byte_data(self.address, 0x1C, 0x00)
        self.bus.write_byte_data(self.address, 0x1B, 0x00)
        time.sleep(0.1)

    def calibrate_sensor(self):
        accel_sum = [0, 0]
        gyro_sum = 0
        samples = 100
        for _ in range(samples):
            accel = self.get_raw_accel_data()
            gyro = self.get_raw_gyro_data()
            accel_sum[0] += accel['x']
            accel_sum[1] += accel['y']
            gyro_sum += gyro['z']
            time.sleep(0.01)
        self.accel_offset_x = accel_sum[0] / samples
        self.accel_offset_y = accel_sum[1] / samples
        self.gyro_offset_z = gyro_sum / samples

    def read_i2c_word(self, reg):
        high = self.bus.read_byte_data(self.address, reg)
        low = self.bus.read_byte_data(self.address, reg + 1)
        val = (high << 8) + low
        return -((65535 - val) + 1) if val >= 0x8000 else val

    def get_raw_accel_data(self):
        x = self.read_i2c_word(0x3B)
        y = self.read_i2c_word(0x3D)
        return {'x': x, 'y': y}

    def get_accel_data(self):
        raw = self.get_raw_accel_data()
        x = (raw['x'] - self.accel_offset_x) / self.accel_scale
        y = (raw['y'] - self.accel_offset_y) / self.accel_scale
        # 센서 장착 방향에 따른 좌표 변환 (출력: 앞쪽(-y), 뒤쪽(+y), 오른쪽(+x), 왼쪽(-x))
        return {'x': y, 'y': -x}

    def get_raw_gyro_data(self):
        z = self.read_i2c_word(0x47)
        return {'z': z}

    def get_gyro_data(self):
        raw = self.get_raw_gyro_data()
        z = (raw['z'] - self.gyro_offset_z) / self.gyro_scale
        return {'z': -z}

########################################
# [글로벌 변수: QR 인식 위치 (예: 마지막으로 인식된 QR의 중심)]
########################################
last_qr_position = None  # (cx, cy)를 저장 (필요 시 좌표 변환)

########################################
# [글로벌 변수: 전면 카메라(YOLO/깊이) 측정값]
########################################
front_object_distance = None

########################################
# [라인트래킹 및 센서 융합 주행 함수 – 하단 카메라(0번)]
########################################
def driving_loop():
    """
    - 하단 카메라(0번)를 이용하여 라인트래킹 및 QR 코드 검출 수행  
    - 초음파 센서와 전면 카메라(YOLO/깊이) 측정값을 확인하여 돌발 상황 발생 시 모터 정지 및 MQTT 경고 전송  
    """
    global mqtt_received_command, last_qr_position, front_object_distance

    motor = MotorDriver()
    # 하단 카메라: 라인트래킹/QR 검출
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.2)
   
    if not cap.isOpened():
        print("하단 카메라(0번)를 열 수 없습니다.")
        return

    ret, frame = cap.read()
    if not ret:
        print("하단 카메라 프레임을 읽을 수 없습니다.")
        return

    frame_height, frame_width = frame.shape[:2]
    frame_center = frame_width // 2

    # PID 및 속도 설정 (라인트래킹용)
    pid = PID(kp=0.1, ki=0.0, kd=0.01)
    original_speed = 40   # 기본 속도 (cm/s)
    slow_speed = 8        # 감속 시 속도
    target_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    # 상태 변수
    STATE_ACTIVE = 1
    STATE_STOP   = 2
    state = STATE_ACTIVE

    last_distance_print = time.time()

    while True:
        current_time = time.time()
        dt = current_time - prev_time
        prev_time = current_time

        # 초음파 센서 측정 (1초마다 출력)
        ultrasonic_distance = get_distance()
        if current_time - last_distance_print >= 1.0:
            print(f"[DEBUG] 초음파 센서: {ultrasonic_distance} cm")
            last_distance_print = current_time

        # 돌발 상황 조건 1: 초음파 센서 임계치 (<30cm)
        if ultrasonic_distance < 30:
            print("돌발 상황: 초음파 센서 임계치 도달")
            motor.MotorStop()
            mqtt_client.publish(TOPIC_OBSTACLE, json.dumps({"ultrasonic": ultrasonic_distance}))
            while mqtt_received_command != 'RESUME':
                time.sleep(0.1)
            mqtt_received_command = None
            state = STATE_ACTIVE
            print("재가동 명령 수신 -> 주행 재개")
            continue

        # 돌발 상황 조건 2: 전면 카메라(YOLO/깊이) 측정값이 임계치 (≤750)일 경우
        if front_object_distance is not None and front_object_distance <= 750:
            print("돌발 상황: 전면 YOLO(깊이) 임계치 도달")
            motor.MotorStop()
            mqtt_client.publish(TOPIC_OBSTACLE, json.dumps({"yolo_depth": front_object_distance}))
            while mqtt_received_command != 'RESUME':
                time.sleep(0.1)
            mqtt_received_command = None
            state = STATE_ACTIVE
            print("재가동 명령 수신 -> 주행 재개")
            continue

        ret, frame = cap.read()
        if not ret:
            print("하단 카메라 프레임 읽기 실패")
            break

        # QR 코드 검출 (위치 및 동작 정보 확인용)
        qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
        if qr_detected:
            cv2.circle(frame, qr_centroid, 5, (255, 0, 0), -1)
            cv2.putText(frame, f"QR: {qr_data}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            try:
                # QR 데이터가 JSON 문자열이라고 가정
                qr_info = json.loads(qr_data)
                qr_type = qr_info.get("type", "None")
                qr_location = qr_info.get("location", "")
                print(f"QR 정보 - type: {qr_type}, location: {qr_location}")
                
                # QR에서 회전 명령이 포함된 경우 해당 동작 실행
                if qr_type.lower() == "turn right":
                    print("QR 명령: 우회전")
                    motor.MotorStop()
                    right_rotate_90_degrees(motor)
                    # 재가동 시 필요한 추가 처리 코드
                elif qr_type.lower() == "turn left":
                    print("QR 명령: 좌회전")
                    motor.MotorStop()
                    left_rotate_90_degrees(motor)
                    # 재가동 시 필요한 추가 처리 코드
                elif "loading" in qr_type.lower() and "turn right" in qr_type.lower():
                    print("QR 명령: 로딩 후 우회전")
                    # 로딩 관련 동작 수행 후 우회전
                    motor.MotorStop()
                    # (예: 로딩 동작 처리 추가)
                    right_rotate_90_degrees(motor)
                # "None"이면 특별한 동작 없이 진행 (또는 다른 처리)
            except Exception as e:
                print("QR 데이터 파싱 오류:", e)
            # 마지막 QR 위치 갱신 (위치 비교 등 다른 용도로 활용 가능)
            last_qr_position = qr_centroid


        # 빨간색 라인 검출 및 PID 보정 (라인트래킹)
        detected, centroid, mask = detect_red_line(frame)
        if detected and centroid is not None:
            cx, cy = centroid
            cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
            cv2.line(frame, (frame_center, 0), (frame_center, frame_height), (255, 0, 0), 2)
            cv2.putText(frame, f"Centroid: ({cx}, {cy})", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            error = cx - frame_center
            correction = pid.update(error, dt)
            max_delta = 2
            delta = correction - prev_correction
            if abs(delta) > max_delta:
                correction = prev_correction + max_delta * np.sign(delta)
            prev_correction = correction
            min_speed = 10
            left_speed = target_speed + correction
            right_speed = target_speed - correction
            left_speed = max(min_speed, min(100, left_speed))
            right_speed = max(min_speed, min(100, right_speed))
            motor.MotorRun(0, 'forward', left_speed)
            motor.MotorRun(1, 'forward', right_speed)
            cv2.putText(frame, f"Line Tracking: L {left_speed:.1f}, R {right_speed:.1f}",
                        (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            print(f"[ACTIVE] error: {error:.2f}, correction: {correction:.2f}, L: {left_speed:.1f}, R: {right_speed:.1f}")
        else:
            print("돌발 상황: 빨간색 라인 미검출!")
            motor.MotorStop()
            mqtt_client.publish(TOPIC_OBSTACLE, json.dumps({"emergency": "line_not_detected"}))
            time.sleep(1)
            continue

        # MQTT 원격 명령 처리
        if mqtt_received_command is not None:
            if mqtt_received_command == 'STOP':
                print("Remote STOP 명령 실행")
                motor.MotorStop()
                state = STATE_STOP
                mqtt_received_command = None
                cv2.putText(frame, "REMOTE STOP", (10, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("Frame", frame)
                cv2.waitKey(1)
                continue
            elif mqtt_received_command == 'TURN':
                print("Remote TURN 명령 실행")
                motor.MotorStop()
                right_rotate_90_degrees(motor)
                mqtt_received_command = None

        cv2.imshow("Frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    motor.MotorStop()
    cap.release()
    cv2.destroyAllWindows()
    GPIO.cleanup()

########################################
# [전면 카메라(YOLO/깊이) 감지 쓰레드 – 카메라 번호 2]
########################################
def yolo_detection_thread():
    """
    전면 카메라(2번)를 이용해 MiDaS 기반 깊이 추정을 수행하여
    중앙 깊이 값을 전역 변수(front_object_distance)에 업데이트
    """
    global front_object_distance
    cap_yolo = cv2.VideoCapture(2)
    if not cap_yolo.isOpened():
        print("전면 카메라(2번)를 열 수 없습니다.")
        return
    while True:
        ret, frame = cap_yolo.read()
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
        front_object_distance = depth_map[center_y, center_x]
        # 디버그용 전면 깊이 맵 출력
        depth_map_normalized = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
        depth_map_uint8 = (depth_map_normalized * 255).astype(np.uint8)
        depth_colormap = cv2.applyColorMap(depth_map_uint8, cv2.COLORMAP_JET)
        cv2.imshow("Front Depth Map", depth_colormap)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        time.sleep(0.1)
    cap_yolo.release()

########################################
# [가속도계 및 위치 확인 쓰레드]
########################################
def accelerometer_thread():
    """
    MPU6050을 이용해 가속도 데이터를 읽고 칼만 필터로 위치를 추정한 후,
    마지막 QR 코드로 인식한 위치와 비교하여 불일치 시 돌발 상황 MQTT 메시지 전송
    """
    bus = smbus.SMBus(7)  # I2C 버스 번호 수정 필요
    mpu = MPU6050(bus)
    kalman_x = KalmanFilter(Q=0.001, R=0.1)
    kalman_y = KalmanFilter(Q=0.001, R=0.1)
   
    # 초기 위치 (예: 출발점, 단위: m)
    position = np.array([0.0, 8.0])
    velocity = np.array([0.0, 0.0])
    angle = 0.0  # 자이로 기반 회전 각도
    alpha = 0.1
    gravity = 9.81
    prev_time = time.time()

    prev_position = position.copy()

    while True:
        current_time = time.time()
        dt = current_time - prev_time
        prev_time = current_time

        accel = mpu.get_accel_data()   # 단위: g (보정 후)
        gyro = mpu.get_gyro_data()     # 단위: deg/s
        angle += gyro['z'] * dt

        accel_x = alpha * accel['x']
        accel_y = alpha * accel['y']
        accel_world_x = accel_x * math.cos(angle) - accel_y * math.sin(angle)
        accel_world_y = accel_x * math.sin(angle) + accel_y * math.cos(angle)
        accel_world_x *= gravity
        accel_world_y *= gravity

        raw_vel_x = velocity[0] + accel_world_x * dt
        raw_vel_y = velocity[1] + accel_world_y * dt

        velocity[0] = kalman_x.update(raw_vel_x, dt)
        velocity[1] = kalman_y.update(raw_vel_y, dt)

        position[0] += velocity[0] * dt
        position[1] += velocity[1] * dt

        if abs(accel_world_x) < 0.02 and abs(accel_world_y) < 0.02:
            velocity *= 0.95

        delta = np.linalg.norm(position - prev_position)
        prev_position = position.copy()

        pos_data = {
            "x": round(float(position[0]), 2),
            "y": round(float(position[1]), 2),
            "speed": round(math.sqrt(velocity[0]**2 + velocity[1]**2)*100, 2)
        }
        mqtt_client.publish(TOPIC_AGV_TO_SIMPY, json.dumps(pos_data))
        print(f"가속도계 위치: x={pos_data['x']}, y={pos_data['y']}, speed={pos_data['speed']} cm/s")

        if last_qr_position is not None:
            qr_x, qr_y = last_qr_position
            # 예시 변환: 화면 좌표 -> m 단위 (환경에 따라 변환 필요)
            qr_position_m = np.array([qr_x/100.0, qr_y/100.0])
            diff = np.linalg.norm(position - qr_position_m)
            if diff > 1.0:
                print("돌발 상황: 가속도계 위치와 QR 위치 불일치")
                mqtt_client.publish(TOPIC_OBSTACLE, json.dumps({"emergency": "position_mismatch", "diff": diff}))
        time.sleep(1)

########################################
# [메인 함수: 쓰레드 시작]
########################################
def main():
    try:
        drive_thread = threading.Thread(target=driving_loop, daemon=True)
        yolo_thread = threading.Thread(target=yolo_detection_thread, daemon=True)
        accel_thread = threading.Thread(target=accelerometer_thread, daemon=True)
        drive_thread.start()
        yolo_thread.start()
        accel_thread.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("프로그램 종료")
        GPIO.cleanup()

if __name__ == "__main__":
    main()
