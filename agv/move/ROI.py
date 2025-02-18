#!/usr/bin/python
import cv2
import numpy as np
import time
from PCA9685 import PCA9685
import paho.mqtt.client as mqtt
import json
import smbus
import math
import RPi.GPIO as GPIO

# ------------------------
# 하드웨어/센서 초기화
# ------------------------
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
    return round(distance, 2)

# ------------------------
# MQTT 설정
# ------------------------
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_QR_INFO = "agv/qr_info"         # QR 감지 시 정보 전송
TOPIC_SIMPY_TO_AGV = "simpy/commands"  # 원격 명령 수신
TOPIC_OBSTACLE = "agv/obstacle"        # 장애물 감지 시 전송

mqtt_received_path = []      # MQTT로 받은 전체 경로 (PATH 수신 여부 확인용)
mqtt_received_command = None # MQTT로 받은 원격 명령 (STOP, RESUME, TURN)
mqtt_path_received = False   # PATH 명령 수신 여부

def on_connect(client, userdata, flags, rc):
    print("[MQTT] on_connect rc =", rc)
    client.subscribe(TOPIC_SIMPY_TO_AGV)
    print(f"[MQTT] Subscribed to topic: {TOPIC_SIMPY_TO_AGV}")

def on_message(client, userdata, msg):
    global mqtt_received_path, mqtt_received_command, mqtt_path_received
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
            print("[MQTT] 알 수 없는 명령:", cmd)
    except Exception as e:
        print("[MQTT] on_message 오류:", e)

mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

# ------------------------
# 모터 제어 클래스 (PCA9685 기반)
# ------------------------
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

# ------------------------
# PID 컨트롤러 클래스
# ------------------------
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

# ------------------------
# 영상 처리 함수들 (빨간색 라인 & QR 코드 검출)
# ------------------------
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 100, 100])
upper_red2 = np.array([180, 255, 255])

