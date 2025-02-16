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
TOPIC_SIMPY_TO_AGV = "simpy/commands"  # 시뮬레이터 → AGV 명령

mqtt_received_path = []  # MQTT로 받은 전체 경로 리스트

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

# --- 모터 제어 클래스 (건들지 말 것) ---
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

# --- PID 컨트롤러 (건들지 말 것) ---
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

# --- 칼만 필터 ---
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

# --- MPU6050 (건들지 말 것) ---
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
        return {'x': y, 'y': -x}
    def get_raw_gyro_data(self):
        z = self.read_i2c_word(0x47)
        return {'z': z}
    def get_gyro_data(self):
        raw = self.get_raw_gyro_data()
        z = (raw['z'] - self.gyro_offset_z) / self.gyro_scale
        return {'z': -z}

# --- 빨간색 라인 검출 함수 (건들지 말 것) ---
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

# --- QR 코드 검출 함수 (건들지 말 것) ---
def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        pts = points[0]
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        return True, (cx, cy), data # 검출 성공 시
    return False, None, None

# --- ROI 기반 라인 검출 (chick-it.tistory.com/20 유사) ---
def find_line_roi(frame):
    h, w = frame.shape[:2]
    roi_y = int(h * 2 / 3)
    roi = frame[roi_y:h, 0:w]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower1 = np.array([0, 100, 100])
    upper1 = np.array([10, 255, 255])
    lower2 = np.array([160, 100, 100])
    upper2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower1, upper1)
    mask2 = cv2.inRange(hsv, lower2, upper2)
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
            return True, (cx, roi_y + cy)
    return False, (0, 0)

