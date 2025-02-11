import cv2
import numpy as np
import time
from PCA9685 import PCA9685
import paho.mqtt.client as mqtt
import json

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

# --- MQTT 클라이언트 초기화 ---
BROKER = "broker.hivemq.com"
PORT = 1883
MQTT_TOPIC = "agv/qr_info"

mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

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
    original_speed = 10  # 직진 시 기본 속도 (단위: cm/s로 가정)
    current_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    # 상태 정의
    STATE_WAIT_START = 0   # 시작 QR 코드 대기 (출발지: (8,0))
    STATE_STRAIGHT = 1     # 직진 주행
    STATE_LINE_TRACK = 2   # 누적 100cm 이상 이동 후 라인트래킹 (속도 8)
    STATE_STOP = 3         # 라인트래킹 도중 QR 인식 시 정지 후 명령 대기
    state = STATE_WAIT_START
    start_straight_time = None  # 직진 시작 시각 (누적 이동거리 측정을 위해)

    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break

            # 상태에 따라 동작 분기
            if state == STATE_WAIT_START:
                # 시작 QR 코드 인식 대기 (출발지에서 QR 인식되면 직진 모드로 전환)
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    print("출발지 QR 코드 감지 – 직진 주행 시작")
                    state = STATE_STRAIGHT
                    start_straight_time = current_time
                cv2.putText(frame, "Waiting for Start QR", (10,30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
                motor.MotorStop()

            elif state == STATE_STRAIGHT:
                # 직진 주행: 두 모터에 동일 속도 (original_speed)로 구동
                motor.MotorRun(0, 'forward', original_speed)
                motor.MotorRun(1, 'forward', original_speed)
                # 시뮬레이션: 직진 시작 시각부터 경과 시간에 따라 이동거리(단위: cm) 계산
                distance_traveled = (current_time - start_straight_time) * original_speed
                cv2.putText(frame, f"Distance: {distance_traveled:.1f} cm", (10,60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
                # 누적 이동거리가 100cm 이상이면 라인트래킹 모드 전환
                if distance_traveled >= 100:
                    print("100cm 이동 완료 – 라인트래킹 모드로 전환")
                    state = STATE_LINE_TRACK
                    prev_correction = 0

            elif state == STATE_LINE_TRACK:
                # 라인트래킹 모드: 속도 8로 주행
                current_speed = 8
                # 만약 QR 코드가 감지되면 정지 후 명령 대기 상태로 전환
                qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                if qr_detected:
                    print("라인 트래킹 중 QR 코드 감지 – 정지 및 명령 대기")
                    motor.MotorStop()
                    state = STATE_STOP
                    # MQTT로 QR 정보 전송
                    qr_info = {"position": qr_centroid, "data": qr_data}
                    mqtt_client.publish(MQTT_TOPIC, json.dumps(qr_info))
                    time.sleep(1)
                    continue

                # 빨간색 라인 검출 및 PID 보정
                detected, centroid, mask = detect_red_line(frame)
                if detected and centroid is not None:
                    cx, cy = centroid
                    cv2.circle(frame, (cx, cy), 5, (0,255,0), -1)
                    cv2.line(frame, (frame_center, 0), (frame_center, frame_height),
                             (255,0,0), 2)
                    cv2.putText(frame, f"Centroid: ({cx}, {cy})", (10,30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                    error = cx - frame_center
                    correction = pid.update(error, dt)
                    # 보정값의 급격한 변화 제한 (최대 변화량 max_delta)
                    max_delta = 2
                    delta = correction - prev_correction
                    if abs(delta) > max_delta:
                        correction = prev_correction + max_delta * np.sign(delta)
                    prev_correction = correction

                    # 양쪽 모터 모두 전진시키되, 속도 차이를 통해 회전 보정  
                    # (최소 속도(min_speed)를 유지하여 한쪽 모터가 0에 가까워지지 않도록 함)
                    min_speed = 4
                    left_speed = current_speed + correction
                    right_speed = current_speed - correction
                    if left_speed < min_speed:
                        left_speed = min_speed
                    if right_speed < min_speed:
                        right_speed = min_speed
                    left_speed = max(min_speed, min(100, left_speed))
                    right_speed = max(min_speed, min(100, right_speed))

                    motor.MotorRun(0, 'forward', left_speed)
                    motor.MotorRun(1, 'forward', right_speed)
                    cv2.putText(frame, f"Line Tracking: L {left_speed:.1f}, R {right_speed:.1f}",
                                (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                    print(f"error: {error:.2f}, correction: {correction:.2f}, "
                          f"left_speed: {left_speed:.1f}, right_speed: {right_speed:.1f}")
                else:
                    # 라인이 검출되지 않으면 이전 보정값을 서서히 감쇠하며 전진
                    prev_correction *= 0.9
                    left_speed = current_speed + prev_correction
                    right_speed = current_speed - prev_correction
                    if left_speed < 4:
                        left_speed = 4
                    if right_speed < 4:
                        right_speed = 4
                    motor.MotorRun(0, 'forward', left_speed)
                    motor.MotorRun(1, 'forward', right_speed)
                    cv2.putText(frame, "Line not detected", (10,30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

            elif state == STATE_STOP:
                # 정지 상태: 모터 정지 후 명령 대기 (여기서는 input()으로 RESUME 명령 수신)
                motor.MotorStop()
                cv2.putText(frame, "Stopped, waiting for command", (10,30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,0), 2)
                print("정지 상태: 명령을 입력하세요 (RESUME 입력 시 재시작):")
                cmd = input()
                if cmd.strip().upper() == "RESUME":
                    print("재시작 명령 수신 – 직진 모드로 전환")
                    state = STATE_STRAIGHT
                    start_straight_time = time.time()  # 이동거리 초기화
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
