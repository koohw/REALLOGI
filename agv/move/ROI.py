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
            full_path = payload.get('data', {}).get('full_path', [])
            print("[MQTT] PATH 명령 수신 =", full_path)
            mqtt_received_path = full_path
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
        # PCA9685 debug=False 설정 -> I2C 레지스터 로그가 뜨지 않도록 
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

# 회전 함수
def rotate_90_degrees(motor):
    motor.MotorRun(0, 'forward', 50)
    motor.MotorRun(1, 'backward', 50)
    time.sleep(1)  # 90도 회전에 필요한 시간 조정
    motor.MotorStop() 

# ------------------------
# [라인트래킹 메인 함수]
#  - 이 함수는 PATH 수신 후에만 호출됨
# ------------------------
def line_following_with_qr():
    global mqtt_received_command, mqtt_received_path

    # 여기서부터 실제 하드웨어 초기화 (로그는 여기서부터 시작)
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
    original_speed = 40 # cm/s
    slow_speed = 8      # 감속 시 속도 
    target_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    # 상태 정의
    STATE_WAIT_START = 0 # MQTT 통신 완료 전 대기 (출발지 QR 없앰)
    STATE_ACTIVE     = 1
    STATE_STOP       = 2
    state = STATE_WAIT_START
    start_active_time = None
    distance_traveled = 0

    # 디버깅용 코드. 마지막 거리 출력 시각
    last_distance_print = time.time()

    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            # 초음파 센서로 1초마다 거리 측정
            distance = get_distance()
            if current_time - last_distance_print >= 1.0:
                print(f"[DEBUG] 초음파 센서 측정 거리: {distance} cm")
                last_distance_print = current_time

            # 30cm 이내 물체 감지 시 이상 물체로 판단.
            # 모터 정지 및 MQTT 전송 
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
            
            # MQTT 원격 명령 처리 (STOP, RESUME, TURN)
            if mqtt_received_command is not None:
                if mqtt_received_command == 'STOP':
                    print("Remote STOP 명령 실행")
                    motor.MotorStop()
                    state = STATE_STOP
                    mqtt_received_command = None
                    # 원격 정지 시, 화면에 상태 표시 후 다음 루프로
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

            # 상태에 따른 동작 처리 
            if state == STATE_WAIT_START:
                    # MQTT 통신이 완료되면 바로 라인트래킹 시작
                    if mqtt_received_path:
                        print("MQTT 통신 완료 – 활성 상태 전환 (라인트래킹 시작)")
                        state = STATE_ACTIVE
                        start_active_time = current_time
                    else:
                        cv2.putText(frame, "Waiting for MQTT", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        motor.MotorStop()

            elif state == STATE_ACTIVE:
                # 이동 거리 (근사: 전진 속도 * 시간)
                distance_traveled = (current_time - start_active_time) * original_speed
                # 100cm 미만이면 기본 속도, 그 이상이면 감속
                # if distance_traveled < 100:
                #     target_speed = original_speed
                # else:
                #     target_speed = slow_speed

                # # QR 코드 검출 (100cm 이상 이동하면 90도 회전)
                # qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                # if qr_detected and distance_traveled >= 100:
                #     print("100cm 이동 후 QR 코드 감지 – 90도 회전")
                #     motor.MotorStop()
                #     rotate_90_degrees(motor)
                #     state = STATE_STOP
                #     qr_info = {"position": qr_centroid, "data": qr_data}
                #     mqtt_client.publish(TOPIC_QR_INFO, json.dumps(qr_info))
                #     time.sleep(1)
                #     continue
                
                # # 빨간색 라인 검출 및 PID 제어
                # detected, centroid, mask = detect_red_line(frame)
                # if detected and centroid is not None:
                #     cx, cy = centroid
                #     cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                #     cv2.line(frame, (frame_center, 0), (frame_center, frame_height),
                #              (255, 0, 0), 2)
                #     cv2.putText(frame, f"Centroid: ({cx}, {cy})", (10, 30),
                #                 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                #     error = cx - frame_center
                #     correction = pid.update(error, dt)

                #     # 보정값 급격 변화 제한 
                #     max_delta = 2
                #     delta = correction - prev_correction
                #     if abs(delta) > max_delta:
                #         correction = prev_correction + max_delta * np.sign(delta)
                #     prev_correction = correction

                #     min_speed = 4
                #     left_speed = target_speed + correction
                #     right_speed = target_speed - correction
                #     left_speed = max(min_speed, min(100, left_speed))
                #     right_speed = max(min_speed, min(100, right_speed))

                #     motor.MotorRun(0, 'forward', left_speed)
                #     motor.MotorRun(1, 'forward', right_speed)
                #     cv2.putText(frame, f"Line Tracking: L {left_speed:.1f}, R {right_speed:.1f}",
                #                 (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                #     print(f"[ACTIVE] error: {error:.2f}, correction: {correction:.2f}, L: {left_speed:.1f}, R: {right_speed:.1f}")
                # else:
                #     # 라인 미검출 시 이전 보정값 서서히 감쇠 
                #     prev_correction *= 0.9
                #     left_speed = target_speed + prev_correction
                #     right_speed = target_speed - prev_correction
                #     left_speed = max(4, min(100, left_speed))
                #     right_speed = max(4, min(100, right_speed))
                #     motor.MotorRun(0, 'forward', left_speed)
                #     motor.MotorRun(1, 'forward', right_speed)
                #     cv2.putText(frame, "Line not detected", (10, 30),
                #                 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # # 현재 속도 표시 (카메라 화면에 출력)
                # cv2.putText(frame, f"Speed: {target_speed} cm/s", (10, 120),
                #             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                # STATE_ACTIVE 내부, 라인 검출 및 모터 제어 부분 (기존 PID 제어 코드를 대체)
                # 원래 전체 프레임에서 검출하던 부분 대신, 아래와 같이 ROI(60:120, 0:160) 영역에서 처리합니다.

                # 1. ROI 대신 frame 전체로 처리함 
                full_img = frame

                # 2. ROI에서 HSV 변환 및 빨간색 마스크 생성
                hsv = cv2.cvtColor(full_img, cv2.COLOR_BGR2HSV)
                lower_red1 = np.array([0, 100, 100])
                upper_red1 = np.array([10, 255, 255])
                lower_red2 = np.array([160, 100, 100])
                upper_red2 = np.array([180, 255, 255])
                mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                mask = cv2.bitwise_or(mask1, mask2)

                # 3. 노이즈 제거: 모폴로지 연산 (에로전과 디롤션)
                mask = cv2.erode(mask, None, iterations=2)
                mask = cv2.dilate(mask, None, iterations=2)
                cv2.imshow('Red Mask', mask)

                # 4. 윤곽선 검출 및 무게중심 계산
                contours, hierarchy = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                if len(contours) > 0:
                    c = max(contours, key=cv2.contourArea)
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        # (옵션) ROI 내에서 무게중심 표시
                        cv2.line(full_img, (cx, 0), (cx, full_img.shape[0]), (255, 0, 0), 1)
                        cv2.imshow('Full Image', full_img)
                        print("Red line center cx:", cx)

                        # 전체 프레임 기준 모터 제어: 중심은 frame_width//2 (예: 640 -> 320)
                        frame_center = full_img.shape[1] // 2
                        # 좌우 임계값은 상황에 맞게 조절 (여기선 ±40 픽셀 기준)
                        if cx < frame_center - 40:
                            print("Turn Right!")
                            # 오른쪽으로 회전: 오른쪽 모터 정지, 왼쪽 모터 전진
                            motor.MotorRun(0, 'forward', 40)
                            motor.MotorStop(1)
                        elif cx > frame_center + 40:
                            print("Turn Left!")
                            # 왼쪽으로 회전: 왼쪽 모터 정지, 오른쪽 모터 전진
                            motor.MotorStop(0)
                            motor.MotorRun(1, 'forward', 40)
                        else:
                            print("Go Straight!")
                            motor.MotorRun(0, 'forward', 40)
                            motor.MotorRun(1, 'forward', 40)
                    else:
                        print("Zero division error in moments calculation")
                        motor.MotorStop()
                else:
                    print("Red line not detected")
                    # 라인 미검출 시, 이전 명령을 유지하거나 안전하게 정지
                    motor.MotorStop()
                        
                


            elif state == STATE_STOP:
                motor.MotorStop()
                cv2.putText(frame, "Stopped, waiting for command", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                # 원격 정지 시, 별도의 입력 대기 루틴 없이 MQTT로 RESUME 명령을 받으면 재시작
                print("정지 상태: 명령을 입력하세요 (RESUME 입력 시 재시작):")
        

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
# ------------------------
# [메인 함수]
#  - 1) MQTT PATH 수신 전까지 대기
#  - 2) PATH가 수신되면 라인트래킹 함수 호출
# ------------------------
def main():
    global mqtt_path_received
    print("[MAIN] MQTT에서 PATH를 기다리는 중...")
    # PATH 수신될 때까지 대기
    while not mqtt_path_received:
        time.sleep(1)

    print("[MAIN] PATH 수신됨! 라인트래킹 시작...")
    line_following_with_qr()

if __name__ == '__main__':
    main()
