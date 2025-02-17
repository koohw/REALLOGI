import cv2
import numpy as np
import time
from PCA9685 import PCA9685
import paho.mqtt.client as mqtt
import json
import smbus
import math
import RPi.GPIO as GPIO

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
TOPIC_SIMPY_TO_AGV = "simpy/commands"
TOPIC_OBSTACLE = "agv/obstacle"       # 장애물 감지 시 정보 전송

mqtt_received_path = []  # MQTT로 받은 전체 경로 리스트
mqtt_received_command = None # MQTT로 받은 원격 명령 (STOP, RESUME, TURN)
mqtt_path_received = False    # PATH 명령이 수신되었는지 여부

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
            # 여기서 "path" 키를 사용합니다.
            path = payload.get('data', {}).get('path', [])
            print("[MQTT] PATH 명령 수신 =", path)
            mqtt_received_path = path
            mqtt_path_received = True  # 경로 수신 플래그
        else:
            print("[MQTT] 알 수 없는 명령 수신:", cmd)
    except Exception as e:
        print("[MQTT] on_message 오류:", e)

# ------------------------
# [MQTT 클라이언트 초기화]
# ------------------------
mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

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
def rotate_90_degrees(motor):
    motor.MotorRun(0, 'forward', 80)
    motor.MotorRun(1, 'backward', 80)
    time.sleep(1)
    motor.MotorStop()

# ------------------------
# [메인 함수: 라인트래킹]
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
        print("프레임을 읽을 수 없습니다.")
        return
    frame_height, frame_width = frame.shape[:2]
    frame_center = frame_width // 2
    pid = PID(kp=0.1, ki=0.0, kd=0.01)
    original_speed = 40
    slow_speed = 8
    target_speed = original_speed
    prev_time = time.time()
    prev_correction = 0
    STATE_WAIT_START = 0
    STATE_ACTIVE     = 1
    STATE_STOP       = 2
    state = STATE_WAIT_START
    start_active_time = None
    distance_traveled = 0
    last_distance_print = time.time()

    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time
            distance = get_distance()
            if current_time - last_distance_print >= 1.0:
                print(f"[DEBUG] 초음파 센서 측정 거리: {distance} cm")
                last_distance_print = current_time

            if distance < 30:
                print("이상 물체가 감지됩니다. 카메라를 확인해주세요.")
                motor.MotorStop()
                mqtt_client.publish(TOPIC_OBSTACLE, json.dumps({"distance": distance}))
                time.sleep(1)
                continue

            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break
            
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
                elif mqtt_received_command == 'RESUME':
                    print("Remote RESUME 명령 실행")
                    state = STATE_ACTIVE
                    if start_active_time is None:
                        start_active_time = current_time
                    mqtt_received_command = None
                elif mqtt_received_command == 'TURN':
                    print("Remote TURN 명령 실행")
                    motor.MotorStop()
                    rotate_90_degrees(motor)
                    mqtt_received_command = None

            if state == STATE_WAIT_START:
                    if mqtt_received_path:
                        print("MQTT 통신 완료 – 활성 상태 전환 (라인트래킹 시작)")
                        state = STATE_ACTIVE
                        start_active_time = current_time
                    else:
                        cv2.putText(frame, "Waiting for MQTT", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        motor.MotorStop()
            elif state == STATE_ACTIVE:
                distance_traveled = (current_time - start_active_time) * original_speed
                cv2.putText(frame, f"Distance: {distance_traveled:.1f} cm", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                if distance_traveled < 150:
                    target_speed = original_speed
                else:
                    target_speed = slow_speed
                if distance_traveled >= 150:
                    qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                    if qr_detected:
                        print("QR DETECT -> 90 TURN")
                        motor.MotorStop()
                        qr_info = {"position": qr_centroid, "data": qr_data}
                        mqtt_client.publish(TOPIC_QR_INFO, json.dumps(qr_info))
                        rotate_90_degrees(motor)
                        time.sleep(1)
                        start_active_time = time.time()
                        target_speed = original_speed
                        continue
                
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
                    mqtt_client.publish(TOPIC_OBSTACLE, json.dumps({"emergency": True}))
                    time.sleep(1)
                    continue
            elif state == STATE_STOP:
                motor.MotorStop()
                cv2.putText(frame, "Stopped, waiting for command", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                print("정지 상태: RESUME 입력 시 재가동")
                cmd = input()
                if cmd.strip().upper() == "RESUME":
                    print("재시작 명령 수신 – 활성 상태로 전환")
                    state = STATE_ACTIVE
                    start_active_time = time.time()
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
        GPIO.cleanup()

def main():
    global mqtt_path_received
    print("[MAIN] MQTT에서 PATH를 기다리는 중...")
    while not mqtt_path_received:
        time.sleep(1)
    print("[MAIN] PATH 수신됨! 라인트래킹 시작...")
    line_following_with_qr()

if __name__ == '__main__':
    main()
