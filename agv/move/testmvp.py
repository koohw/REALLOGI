import cv2
import numpy as np
import time
import math
import json
from smbus2 import SMBus
import paho.mqtt.client as mqtt
from PCA9685 import PCA9685

# Jetson 환경에서 I2C 통신을 위해 smbus2를 사용 (만약 smbus가 설치되어 있다면 아래와 같이 변경 가능)
try:
    import smbus
except ImportError:
    from smbus2 import SMBus

# --- MQTT 설정 ---
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_QR_INFO = "agv/qr_info"
TOPIC_SIMPY_TO_AGV = "simpy/commands"

mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

def on_connect(client, userdata, flags, rc):
    client.subscribe(TOPIC_SIMPY_TO_AGV)

def on_message(client, userdata, msg):
    command = json.loads(msg.payload)
    if command.get('command') == 'STOP':
        print("AGV 정지 명령 수신")
    elif command.get('command') == 'RESUME':
        print("AGV 재시작 명령 수신")

# --- 모터 제어 클래스 (mvp.py와 distance.py 동일) ---
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

# --- PID 컨트롤러 (mvp.py와 distance.py 동일) ---
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

# --- MPU6050 클래스 (mvp.py와 distance.py에서 사용한 보정 및 초기화 방식) ---
class MPU6050:
    def __init__(self, bus, address=0x68):
        self.bus = bus
        self.address = address
        self.gyro_scale = 131.0
        self.accel_scale = 16384.0
        self.init_sensor()
        self.calibrate_sensor()

    def init_sensor(self):
        # MPU6050 초기화: 전원 관리, 감도 설정
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
        # 센서 장착 방향에 따른 좌표 변환 (내부: x, y → 출력: 앞쪽(-y), 뒤쪽(+y), 오른쪽(+x), 왼쪽(-x))
        return {'x': y, 'y': -x}

    def get_raw_gyro_data(self):
        z = self.read_i2c_word(0x47)
        return {'z': z}

    def get_gyro_data(self):
        raw = self.get_raw_gyro_data()
        z = (raw['z'] - self.gyro_offset_z) / self.gyro_scale
        return {'z': -z}

# --- 빨간색 라인 검출 함수 (mvp.py와 동일) ---
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

# --- QR 코드 검출 함수 (mvp.py와 동일) ---
def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        pts = points[0]
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        return True, (cx, cy), data
    return False, None, None

# --- 메인 함수 ---
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

    # I2C 버스 및 MPU6050 초기화 (가속도계/자이로 센서)
    bus = smbus.SMBus(1)
    mpu = MPU6050(bus)

    # PID 및 속도 설정 (mvp.py의 값 사용)
    pid = PID(kp=0.1, ki=0.0, kd=0.01)
    original_speed = 40  # 초기 목표 속도 (cm/s)
    target_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    # 가속도계 기반 거리 및 속도 측정을 위한 변수 (distance.py 방식)
    velocity_forward = 0.0  # 단위: m/s
    position_forward = 0.0  # 단위: m

    # 상태 정의
    STATE_WAIT_START = 0   # 출발지 QR 대기
    STATE_ACTIVE     = 1   # 라인트래킹 중
    STATE_STOP       = 2   # 정지 및 명령 대기
    state = STATE_WAIT_START

    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break

            # --- 가속도계 센서를 통한 거리/속도 통합 (distance.py 방식) ---
            accel_data = mpu.get_accel_data()
            # distance.py에서는 get_accel_data()['x']를 사용 (단위: g)를 m/s²로 변환
            accel_forward = accel_data['x'] * 9.81  # m/s²
            new_velocity = velocity_forward + accel_forward * dt
            # 평균 속도로 적분
            position_forward += (velocity_forward + new_velocity) / 2 * dt
            velocity_forward = new_velocity
            # cm 단위로 변환
            distance_traveled = abs(position_forward) * 100

            cv2.putText(frame, f"Distance: {distance_traveled:.1f} cm", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # --- 상태별 동작 ---
            if state == STATE_WAIT_START:
                # 출발지 QR 인식 대기
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                cv2.putText(frame, "Waiting for Start QR", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                motor.MotorStop()
                if qr_detected:
                    print("출발지 QR 코드 감지 – 활성 상태 전환 (라인트래킹 시작)")
                    state = STATE_ACTIVE
                    # 활성 시 가속도계 기준 초기화
                    velocity_forward = 0.0
                    position_forward = 0.0

            elif state == STATE_ACTIVE:
                # 누적 이동거리에 따라 목표 속도 변경
                if distance_traveled < 160:
                    target_speed = original_speed
                else:
                    target_speed = 8

                # 라인트래킹 도중 QR 코드가 감지되면 정지 및 STATE_STOP 전환
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    print("라인트래킹 중 QR 코드 감지 – 정지 및 명령 대기")
                    motor.MotorStop()
                    state = STATE_STOP
                    # MQTT로 QR 정보 전송
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
                    # 보정값의 급격한 변화 제한
                    max_delta = 2
                    delta = correction - prev_correction
                    if abs(delta) > max_delta:
                        correction = prev_correction + max_delta * np.sign(delta)
                    prev_correction = correction

                    # 두 모터 모두 전진시키되, 속도 차이로 회전 보정
                    min_speed = 4
                    left_speed = max(min_speed, min(100, target_speed + correction))
                    right_speed = max(min_speed, min(100, target_speed - correction))

                    motor.MotorRun(0, 'forward', left_speed)
                    motor.MotorRun(1, 'forward', right_speed)
                    cv2.putText(frame, f"Line Tracking: L {left_speed:.1f}, R {right_speed:.1f}",
                                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    print(f"[ACTIVE] error: {error:.2f}, correction: {correction:.2f}, L: {left_speed:.1f}, R: {right_speed:.1f}")
                else:
                    # 라인 미검출 시 이전 보정값을 감쇠하며 전진
                    prev_correction *= 0.9
                    left_speed = max(4, target_speed + prev_correction)
                    right_speed = max(4, target_speed - prev_correction)
                    motor.MotorRun(0, 'forward', left_speed)
                    motor.MotorRun(1, 'forward', right_speed)
                    cv2.putText(frame, "Line not detected", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            elif state == STATE_STOP:
                # 정지 상태: 모터 정지 후 명령 대기
                motor.MotorStop()
                cv2.putText(frame, "Stopped, waiting for command", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                print("정지 상태: 명령을 입력하세요 (RESUME 입력 시 재시작):")
                cmd = input()
                if cmd.strip().upper() == "RESUME":
                    print("재시작 명령 수신 – 활성 상태로 전환")
                    state = STATE_ACTIVE
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
