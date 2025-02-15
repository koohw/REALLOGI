import cv2
import numpy as np
import time
import math
import json
from smbus2 import SMBus
import paho.mqtt.client as mqtt
from PCA9685 import PCA9685

try:
    import smbus
except ImportError:
    from smbus2 import SMBus

# --- MQTT 설정 ---
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_QR_INFO = "agv/qr_info"         # QR 감지 시 정보 전송
TOPIC_SIMPY_TO_AGV = "simpy/commands" # 시뮬레이터 → AGV 명령 (PATH, STOP 등)

mqtt_received_path = []  # MQTT로 받은 full_path를 저장
def on_connect(client, userdata, flags, rc):
    print("[MQTT] on_connect rc =", rc)
    client.subscribe(TOPIC_SIMPY_TO_AGV)
    print(f"[MQTT] Subscribed to topic: {TOPIC_SIMPY_TO_AGV}")

def on_message(client, userdata, msg):
    global mqtt_received_path
    try:
        payload = json.loads(msg.payload.decode())
        cmd = payload.get('command')
        if cmd == 'STOP':
            print("[MQTT] AGV 정지 명령 수신")
        elif cmd == 'RESUME':
            print("[MQTT] AGV 재시작 명령 수신")
        elif cmd == 'PATH':
            full_path = payload.get('data', {}).get('full_path', [])
            print("[MQTT] PATH 명령 수신 =", full_path)
            mqtt_received_path = full_path
        else:
            print("[MQTT] 알 수 없는 명령 수신:", cmd)
    except Exception as e:
        print("[MQTT] on_message 오류:", e)

mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

# --- 모터 제어 클래스 (수정 금지) ---
class MotorDriver:
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
            speed = 100
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

# --- PID 컨트롤러 (수정 금지) ---
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

# --- 칼만 필터 (이번 예제에서는 사용 안 해도 무방) ---
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

# --- MPU6050 (수정 금지, 기본 보정) ---
class MPU6050:
    def __init__(self, bus, address=0x68):
        self.bus = bus
        self.address = address
        self.gyro_scale = 131.0
        self.accel_scale = 16384.0
        self.init_sensor()
        self.calibrate_sensor()

    def init_sensor(self):
        self.bus.write_byte_data(self.address, 0x6B, 0x00)  # 전원 관리 해제
        self.bus.write_byte_data(self.address, 0x1C, 0x00)  # 가속도 감도 설정
        time.sleep(0.1)

    def calibrate_sensor(self):
        accel_sum = [0, 0]
        samples = 100
        for _ in range(samples):
            accel = self.get_raw_accel_data()
            accel_sum[0] += accel['x']
            accel_sum[1] += accel['y']
            time.sleep(0.01)
        self.accel_offset_x = accel_sum[0] / samples
        self.accel_offset_y = accel_sum[1] / samples

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
        # 내부 좌표: x(오른쪽 +), y(앞쪽 -) → 출력도 같은 기준
        x = (raw['x'] - self.accel_offset_x) / self.accel_scale
        y = (raw['y'] - self.accel_offset_y) / self.accel_scale
        return {'x': y, 'y': -x}

# --- 빨간색 라인 검출 함수 (수정 금지) ---
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
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return True, (cx, cy), mask
    return False, None, mask

# --- QR 코드 검출 함수 (수정 금지) ---
def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        pts = points[0]
        qr_x = int(np.mean(pts[:, 0]))
        qr_y = int(np.mean(pts[:, 1]))
        return True, (qr_x, qr_y), data
    return False, None, None