def detect_red_line(frame):
    blurred = cv2.GaussianBlur(frame, (5,5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    kernel = np.ones((5,5), np.uint8)
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

def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        pts = points[0]
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        return True, (cx, cy), data
    return False, None, None

# ------------------------
# 회전 함수 (90도 회전)
# ------------------------
def right_90_rotate(motor):
    motor.MotorRun(0, 'forward', 80)
    motor.MotorRun(1, 'backward', 80)
    time.sleep(1)  # 90도 회전에 필요한 시간 (튜닝 필요)
    motor.MotorStop()

def left_90_rotate(motor):
    motor.MotorRun(0, 'backward', 80)
    motor.MotorRun(1, 'forward', 80)
    time.sleep(1)
    motor.MotorStop()

# ------------------------
# 라인트래킹 및 경로(세그먼트) 제어 함수
# ------------------------
def line_following_with_qr():
    global mqtt_received_command, mqtt_received_path

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
        print("프레임 읽기 실패")
        return

    frame_height, frame_width = frame.shape[:2]
    frame_center = frame_width // 2

    pid = PID(kp=0.1, ki=0.0, kd=0.01)
    original_speed = 40  # 주행 속도 (cm/s)
    slow_speed = 8       # QR 감지 모드에서 감속 속도

    # ------------------------
    # 세그먼트 설정 (요구하신 경로)
    # ------------------------
    segments = [
        {"distance":600, "action":"right",    "expected_qr": (4,0)},
        {"distance":450, "action":"left",     "expected_qr": (4,3)},
        {"distance":150, "action":"right",    "expected_qr": (3,3), "stop_time":10},
        {"distance":0,   "action":"left",     "expected_qr": (3,4)},
        {"distance":450, "action":"complete", "expected_qr": (0,4)}
    ]
    current_seg = 0
    seg_start_time = time.time()  # 세그먼트 시작 시각

    # 상태: "DRIVE" = 주행 중, "WAIT_RESUME" = QR 검출 후 RESUME 대기
    STATE_DRIVE = 0
    STATE_WAIT_RESUME = 1
    state = STATE_DRIVE

    prev_time = time.time()
    prev_correction = 0

    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            # 장애물 감지 (30cm 이내)
            if get_distance() < 30:
                print("장애물 감지!")
                motor.MotorStop()
                mqtt_client.publish(TOPIC_OBSTACLE, json.dumps({"distance": get_distance()}))
                time.sleep(1)
                continue

            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break

            # 원격 명령 처리 (STOP, RESUME, TURN)
            if mqtt_received_command is not None:
                if mqtt_received_command == 'STOP':
                    print("Remote STOP 명령 실행")
                    motor.MotorStop()
                    state = STATE_WAIT_RESUME
                    mqtt_received_command = None
                    cv2.putText(frame, "REMOTE STOP", (10, 150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                    cv2.imshow("Frame", frame)
                    cv2.waitKey(1)
                    continue
                # TURN 명령은 별도 처리 (필요시)
                elif mqtt_received_command == 'TURN':
                    print("Remote TURN 명령 실행")
                    motor.MotorStop()
                    right_90_rotate(motor)
                    mqtt_received_command = None

            # 상태별 동작 처리
            if state == STATE_DRIVE:
                # 현재 세그먼트 정보
                seg = segments[current_seg]
                # 대략 주행한 거리 (초당 original_speed cm 가정)
                seg_distance = (current_time - seg_start_time) * original_speed

                # 주행 속도 결정: 아직 목표 거리 미달이면 원래 속도, 달성 후 감속
                if seg_distance < seg["distance"]:
                    target_speed = original_speed
                else:
                    target_speed = slow_speed
                    # QR 검출 시도 (감속 상태에서)
                    qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                    if qr_detected:
                        print(f"QR 감지: {qr_data} at {qr_centroid}")
                        motor.MotorStop()
                        # MQTT로 QR 정보 전송
                        mqtt_client.publish(TOPIC_QR_INFO, json.dumps({"position": qr_centroid, "data": qr_data}))
                        # QR 검출 후 RESUME 명령을 기다리기 위해 상태 전환
                        state = STATE_WAIT_RESUME
                        # 화면에 메시지 표시
                        cv2.putText(frame, "QR detected - waiting for RESUME", (10, 120),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)

                # 라인트래킹: 빨간색 라인 검출 및 PID 보정
                detected, centroid, mask = detect_red_line(frame)
                if detected and centroid is not None:
                    cx, cy = centroid
                    error = cx - frame_center
                    correction = pid.update(error, dt)
                    max_delta = 2
                    delta = correction - prev_correction
                    if abs(delta) > max_delta:
                        correction = prev_correction + max_delta * np.sign(delta)
                    prev_correction = correction
                    min_speed = 10
                    left_speed = max(min_speed, min(100, target_speed + correction))
                    right_speed = max(min_speed, min(100, target_speed - correction))
                    motor.MotorRun(0, 'forward', left_speed)
                    motor.MotorRun(1, 'forward', right_speed)
                    cv2.putText(frame, f"Tracking: L {left_speed:.1f}, R {right_speed:.1f}",
                                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                else:
                    print("빨간색 라인 미검출!")
                    motor.MotorStop()
                    mqtt_client.publish(TOPIC_OBSTACLE, json.dumps({"emergency": True}))
                    time.sleep(1)
                    continue

                # 화면에 세그먼트 및 주행 거리 표시
                cv2.putText(frame, f"Seg {current_seg+1}/{len(segments)}  {seg_distance:.1f}/{seg['distance']} cm",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

            elif state == STATE_WAIT_RESUME:
                # QR 감지 후 모터 정지 상태 – RESUME 명령 대기
                cv2.putText(frame, "Waiting for RESUME command", (10, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
                if mqtt_received_command == "RESUME":
                    print(f"RESUME 수신 – 세그먼트 {current_seg+1} 동작 실행")
                    mqtt_received_command = None
                    seg = segments[current_seg]
                    # 만약 해당 세그먼트에 정지 시간이 설정되어 있으면
                    if "stop_time" in seg and seg["stop_time"] > 0:
                        print(f"{seg['stop_time']}초 정지")
                        motor.MotorStop()
                        time.sleep(seg["stop_time"])
                    # 지정 동작 수행
                    if seg["action"] == "right":
                        print("오른쪽 90도 회전 수행")
                        right_90_rotate(motor)
                    elif seg["action"] == "left":
                        print("왼쪽 90도 회전 수행")
                        left_90_rotate(motor)
                    elif seg["action"] == "complete":
                        print("최종 구간: 정지 후 적재 완료 메시지 전송")
                        motor.MotorStop()
                        mqtt_client.publish("agv/loading_complete", json.dumps({"status": "complete"}))
                        break
                    # 다음 세그먼트로 전환
                    current_seg += 1
                    if current_seg >= len(segments):
                        print("경로 완료")
                        break
                    state = STATE_DRIVE
                    seg_start_time = time.time()  # 다음 구간 주행 거리 초기화

            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Ctrl+C 입력, 모터 정지")
    finally:
        motor.MotorStop()
        cap.release()
        cv2.destroyAllWindows()
        GPIO.cleanup()

# ------------------------
# 메인 함수: MQTT PATH 수신 후 라인트래킹/경로 제어 시작
# ------------------------
def main():
    global mqtt_path_received
    print("[MAIN] MQTT에서 PATH 수신 대기 중...")
    while not mqtt_path_received:
        time.sleep(1)
    print("[MAIN] PATH 수신됨! 라인트래킹 시작...")
    line_following_with_qr()

if __name__ == '__main__':
    main()
