import cv2
import numpy as np
import time
import math
import json
from PCA9685 import PCA9685
import paho.mqtt.client as mqtt

try:
    import smbus
except ImportError:
    from smbus2 import SMBus

# ===== 전역 MQTT 명령 변수 =====
mqtt_command = None

# ===== 모터 제어 클래스 (변경 없음) =====
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

# ===== PID 컨트롤러 클래스 (변경 없음) =====
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

# ===== 가속도계 센서 관련 클래스 (첫번째 코드 그대로) =====
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
        return {'x': y, 'y': -x}  # 내부 좌표 변환

    def get_raw_gyro_data(self):
        z = self.read_i2c_word(0x47)
        return {'z': z}

    def get_gyro_data(self):
        raw = self.get_raw_gyro_data()
        z = (raw['z'] - self.gyro_offset_z) / self.gyro_scale
        return {'z': -z}

# ===== 빨간색 라인 및 QR 코드 검출 함수 (변경 없음) =====
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

def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        pts = points[0]
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        return True, (cx, cy), data
    return False, None, None

# ===== MQTT 설정 및 콜백 함수 (참고 코드 반영) =====
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_AGV_TO_SIMPY = "agv/status"       # 상태 및 ACK 메시지 송신 토픽
TOPIC_SIMPY_TO_AGV = "simpy/commands"     # 서버로부터 명령 수신 토픽
TOPIC_QR_INFO = "agv/qr_info"             # QR 코드 정보 송신 토픽

mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(TOPIC_SIMPY_TO_AGV)