def line_following_with_qr():
    motor = MotorDriver()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.1)

    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    ret, frame = cap.read()
    if not ret:
        print("프레임을 읽을 수 없습니다.")
        return

    frame_center = frame.shape[1] // 2

    # MQTT에서 받은 PATH 리스트가 비어있으면, 일단 대기 후 재시도
    global mqtt_received_path
    while len(mqtt_received_path) == 0:
        print("Waiting for destination coordinates from MQTT...")
        time.sleep(1)

    destinations = mqtt_received_path
    print("목적지 좌표 수신 완료:", destinations)

    # I2C 버스 및 MPU6050
    try:
        bus = SMBus(7)
        mpu = MPU6050(bus)
    except Exception as e:
        print("MPU6050 초기화 실패:", e)
        return

    # PID 및 속도 설정
    pid = PID(kp=0.06, ki=0.0, kd=0.03)
    original_speed = 40  # 기본 직진 속도
    current_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    # 2D 위치, 속도 벡터 (m 단위)
    position = np.array([0.0, 0.0])   # (x, y)
    velocity = np.array([0.0, 0.0])   # (vx, vy)

    # 상태 정의
    STATE_WAIT_START = 0
    STATE_STRAIGHT   = 1
    STATE_QR_FIND    = 2
    STATE_STOP       = 3
    state = STATE_WAIT_START

    # 편의상, 우리가 50cm 이동하면 다음 상태로 전환하는 식이라면:
    waypoint_distance = 50.0
    error_margin = 2.0

    print("경로가 설정되었습니다. 출발지 QR 코드를 카메라에 보여주세요.")

    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break

            # --- 2D 가속도계 측정 ---
            accel = mpu.get_accel_data()  # {x, y} 단위: g
            # x축(m/s^2), y축(m/s^2)
            accel_x = accel['x'] * 9.81
            accel_y = accel['y'] * 9.81

            # 속도 적분
            new_vx = velocity[0] + accel_x * dt
            new_vy = velocity[1] + accel_y * dt

            # 위치 적분 (평균속도)
            position[0] += (velocity[0] + new_vx) * 0.5 * dt
            position[1] += (velocity[1] + new_vy) * 0.5 * dt
            velocity[0] = new_vx
            velocity[1] = new_vy

            # 현재 속도(cm/s)
            speed_cm = int(np.hypot(velocity[0], velocity[1]) * 100)
            # 현재 위치(단위 cm)
            pos_x_cm = int(position[0] * 100)
            pos_y_cm = int(position[1] * 100)
            # 출발점(0,0) 대비 직선거리
            dist = int(math.hypot(pos_x_cm, pos_y_cm))

            # 카메라 화면에 위치/속도/거리 표시
            cv2.putText(frame, f"Pos: ({pos_x_cm}, {pos_y_cm})", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            cv2.putText(frame, f"Speed: {speed_cm} cm/s", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            cv2.putText(frame, f"Dist: {dist} cm", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

            # 상태머신
            if state == STATE_WAIT_START:
                # 출발지 QR 인식 대기
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    print("출발지 QR 코드 감지 – 직진 주행 시작")
                    state = STATE_STRAIGHT
                    position = np.array([0.0, 0.0])
                    velocity = np.array([0.0, 0.0])
                else:
                    motor.MotorStop()

            elif state == STATE_STRAIGHT:
                # 빨간색 라인 검출 + PID 보정
                line_found, centroid, mask = detect_red_line(frame)
                if line_found and centroid is not None:
                    cx, cy = centroid
                    error = (cx - frame_center)
                    # kp=0.06, kd=0.03, correction에 0.5 배수로 부드럽게
                    correction = pid.update(error, dt) * 0.5
                    # 급격한 변동 제한
                    max_delta = 2
                    delta = correction - prev_correction
                    if abs(delta) > max_delta:
                        correction = prev_correction + max_delta * np.sign(delta)
                    prev_correction = correction

                    # 좌/우 속도 계산
                    min_speed = 4
                    left_speed = current_speed + correction
                    right_speed = current_speed - correction
                    left_speed = max(min_speed, min(100, left_speed))
                    right_speed = max(min_speed, min(100, right_speed))

                    motor.MotorRun(0, 'forward', left_speed)
                    motor.MotorRun(1, 'forward', right_speed)
                else:
                    # 라인 미검출 시 전진
                    motor.MotorRun(0, 'forward', current_speed)
                    motor.MotorRun(1, 'forward', current_speed)

                # 일정 거리 도달 시 속도감속 + QR 탐색 상태
                if abs(dist - waypoint_distance) <= error_margin:
                    print("목적지 도착 임박: 속도 감속 및 QR 감지 모드로 전환")
                    current_speed = 8
                    state = STATE_QR_FIND

            elif state == STATE_QR_FIND:
                # 느린 속도로 QR 탐색
                motor.MotorRun(0, 'forward', current_speed)
                motor.MotorRun(1, 'forward', current_speed)
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    print("QR 코드 감지 – 정지 후 MQTT 전송")
                    motor.MotorStop()
                    # 예: 다음 목적지 인덱스, QR 데이터 등 전송
                    # 실제 경로 인덱스 관리나 mqtt publish 로직은 상황에 맞춰 작성
                    qr_info = {"qr_data": qr_data, "position": [pos_x_cm, pos_y_cm]}
                    mqtt_client.publish(TOPIC_QR_INFO, json.dumps(qr_info))
                    time.sleep(1)
                    state = STATE_STOP

            elif state == STATE_STOP:
                motor.MotorStop()
                cv2.putText(frame, "Stopped, waiting for command", (10, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,0), 2)
                print("정지 상태: 명령을 입력하세요 (RESUME / ROTATE_LEFT / ROTATE_RIGHT):")
                cmd = input().strip().upper()
                if cmd == "RESUME":
                    print("재시작 – 직진 모드")
                    # 다음 목적지 인덱스 증가 등 처리
                    position = np.array([0.0, 0.0])
                    velocity = np.array([0.0, 0.0])
                    current_speed = original_speed
                    state = STATE_STRAIGHT
                elif cmd == "ROTATE_LEFT":
                    print("좌회전 명령 – 모터 반대방향 구동")
                    motor.MotorRun(0, 'backward', 30)
                    motor.MotorRun(1, 'forward', 30)
                    time.sleep(0.5)
                    motor.MotorStop()
                    state = STATE_STRAIGHT
                elif cmd == "ROTATE_RIGHT":
                    print("우회전 명령 – 모터 반대방향 구동")
                    motor.MotorRun(0, 'forward', 30)
                    motor.MotorRun(1, 'backward', 30)
                    time.sleep(0.5)
                    motor.MotorStop()
                    state = STATE_STRAIGHT
                else:
                    print("알 수 없는 명령. 계속 정지합니다.")

            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Ctrl+C 입력, 종료 중")
    finally:
        motor.MotorStop()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    line_following_with_qr()