# --- 메인 함수: 라인트래킹 + QR 감지 + MPU6050 센서 값 화면 표시 ---
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
    frame_height, frame_width = frame.shape[:2]
    frame_center = frame_width // 2

    # MQTT로부터 PATH 수신 대기 (목적지 리스트)
    global mqtt_received_path
    while len(mqtt_received_path) == 0:
        print("Waiting for destination coordinates from MQTT...")
        time.sleep(1)
    destinations = mqtt_received_path
    print("목적지 좌표 수신 완료:", destinations)

    # MPU6050 초기화 (I2C 버스 번호는 필요에 따라 수정)
    try:
        bus = smbus.SMBus(7)
        mpu = MPU6050(bus)
    except Exception as e:
        print("MPU6050 초기화 실패:", e)
        return

    # 칼만 필터 (2D 속도 보정을 위해)
    kalman_x = KalmanFilter(Q=0.001, R=0.1)
    kalman_y = KalmanFilter(Q=0.001, R=0.1)

    # PID 및 속도 설정
    pid = PID(kp=0.1, ki=0.0, kd=0.01)
    original_speed = 40   # 기본 속도 40
    slow_speed = 8        # QR 감지 시 감속 속도 8
    current_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    # MPU6050 기반 위치, 속도 (단위: m, m/s) – 2D만 고려
    position = np.array([0.0, 8.0])  # (x, y); 초기 출발지 (8,0) → 출력 순서는 (y, x)
    velocity = np.array([0.0, 0.0])

    # 시뮬레이션 상 각도 (자이로 데이터로 갱신)
    angle = 0.0  

    # 간단한 노이즈 필터링 계수 및 중력 상수 (m/s^2)
    alpha = 0.1
    gravity = 9.81
    prev_time = time.time()

    # 상태 정의
    STATE_WAIT_START = 0  # 출발지 QR 대기 (첫 QR "8,0" 인식 시 바로 출발)
    STATE_ACTIVE = 1      # 라인트래킹 진행
    STATE_QR_FIND = 2     # 도중 QR 감지 시 정지 및 MQTT 전송
    STATE_STOP = 3        # 정지 상태, 명령 대기
    state = STATE_WAIT_START
    start_active_time = None  # 활성 상태 시작 시각(거리 측정을 위한 기준)

    print("경로가 설정되었습니다. 출발지 QR 코드를 카메라에 보여주세요.")

    try:
        # 메인 루프
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break

            # ===== MPU6050 센서 데이터 업데이트 =====
            # (가속도계 측정 → 속도, 위치 계산; 단, 2D(x,y)만 계산)
            accel = mpu.get_accel_data()  # 단위: g
            gyro = mpu.get_gyro_data()      # 단위: deg/s (센서에 따라 다름)
            # 자이로 데이터를 이용해 회전각(heading) 갱신
            angle += gyro['z'] * dt

            # 간단한 low-pass 필터 적용 (필요시 추가 오프셋 적용 가능)
            accel_x = alpha * accel['x']
            accel_y = alpha * accel['y']

            # 가속도 값을 월드 좌표계로 변환 (회전 보정)
            accel_world_x = accel_x * math.cos(angle) - accel_y * math.sin(angle)
            accel_world_y = accel_x * math.sin(angle) + accel_y * math.cos(angle)

            # 가속도를 m/s² 단위로 변환 (g → m/s²)
            accel_world_x *= gravity
            accel_world_y *= gravity

            # 원시 속도 추정 (적분)
            raw_vel_x = velocity[0] + accel_world_x * dt
            raw_vel_y = velocity[1] + accel_world_y * dt

            # 칼만 필터로 속도 보정 (m/s 단위)
            velocity[0] = kalman_x.update(raw_vel_x, dt)
            velocity[1] = kalman_y.update(raw_vel_y, dt)

            # 속도 적분으로 위치 추정 (단위: m)
            position[0] += velocity[0] * dt
            position[1] += velocity[1] * dt

            # 미세한 가속도에서는 마찰 효과로 속도 서서히 감소
            if abs(accel_world_x) < 0.02 and abs(accel_world_y) < 0.02:
                velocity *= 0.95

            # 속도를 cm/s 단위로 변환 (1 m/s = 100 cm/s)
            speed_cm_s = math.sqrt(velocity[0]**2 + velocity[1]**2) * 100
            # MQTT 전송 데이터 구성 (출력 순서: y, x)
            position_data = {
                "y": round(float(position[1]), 2),
                "x": round(float(position[0]), 2),
                "speed": round(speed_cm_s, 2)
            }
            displacement = int(math.hypot(position_data['y'], position_data['x'], position_data['speed']))

            # ===== 카메라 화면에 센서 데이터 표시 (정수) =====
            cv2.putText(frame, f"Pos: ({position_data['y']}, {position_data['x']})", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            cv2.putText(frame, f"Speed: {position_data['speed']} cm/s", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            cv2.putText(frame, f"Displ: {displacement} cm", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

            # ===== 상태머신 =====
            if state == STATE_WAIT_START:
                # 첫 QR(8,0) 감지 – 명령 없이 바로 출발
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                cv2.putText(frame, "Waiting for Start QR", (10, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255),2)
                motor.MotorStop()
                if qr_detected and qr_data.strip() == "8,0":
                    print("첫 출발 QR(8,0) 감지 – 주행 시작")
                    state = STATE_ACTIVE
                    start_position = position.copy()  # 출발 시 기준 갱신
                    # 경로 리스트에서 [8,0] 제거 (이미 도착한 것으로 처리)
                    if [8,0] in destinations:
                        destinations.remove([8,0])
                    print("남은 경로:", destinations)
                else:
                    motor.MotorStop()

            elif state == STATE_ACTIVE:
                # 주행 중: 라인(ROI) 검출 및 PID 보정
                # 먼저 도중 QR 감지도 함께 체크
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    print("주행 중 QR 감지 – 속도 감속 후 정지 및 MQTT 전송")
                    current_speed = slow_speed
                    # QR 데이터 예: "7,1" → 경로에서 제거 및 현재 위치 갱신
                    try:
                        coords = qr_data.strip().split(",")
                        Y = int(coords[0])
                        X = int(coords[1])
                        if [Y, X] in destinations:
                            print("QR 인식된 좌표 제거:", (Y, X))
                            destinations.remove([Y, X])
                        print("남은 경로:", destinations)
                        # 센서 위치 리셋(출발 기준 재측정)
                        position[:] = 0.0
                        velocity[:] = 0.0
                    except Exception as e:
                        print("QR 파싱 오류:", e)
                    state = STATE_QR_FIND
                    motor.MotorStop()
                    time.sleep(1)
                    continue
                else:
                    current_speed = original_speed

                # ROI 기반 라인 검출 (빨간색)
                line_found, (cx, cy) = find_line_roi(frame)
                if line_found:
                    error = cx - frame_center
                    correction = pid.update(error, dt) * 0.5
                    max_delta = 2
                    delta = correction - prev_correction
                    if abs(delta) > max_delta:
                        correction = prev_correction + max_delta * np.sign(delta)
                    prev_correction = correction

                    min_speed = 4
                    left_speed = current_speed + correction
                    right_speed = current_speed - correction
                    left_speed = max(min_speed, min(100, left_speed))
                    right_speed = max(min_speed, min(100, right_speed))
                    motor.MotorRun(0, 'forward', left_speed)
                    motor.MotorRun(1, 'forward', right_speed)
                    cv2.putText(frame, f"Line Tracking: L {left_speed}, R {right_speed}", (10, 150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0),2)
                    print(f"[ACTIVE] error: {error}, correction: {correction}, L: {left_speed}, R: {right_speed}")
                else:
                    # 라인 미검출 시, 이전 보정값 감쇠 후 직진 (계속 라인 재탐색)
                    prev_correction *= 0.9
                    left_speed = max(4, current_speed + prev_correction)
                    right_speed = max(4, current_speed - prev_correction)
                    motor.MotorRun(0, 'forward', left_speed)
                    motor.MotorRun(1, 'forward', right_speed)
                    cv2.putText(frame, "Line not detected", (10, 150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255),2)

                # # 일정 이동 거리(50cm) 도달 시, 다음 QR를 위해 감속 후 QR 탐색 모드로 전환
                # if abs(dist - waypoint_distance) <= error_margin:
                #     print("목적지 도착 임박 (50cm) → QR 감지 모드 전환")
                #     current_speed = slow_speed
                #     state = STATE_QR_FIND

            elif state == STATE_QR_FIND:
                motor.MotorRun(0, 'forward', current_speed)
                motor.MotorRun(1, 'forward', current_speed)
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    print("QR 코드 감지 – 정지 후 MQTT 전송")
                    motor.MotorStop()
                    qr_info = {"qr_data": qr_data, "position": [position_data['y'], position_data['x']]}
                    mqtt_client.publish(TOPIC_QR_INFO, json.dumps(qr_info))
                    time.sleep(1)
                    state = STATE_STOP

            elif state == STATE_STOP:
                motor.MotorStop()
                cv2.putText(frame, "Stopped, waiting for command", (10, 180),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,0),2)
                print("정지 상태: 명령을 입력하세요 (RESUME / ROTATE_LEFT / ROTATE_RIGHT):")
                cmd = input().strip().upper()
                if cmd == "RESUME":
                    print("재시작 명령 수신 – ACTIVE 모드")
                    state = STATE_ACTIVE
                    prev_correction = 0
                    # 경로 리스트에 따라 다음 QR로 진행 (이미 인식된 QR은 제거됨)
                elif cmd == "ROTATE_LEFT":
                    print("좌회전 명령 – 모터 반대방향 구동")
                    motor.MotorRun(0, 'backward', 30)
                    motor.MotorRun(1, 'forward', 30)
                    time.sleep(0.5)
                    motor.MotorStop()
                    state = STATE_ACTIVE
                elif cmd == "ROTATE_RIGHT":
                    print("우회전 명령 – 모터 반대방향 구동")
                    motor.MotorRun(0, 'forward', 30)
                    motor.MotorRun(1, 'backward', 30)
                    time.sleep(0.5)
                    motor.MotorStop()
                    state = STATE_ACTIVE
                else:
                    print("알 수 없는 명령 → 계속 정지")

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