def on_message(client, userdata, msg):
    global mqtt_command
    try:
        command = json.loads(msg.payload)
        print(f"Received command: {command}")
        mqtt_command = command
    except Exception as e:
        print(f"Error processing message: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

# ===== 라인트래킹 + QR 검출 + 가속도계 기반 이동거리 측정 병합 메인 함수 =====
def line_following_with_qr_and_accel():
    global mqtt_command
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

    # PID 및 속도 설정 (계산 변경 없음)
    pid = PID(kp=0.1, ki=0.0, kd=0.01)
    original_speed = 40  # 초기 목표 속도 (cm/s)
    target_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    # 가속도계 관련 초기화 (첫번째 코드 그대로)
    bus = smbus.SMBus(7)
    mpu = MPU6050(bus)
    kalman_x = KalmanFilter(Q=0.001, R=0.1)
    kalman_y = KalmanFilter(Q=0.001, R=0.1)
    # 내부 좌표계: (x, y) 단위 m, 출발지는 (8,0) (출력 시: (y,x))
    position = np.array([0.0, 8.0])
    velocity = np.array([0.0, 0.0])
    # 라인트래킹 시작 시 가속도계 기준 시작 위치 재설정
    start_position = position.copy()
    angle = 0.0
    alpha = 0.1
    gravity = 9.81
    prev_time_acc = time.time()

    # 상태 정의
    STATE_WAIT_START = 0   # 출발지 QR 코드 대기
    STATE_ACTIVE     = 1   # QR 인식 후 라인트래킹 활성 상태
    STATE_STOP       = 2   # 라인트래킹 중 QR 감지 시 정지 및 명령 대기
    state = STATE_WAIT_START
    start_active_time = None

    try:
        while True:
            # --- 영상 처리 및 PID dt 계산 ---
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break

            # --- 가속도계 센서 업데이트 (첫번째 코드 그대로) ---
            current_time_acc = time.time()
            dt_acc = current_time_acc - prev_time_acc
            prev_time_acc = current_time_acc

            accel = mpu.get_accel_data()    # 단위: g
            gyro = mpu.get_gyro_data()      # 단위: 센서 설정에 따라
            angle += gyro['z'] * dt_acc
            accel_x = alpha * accel['x']
            accel_y = alpha * accel['y']
            accel_world_x = accel_x * math.cos(angle) - accel_y * math.sin(angle)
            accel_world_y = accel_x * math.sin(angle) + accel_y * math.cos(angle)
            accel_world_x *= gravity
            accel_world_y *= gravity
            raw_vel_x = velocity[0] + accel_world_x * dt_acc
            raw_vel_y = velocity[1] + accel_world_y * dt_acc
            velocity[0] = kalman_x.update(raw_vel_x, dt_acc)
            velocity[1] = kalman_y.update(raw_vel_y, dt_acc)
            position[0] += velocity[0] * dt_acc
            position[1] += velocity[1] * dt_acc
            if abs(accel_world_x) < 0.02 and abs(accel_world_y) < 0.02:
                velocity *= 0.95

            # --- 누적 이동거리 계산 (가속도계 기준, 단위: cm) ---
            distance_traveled = np.linalg.norm(position - start_position) * 100
            cv2.putText(frame, f"Distance: {distance_traveled:.1f} cm", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # === 상태별 동작 ===
            if state == STATE_WAIT_START:
                # 출발지 QR 인식 대기
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                cv2.putText(frame, "Waiting for Start QR", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                motor.MotorStop()
                if qr_detected:
                    print("출발지 QR 코드 감지 – 활성 상태 전환 (라인트래킹 시작)")
                    state = STATE_ACTIVE
                    start_active_time = current_time
                    start_position = position.copy()

            elif state == STATE_ACTIVE:
                # 누적 이동거리에 따라 목표 속도 변경
                if distance_traveled < 160:
                    target_speed = original_speed
                else:
                    target_speed = 8

                # 라인트래킹 도중 QR 코드 감지 시
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    # 만약 현재 가속도계상 위치가 시작 위치 (8,0)와 거의 동일하면
                    # MQTT 명령을 기다리지 않고 바로 라인트래킹을 계속한다.
                    if np.linalg.norm(position - start_position) < 0.1:
                        print("출발 위치에 머무름: QR 코드 감지 -> 자동 재시작 (MQTT 명령 없이)")
                        # 상태는 그대로 ACTIVE 유지
                    else:
                        print("라인트래킹 중 QR 코드 감지 – 정지 및 명령 대기")
                        motor.MotorStop()
                        state = STATE_STOP
                        qr_info = {"position": qr_centroid, "data": qr_data}
                        mqtt_client.publish(TOPIC_QR_INFO, json.dumps(qr_info))
                        time.sleep(1)
                        continue

                # 빨간색 라인 검출 및 PID 보정
                detected, centroid, mask = detect_red_line(frame)
                if detected and centroid is not None:
                    cx, cy = centroid
                    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                    cv2.line(frame, (frame_center, 0), (frame_center, frame_height),
                             (255, 0, 0), 2)
                    cv2.putText(frame, f"Centroid: ({cx}, {cy})", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    error = cx - frame_center
                    correction = pid.update(error, dt)
                    max_delta = 2
                    delta = correction - prev_correction
                    if abs(delta) > max_delta:
                        correction = prev_correction + max_delta * np.sign(delta)
                    prev_correction = correction

                    min_speed = 4
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
                    prev_correction *= 0.9
                    left_speed = target_speed + prev_correction
                    right_speed = target_speed - prev_correction
                    left_speed = max(4, min(100, left_speed))
                    right_speed = max(4, min(100, right_speed))
                    motor.MotorRun(0, 'forward', left_speed)
                    motor.MotorRun(1, 'forward', right_speed)
                    cv2.putText(frame, "Line not detected", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            elif state == STATE_STOP:
                motor.MotorStop()
                cv2.putText(frame, "Stopped, waiting for MQTT command", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                print("정지 상태: MQTT 명령 대기 중...")
                if mqtt_command is not None:
                    if mqtt_command.get('command', '').strip().upper() == "RESUME":
                        print("재시작 명령 수신 – 활성 상태로 전환")
                        state = STATE_ACTIVE
                        start_active_time = time.time()
                        start_position = position.copy()
                    else:
                        print("알 수 없는 명령. 계속 정지합니다.")
                    mqtt_command = None

            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Ctrl+C 입력, 모터를 정지합니다.")
    finally:
        motor.MotorStop()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    line_following_with_qr_and_accel()
