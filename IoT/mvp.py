import cv2
import numpy as np
import time
from PCA9685 import PCA9685
import paho.mqtt.client as mqtt
import json
import smbus

# --- 모터 제어 클래스 ---
class MotorDriver:
    def __init__(self):
        self.PWMA = 0   # 왼쪽 모터 속도(PWM) 핀
        self.AIN1 = 1   # 왼쪽 모터 방향 제어 핀 1
        self.AIN2 = 2   # 왼쪽 모터 방향 제어 핀 2
        self.PWMB = 5   # 오른쪽 모터 속도(PWM) 핀
        self.BIN1 = 3   # 오른쪽 모터 방향 제어 핀 1
        self.BIN2 = 4   # 오른쪽 모터 방향 제어 핀 2
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
   
# 가속도계 센서 보정을 위한 칼만 필터
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

# 가속도계 센서서
class MPU6050:
    def __init__(self, bus, address=0x68):
        self.bus = bus
        self.address = address
        self.gyro_scale = 131.0
        self.accel_scale = 16384.0
        self.init_sensor()
        self.calibrate_sensor()

    def init_sensor(self):
        # MPU6050 초기화: 전원 관리 및 감도 설정
        self.bus.write_byte_data(self.address, 0x6B, 0x00)  # 전원 관리 1 레지스터: 슬립 모드 해제
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
        x = (raw['x'] - self.accel_offset_x) / self.accel_scale
        y = (raw['y'] - self.accel_offset_y) / self.accel_scale
        # 센서 장착 방향에 따른 좌표 변환 (내부: x, y → 출력: 앞쪽(-y), 뒤쪽(+y), 오른쪽(+x), 왼쪽(-x))
        return {'x': y, 'y': -x}

# --- 빨간색 라인 검출 함수 ---

# 빨간색 범위 정의
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 100, 100])
upper_red2 = np.array([180, 255, 255])

def detect_red_line(frame):
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # 빨간색 마스크 생성
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)

    # 모폴로지 연산으로 노이즈 제거
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 컨투어 검출
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 유효한 컨투어 필터링
    valid_contours = [c for c in contours if cv2.contourArea(c) > 100]  # 노이즈 제거
   
    # 종횡비(Aspect Ratio)를 이용하여 얇은 선 찾기
    filtered_contours = []
    for c in valid_contours:
        x, y, w, h = cv2.boundingRect(c)  # 바운딩 박스 구하기
        aspect_ratio = w / float(h)  # 종횡비 계산

        if 0.1 < aspect_ratio < 0.5:  # 길고 얇은 선인지 확인
            filtered_contours.append(c)

    # 가장 적절한 컨투어 선택 (면적이 가장 작은 것)
    if filtered_contours:
        selected_contour = min(filtered_contours, key=cv2.contourArea)
        M = cv2.moments(selected_contour)

        if M["m00"] != 0:
            line_x = int(M["m10"] / M["m00"])
            line_y = int(M["m01"] / M["m00"])
            return True, (line_x, line_y), mask

    return False, None, mask

# --- QR 코드 검출 함수 ---
def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        pts = points[0]
        qr_x = int(np.mean(pts[:, 0]))
        qr_y = int(np.mean(pts[:, 1]))
        return True, (qr_x, qr_y), data
    return False, None, None

# --- MQTT 클라이언트 초기화 ---
BROKER = "broker.hivemq.com"
PORT = 1883
MQTT_TOPIC = "agv/qr_info"
TOPIC_AGV_TO_SIMPY = "agv/status"
TOPIC_SIMPY_TO_AGV = "simpy/commands"

mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

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

    frame_height, frame_width = frame.shape[:2]
    frame_center = frame_width // 2

    # ✅ I2C 버스 설정 (MPU6050 한 번만 초기화)
    try:
        bus = smbus.SMBus(7)  # Jetson Orin에서는 i2c-1 또는 i2c-7을 사용할 수도 있음
        mpu = MPU6050(bus)  # MPU6050 센서 객체 생성
    except Exception as e:
        print("MPU6050 초기화 실패:", e)
        return

    # ✅ PID 및 속도 설정
    pid = PID(kp=0.06, ki=0.0, kd=0.03)
    original_speed = 40  # 직진 시 기본 속도
    current_speed = original_speed
    prev_time = time.time()
    prev_correction = 0
    position_x = 0.0  # 이동 거리 (cm)
    velocity_x = 0.0  # 속도 (cm/s)

    # ✅ 상태 정의
    STATE_WAIT_START = 0
    STATE_STRAIGHT = 1
    STATE_QR_FIND = 2
    STATE_STOP = 3
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

            # ✅ 라인 트래킹 유지 (추가)
            detected, centroid, mask = detect_red_line(frame)
            if detected and centroid is not None:
                cx, cy = centroid
                error = cx - frame_center
                correction = pid.update(error, dt) * 0.5  # 보정값을 작게 적용
                
                # 보정값 제한
                max_delta = 2
                delta = correction - prev_correction
                if abs(delta) > max_delta:
                    correction = prev_correction + max_delta * np.sign(delta)
                prev_correction = correction
                
                # 속도 계산 및 적용
                min_speed = 4
                left_speed = max(min_speed, min(100, current_speed + correction))
                right_speed = max(min_speed, min(100, current_speed - correction))
                
                motor.MotorRun(0, 'forward', left_speed)
                motor.MotorRun(1, 'forward', right_speed)

            else:
                prev_correction *= 0.5
                left_speed = max(4, current_speed + prev_correction)
                right_speed = max(4, current_speed - prev_correction)
                motor.MotorRun(0, 'forward', left_speed)
                motor.MotorRun(1, 'forward', right_speed)

            # ✅ 상태에 따른 동작
            if state == STATE_WAIT_START:
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    print("출발지 QR 코드 감지 – 직진 주행 시작")
                    state = STATE_STRAIGHT
                motor.MotorStop()

            elif state == STATE_STRAIGHT:
                motor.MotorRun(0, 'forward', original_speed)
                motor.MotorRun(1, 'forward', original_speed)

                # ✅ 이동 거리 계산 (I2C 센서에서 값 읽기)
                accel_data = mpu.get_accel_data()
                accel_x = accel_data['x'] * 9.81  # m/s² 단위 변환
                velocity_x += accel_x * dt
                position_x += velocity_x * dt

                position = abs(position_x) * 10

                cv2.putText(frame, f"Distance: {position:.1f} cm", (10,60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

                if position >= 50:  # 100cm 도달하면 속도 줄이기
                    print("100cm 이동 완료 – QR 찾기 모드로 전환")
                    state = STATE_QR_FIND

            elif state == STATE_QR_FIND:
                current_speed = 8
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)

                if qr_detected:
                    print("QR 코드 감지 – 정지 및 명령 대기")
                    motor.MotorStop()
                    state = STATE_STOP
                    qr_info = {"position": qr_centroid, "data": qr_data}
                    mqtt_client.publish(MQTT_TOPIC, json.dumps(qr_info))
                    time.sleep(1)
                    continue

            elif state == STATE_STOP:
                motor.MotorStop()
                print("정지 상태: 명령을 입력하세요 (RESUME 입력 시 재시작):")
                cmd = input()
                if cmd.strip().upper() == "RESUME":
                    print("재시작 명령 수신 – 직진 모드로 전환")
                    state = STATE_STRAIGHT

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