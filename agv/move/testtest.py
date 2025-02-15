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
TOPIC_QR_INFO = "agv/qr_info"
TOPIC_SIMPY_TO_AGV = "simpy/commands"

# MQTT로 받은 전체 경로를 저장할 전역 리스트
mqtt_received_path = []

def on_connect(client, userdata, flags, rc):
    print("[MQTT] on_connect rc =", rc)
    client.subscribe(TOPIC_SIMPY_TO_AGV)
    print(f"[MQTT] Subscribed to topic: {TOPIC_SIMPY_TO_AGV}")

def on_message(client, userdata, msg):
    """
    시뮬레이션에서 "simpy/commands" 토픽으로 전송되는 메시지를 수신.
    예) {"command": "PATH", "data": {"full_path": [[8, 0], [8, 1], ...]}}
    """
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
            print("[MQTT] PATH 명령 수신, full_path =", full_path)
            # 여기서 full_path를 실제 경로 리스트로 저장
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
        else:   # 오른쪽 모터
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

# --- PID 컨트롤러 ---
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

# --- MPU6050 클래스 (건들지 말 것) ---
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
        self.bus.write_byte_data(self.address, 0x1B, 0x00)  # 자이로 감도 설정
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
        low = self.bus.read_byte_data(self.address, reg+1)
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
        # 센서 장착 방향에 따른 좌표 변환
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

    # (기존에 목적지 좌표를 input으로 받던 부분 제거/주석)
    # MQTT로부터 수신한 경로(mqtt_received_path)를 사용할 것이라 가정
    # 필요에 따라 라인트래킹 + 경로 주행 로직을 직접 연동해야 합니다.
    
    # 가속도, PID 등 기존 그대로
    ret, frame = cap.read()
    if not ret:
        print("프레임을 읽을 수 없습니다.")
        return

    frame_height, frame_width = frame.shape[:2]
    frame_center = frame_width // 2

    # 예시) 만약 MQTT로부터 받은 경로를 한 칸씩 소진하며 이동하고 싶다면,
    # 아래처럼 사용 가능 (단, line_following + 경로 주행은 별도 설계 필요)
    # e.g., destinations = mqtt_received_path

    try:
        bus = SMBus(7)
        mpu = MPU6050(bus)
    except Exception as e:
        print("MPU6050 초기화 실패:", e)
        return

    pid = PID(kp=0.06, ki=0.0, kd=0.03)
    original_speed = 40
    current_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    position_x = 0.0
    velocity_x = 0.0

    STATE_WAIT_START = 0
    STATE_STRAIGHT   = 1
    STATE_QR_FIND    = 2
    STATE_STOP       = 3
    state = STATE_WAIT_START

    waypoint_distance = 50
    error_margin = 5

    print("시스템 시작: MQTT로부터 PATH 명령을 수신하거나, 출발지 QR 코드를 보여주세요.")
    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break

            accel_data = mpu.get_accel_data()
            accel_forward = accel_data['x'] * 9.81
            new_velocity_x = velocity_x + accel_forward * dt
            position_x += (velocity_x + new_velocity_x) / 2 * dt
            velocity_x = new_velocity_x
            distance_traveled = abs(position_x) * 100

            cv2.putText(frame, f"Distance: {distance_traveled:.1f} cm",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # (이하는 기존 라인트래킹, QR 감지 로직)
            if state == STATE_WAIT_START:
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                cv2.putText(frame, "Waiting for Start QR", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                motor.MotorStop()
                if qr_detected:
                    print("출발지 QR 코드 감지 – 직진 주행 시작")
                    state = STATE_STRAIGHT
                    position_x = 0.0
                    velocity_x = 0.0

            elif state == STATE_STRAIGHT:
                detected, centroid, mask = detect_red_line(frame)
                if detected and centroid is not None:
                    cx, cy = centroid
                    error = cx - frame_center
                    correction = pid.update(error, dt) * 0.5
                    max_delta = 2
                    delta = correction - prev_correction
                    if abs(delta) > max_delta:
                        correction = prev_correction + max_delta * np.sign(delta)
                    prev_correction = correction

                    min_speed = 4
                    left_speed = max(min_speed, min(100, current_speed + correction))
                    right_speed = max(min_speed, min(100, current_speed - correction))
                    motor.MotorRun(0, 'forward', left_speed)
                    motor.MotorRun(1, 'forward', right_speed)
                else:
                    motor.MotorRun(0, 'forward', current_speed)
                    motor.MotorRun(1, 'forward', current_speed)

                if abs(distance_traveled - waypoint_distance) <= error_margin:
                    print("목적지 도착 임박: 속도 감속 및 QR 감지 모드 전환")
                    current_speed = 8
                    state = STATE_QR_FIND

            elif state == STATE_QR_FIND:
                motor.MotorRun(0, 'forward', current_speed)
                motor.MotorRun(1, 'forward', current_speed)
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    print("목적지 QR 코드 감지 – MQTT 전송 및 정지")
                    motor.MotorStop()
                    # 예: 여기서는 QR 코드를 감지하면 TOPIC_QR_INFO로 publish
                    # 실제 시뮬레이션 전체 경로와 연동하려면, mqtt_received_path를 참고해
                    # 다음 waypoint로 넘어가는 등 상태 설계를 해야 합니다.
                    dest_info = {"destination": [99,99], "qr_data": qr_data}
                    mqtt_client.publish(TOPIC_QR_INFO, json.dumps(dest_info))
                    time.sleep(1)
                    state = STATE_STOP

            elif state == STATE_STOP:
                motor.MotorStop()
                cv2.putText(frame, "Stopped, waiting for command", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                print("정지 상태: 명령을 입력하세요 (RESUME / ROTATE_LEFT / ROTATE_RIGHT):")
                cmd = input()
                if cmd.strip().upper() == "RESUME":
                    print("재가동 명령 수신 – 직진 모드 전환")
                    # 원래는 다음 목적지 이동 로직을 구현해야 함
                    position_x = 0.0
                    velocity_x = 0.0
                    current_speed = original_speed
                    state = STATE_STRAIGHT
                elif cmd.strip().upper() == "ROTATE_LEFT":
                    print("좌측 회전 명령 수신 – 회전 수행")
                    motor.MotorRun(0, 'backward', 30)
                    motor.MotorRun(1, 'forward', 30)
                    time.sleep(0.5)
                    motor.MotorStop()
                    state = STATE_STRAIGHT
                elif cmd.strip().upper() == "ROTATE_RIGHT":
                    print("우측 회전 명령 수신 – 회전 수행")
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
        print("Ctrl+C 입력, 모터를 정지합니다.")
    finally:
        motor.MotorStop()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    line_following_with_qr()
