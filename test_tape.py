import cv2
import numpy as np
import time
from PCA9685 import PCA9685
import paho.mqtt.client as mqtt
import json

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

# --- 메인 라인트래킹 및 QR 코드 감지 함수 ---
def line_following_with_qr():
    motor = MotorDriver()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    # 카메라 밝기를 낮춰서 빛 반사 문제를 보정 (환경에 따라 값 조정)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.2)
    # 필요 시 노출도 설정도 추가할 수 있습니다.
    # cap.set(cv2.CAP_PROP_EXPOSURE, -4)
   
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    ret, frame = cap.read()
    if not ret:
        print("프레임을 읽을 수 없습니다.")
        return

    frame_height, frame_width = frame.shape[:2]
    frame_center = frame_width // 2

    # PID 및 주행 속도 설정
    pid = PID(kp=0.1, ki=0.0, kd=0.01)
    original_speed = 10    # 원래 기본 속도
    base_speed = original_speed
    last_speed_update_time = time.time()  # 속도 변경 타이머
    prev_time = time.time()
    prev_correction = 0

    try:
        while True:
            current_time = time.time()
            ret, frame = cap.read()
            if not ret:
                print("프레임 읽기 실패")
                break

            # QR 코드 감지
            qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
            if qr_detected:
                # QR 코드 감지 시 기본 속도를 원래 값으로 재설정
                base_speed = original_speed
                last_speed_update_time = current_time  # 타이머도 재설정
                cv2.putText(frame, "QR Code Detected", (10, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                current_speed = base_speed * 0.5  # QR 인식 시 속도는 낮춤
                qr_info = {"position": qr_centroid, "data": qr_data}
                mqtt_client.publish(MQTT_TOPIC, json.dumps(qr_info))
                print(f"QR Code 정보 전송: {qr_info}")
                time.sleep(1)  # QR 인식 후 잠시 대기
            else:
                # QR 코드 미감지 시 2초마다 속도를 10으로 느리게 변경
                if current_time - last_speed_update_time >= 2.2:
                    base_speed = 8
                    last_speed_update_time = current_time
                    print("2초 경과: base_speed를 10으로 설정함.")
                current_speed = base_speed

            # 빨간색 라인 검출
            detected, centroid, mask = detect_red_line(frame)
            dt = current_time - prev_time
            prev_time = current_time

            if detected and centroid is not None:
                cx, cy = centroid
                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                cv2.line(frame, (frame_center, 0), (frame_center, frame_height), (255, 0, 0), 2)
                cv2.putText(frame, f"Centroid: ({cx}, {cy})", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                error = cx - frame_center
                correction = pid.update(error, dt)
                # 보정값의 급격한 변화 제한
                max_delta = 5
                delta = correction - prev_correction
                if abs(delta) > max_delta:
                    correction = prev_correction + max_delta * np.sign(delta)
                prev_correction = correction

                left_speed = current_speed + correction
                right_speed = current_speed - correction
                left_speed = max(0, min(100, left_speed))
                right_speed = max(0, min(100, right_speed))

                motor.MotorRun(0, 'forward', left_speed)
                motor.MotorRun(1, 'forward', right_speed)

                cv2.putText(frame, f"Error: {error:.2f}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, f"LSpeed: {left_speed:.1f} RSpeed: {right_speed:.1f}", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                print(f"error: {error:.2f}, correction: {correction:.2f}, left_speed: {left_speed:.1f}, right_speed: {right_speed:.1f}")
            else:
                # 라인을 찾지 못한 경우: 이전 보정값을 서서히 감쇠하여 부드러운 탐색 동작 수행
                prev_correction *= 0.9
                left_speed = base_speed + prev_correction
                right_speed = base_speed - prev_correction
                # 탐색 시에도 기본 속도의 50% 정도로 낮춰 부드럽게 회전
                left_speed = max(0, min(100, left_speed * 0.01))
                right_speed = max(0, min(100, right_speed * 0.01))
                motor.MotorRun(0, 'forward', left_speed)
                motor.MotorRun(1, 'forward', right_speed)
                cv2.putText(frame, "Red line not detected", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                print("빨간 라인을 찾을 수 없습니다.")

            cv2.imshow("Frame", frame)
            # cv2.imshow("Mask", mask)

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


