import cv2
import numpy as np
import time
from PCA9685 import PCA9685
import paho.mqtt.client as mqtt
import json
import RPi.GPIO as GPIO
from ultralytics import YOLO

# 초음파 센서 설정
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

# MQTT 설정
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_QR_INFO = "agv/qr_info"         # QR 감지 시 정보 전송
TOPIC_OBSTACLE = "agv/obstacle"       # 장애물 감지 시 정보 전송
TOPIC_WARNING = "agv/warning"         # 사람 또는 박스 감지 시 경고 전송

mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

# YOLOv8 모델 로드
yolo_model = YOLO('yolov8n.pt')

# --- 모터 제어 클래스 ---
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
        return True, (cx, cy), data
    return False, None, None

# 회전 함수
def rotate_90_degrees(motor, direction):
    if direction == 'right':
        motor.MotorRun(0, 'forward', 80)
        motor.MotorRun(1, 'backward', 80)
    elif direction == 'left':
        motor.MotorRun(0, 'backward', 80)
        motor.MotorRun(1, 'forward', 80)
    time.sleep(1)  # 90도 회전에 필요한 시간 조정
    motor.MotorStop()

# 경로 설정
path = [
    {"type": "start", "location": "(7,0)"},
    {"type": "Stop", "location": "(6,0)"},
    {"type": "None", "location": "(5,0)"},
    {"type": "turn Right", "location": "(4,0)"},
    {"type": "None", "location": "(4,1)"},
    {"type": "None", "location": "(4,2)"},
    {"type": "turn left", "location": "(4,3)"},
    {"type": "Loading and turn right", "location": "(3,3)"},
    {"type": "turn left", "location": "(3,4)"},
    {"type": "obstacle", "location": "(2,4)"},
    {"type": "None", "location": "(1,4)"},
    {"type": "Unloading", "location": "(0,4)"}
]

# 라인트래킹 및 경로 수행 함수
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
    original_speed = 40  # 기본 속도
    slow_speed = 8       # QR 감지 시 속도
    target_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    current_step = 0

    try:
        while current_step < len(path):
            current_command = path[current_step]
            print(f"현재 명령: {current_command}")

            # YOLOv8 객체 감지
            results = yolo_model(frame)
            person_or_box_detected = False

            for result in results:
                for box in result.boxes:
                    class_id = box.cls[0].item()
                    label = yolo_model.names[int(class_id)]
                    if label in ['person', 'box']:  # 사람 또는 박스 감지
                        person_or_box_detected = True
                        break

            if person_or_box_detected:
                print("사람 또는 박스 감지! 모터 정지 및 경고 전송")
                motor.MotorStop()
                mqtt_client.publish(TOPIC_WARNING, json.dumps({"warning": "Person or box detected!"}))
                time.sleep(5)  # 5초 대기
                continue

            if current_command["type"] == "start":
                # 출발지 QR 코드 감지 후 출발
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    print("출발지 QR 코드 감지 – 출발")
                    target_speed = slow_speed
                    time.sleep(2)  # QR 감지 후 잠시 대기
                    target_speed = original_speed
                    current_step += 1

            elif current_command["type"] == "Stop":
                # 정지 명령
                print("정지 명령 수행")
                motor.MotorStop()
                time.sleep(2)  # 2초 대기
                current_step += 1

            elif current_command["type"] == "turn Right":
                # 오른쪽으로 90도 회전
                print("오른쪽으로 90도 회전")
                rotate_90_degrees(motor, 'right')
                current_step += 1

            elif current_command["type"] == "turn left":
                # 왼쪽으로 90도 회전
                print("왼쪽으로 90도 회전")
                rotate_90_degrees(motor, 'left')
                current_step += 1

            elif current_command["type"] == "Loading and turn right":
                # 10초 대기 후 오른쪽으로 회전
                print("10초 대기 후 오른쪽으로 회전")
                time.sleep(10)
                rotate_90_degrees(motor, 'right')
                current_step += 1

            elif current_command["type"] == "obstacle":
                # 장애물 감지 후 대기
                print("장애물 감지 후 대기")
                while get_distance() < 30:
                    time.sleep(1)
                current_step += 1

            elif current_command["type"] == "Unloading":
                # 10초 대기
                print("10초 대기")
                time.sleep(10)
                current_step += 1

            # 라인트래킹 수행
            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break

            detected, centroid, mask = detect_red_line(frame)
            if detected and centroid is not None:
                cx, cy = centroid
                error = cx - frame_center
                correction = pid.update(error, dt=0.1)
                left_speed = target_speed + correction
                right_speed = target_speed - correction
                motor.MotorRun(0, 'forward', left_speed)
                motor.MotorRun(1, 'forward', right_speed)
            else:
                motor.MotorStop()

            # 프레임 표시
            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Ctrl+C 입력, 모터를 정지합니다.")
    finally:
        motor.MotorStop()
        cap.release()
        cv2.destroyAllWindows()
        GPIO.cleanup()

if __name__ == '__main__':
    line_following_with_qr()