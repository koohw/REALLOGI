import cv2
import numpy as np
import time
from PCA9685 import PCA9685
import paho.mqtt.client as mqtt
import json
import smbus
import math

# MQTT 설정
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_AGV_TO_SIMPY = "agv/status"
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

# --- 모터 제어 클래스 ---
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
        # motor가 None이면 모든 모터 정지
        if motor is None:
            self.pwm.setDutycycle(self.PWMA, 0)
            self.pwm.setDutycycle(self.PWMB, 0)
        elif motor == 0:
            self.pwm.setDutycycle(self.PWMA, 0)
        else:
            self.pwm.setDutycycle(self.PWMB, 0)

# --- PID 컨트롤러 클래스 ---
# 라인 트래킹 시 발생하는 오차를 보정하여 모터의 속도 차이를 조절함.
class PID:
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.prev_error = 0 # 이전 오차 누적
        self.integral = 0   # 적분값 누적적

    def update(self, error, dt):
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        output = self.kp * error + self.ki * self.integral + self.kd * derivative   # 보정값값
        self.prev_error = error # 이전 오차값 갱신.
        return output

# 가속도계 센서를 통해 현재위치 및 속도 계산하는 부분
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
        # dt가 0이면 나누기 에러 방지
        if dt > 0:
            self.velocity += K * (position_error / dt)
        self.P = (1 - K) * self.P
        return self.velocity  # Kalman Filter는 속도값을 보정한 후 반환

class MPU6050:
    def __init__(self, bus, address=0x68):
        self.bus = bus
        self.address = address
        self.gyro_scale = 131.0
        self.accel_scale = 16384.0
        self.init_sensor()
        self.calibrate_sensor()

    def init_sensor(self):
        # MPU6050 초기화: 전원 관리, 가속도, 자이로 감도 설정
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
        # 센서 보정 후 가속도값 계산 (g 단위)
        raw = self.get_raw_accel_data()
        # 보정: 보정치 제거 후 스케일 적용
        x = (raw['x'] - self.accel_offset_x) / self.accel_scale
        y = (raw['y'] - self.accel_offset_y) / self.accel_scale
        # 센서 장착 방향에 따라 좌표계를 변환 (내부: x, y)
        # 여기서는 센서 축을 변환하여, 추후 계산 시
        # 앞쪽(-y), 뒤쪽(+y), 오른쪽(+x), 왼쪽(-x)이 되도록 함
        return {'x': y, 'y': -x}

    def get_raw_gyro_data(self):
        z = self.read_i2c_word(0x47)
        return {'z': z}

    def get_gyro_data(self):
        raw = self.get_raw_gyro_data()
        z = (raw['z'] - self.gyro_offset_z) / self.gyro_scale
        # 부호 변경은 센서 장착 방향에 따라 조정
        return {'z': -z}


# --- 빨간색 라인 검출 함수 ---
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

# --- QR 코드 검출 함수 ---
def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        pts = points[0]
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        return True, (cx, cy), data # 검출 성공 시
    return False, None, None    # 검출 실패 시시


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

    # PID 및 속도 설정
    pid = PID(kp=0.1, ki=0.0, kd=0.01)
    original_speed = 40  # 출발지 QR 인식 후 초기 목표 속도 (예: 40 cm/s)
    target_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    # 가속도계 관련 초기화 (첫번째 코드 그대로)
    bus = smbus.SMBus(7)
    mpu = MPU6050(bus)
    kalman_x = KalmanFilter(Q=0.001, R=0.1)
    kalman_y = KalmanFilter(Q=0.001, R=0.1)
    # 내부 좌표계: (x, y) 단위: m, 출발지는 (8,0) 출력 (y,x) 순서를 위해 초기값 설정
    position = np.array([0.0, 8.0])
    velocity = np.array([0.0, 0.0])
    # 시작 위치(가속도계 기준): 라인트래킹 시작 시 재설정함
    start_position = position.copy()
    angle = 0.0
    alpha = 0.1
    gravity = 9.81
    prev_time_acc = time.time()

    # 상태 정의
    STATE_WAIT_START = 0   # 출발지 QR 코드 대기
    STATE_ACTIVE     = 1   # QR 인식 후 라인트래킹(항상 수행) 상태
    STATE_STOP       = 2   # 라인트래킹 중 QR 감지 시 정지 및 명령 대기
    state = STATE_WAIT_START
    start_active_time = None  # 활성 상태 시작 시각(거리 측정을 위한 기준)

    try:
        while True:
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
            gyro = mpu.get_gyro_data()      # 단위: (센서 설정에 따라) deg/s
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

            # --- 누적 이동거리 계산: 가속도계 센서를 이용 (단위: cm) ---
            # (라인트래킹 활성 시, 출발 시 재설정한 start_position 기준)
            distance_traveled = np.linalg.norm(position - start_position) * 100
            cv2.putText(frame, f"Distance: {distance_traveled:.1f} cm", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # 상태별 동작 분기
            if state == STATE_WAIT_START:
                # 출발지 QR 인식 대기
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                cv2.putText(frame, "Waiting for Start QR", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                motor.MotorStop()
                if qr_detected:
                    print("출발지 QR 코드 감지 – 활성 상태 전환 (라인트래킹 시작)")
                    state = STATE_ACTIVE
                    start_active_time = current_time  # 활성 상태 시작 시간 기록
                    start_position = position.copy()    # 가속도계 기준 시작 위치 재설정

            elif state == STATE_ACTIVE:
                # 누적 이동거리에 따라 목표 속도 변경
                if distance_traveled < 160:
                    target_speed = original_speed
                else:
                    target_speed = 8

                # 라인트래킹 도중 QR 코드가 감지되면 정지 및 STATE_STOP 전환
                # **출발지(거리 10cm 미만)에서는 QR 인식 후 바로 라인트래킹 수행**
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected and distance_traveled > 5:  # 이동거리 10cm 이상일 때만 명령 대기
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

                    # 두 모터 모두 전진시키되, 속도 차이를 통해 회전 보정  
                    # (최소 속도(min_speed)를 유지하여 한쪽 모터가 거의 멈추지 않도록 함)
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
                    # 라인 미검출 시 이전 보정값을 서서히 감쇠하며 전진
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
                # 정지 상태: 모터 정지 후 명령 대기 (여기서는 input()으로 RESUME 명령 수신)
                motor.MotorStop()
                cv2.putText(frame, "Stopped, waiting for command", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                print("정지 상태: 명령을 입력하세요 (RESUME 입력 시 재시작):")
                cmd = input()
                if cmd.strip().upper() == "RESUME":
                    print("재시작 명령 수신 – 활성 상태로 전환")
                    state = STATE_ACTIVE
                    start_active_time = time.time()  # 이동거리 기준 초기화
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
