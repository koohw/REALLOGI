import cv2
import numpy as np
import time
from PCA9685 import PCA9685
import paho.mqtt.client as mqtt
import json
import smbus
import math
import RPi.GPIO as GPIO

# \ucd08\uc74c\ud30c \uc13c\uc11c \uc124\uc815
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

# MQTT \uc124\uc815
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_QR_INFO = "agv/qr_info"         # QR \uac10\uc9c0 \uc2dc \uc815\ubcf4 \uc804\uc1a1
TOPIC_SIMPY_TO_AGV = "simpy/commands"
TOPIC_OBSTACLE = "agv/obstacle"       # \uc7a5\uc560\ubb3c \uac10\uc9c0 \uc2dc \uc815\ubcf4 \uc804\uc1a1

mqtt_received_path = []  # MQTT\ub85c \ubc1b\uc740 \uc804\uccb4 \uacbd\ub85c \ub9ac\uc2a4\ud2b8
mqtt_received_command = None # MQTT\ub85c \ubc1b\uc740 \uc6d0\uaca9 \uba85\ub839 (STOP, RESUME, TURN)
mqtt_path_received = False    # PATH \uba85\ub839\uc774 \uc218\uc2e0\ub418\uc5c8\ub294\uc9c0 \uc5ec\ubd80

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
            print("[MQTT] AGV \uc815\uc9c0 \uba85\ub839 \uc218\uc2e0")
            mqtt_received_command = 'STOP'
        elif cmd == 'RESUME':
            print("[MQTT] AGV \uc7ac\uc2dc\uc791 \uba85\ub839 \uc218\uc2e0")
            mqtt_received_command = 'RESUME'
        elif cmd == 'TURN':
            print("[MQTT] AGV \ud68c\uc804 \uba85\ub839 \uc218\uc2e0")
            mqtt_received_command = 'TURN'
        elif cmd == 'PATH':
            full_path = payload.get('data', {}).get('full_path', [])
            print("[MQTT] PATH \uba85\ub839 \uc218\uc2e0 =", full_path)
            mqtt_received_path = full_path
            mqtt_path_received = True  # \uacbd\ub85c \uc218\uc2e0 \ud50c\ub798\uadf8
        else:
            print("[MQTT] \uc54c \uc218 \uc5c6\ub294 \uba85\ub839 \uc218\uc2e0:", cmd)
    except Exception as e:
        print("[MQTT] on_message \uc624\ub958:", e)

# ------------------------
# [MQTT \ud074\ub77c\uc774\uc5b8\ud2b8 \ucd08\uae30\ud654]
# ------------------------
mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

# --- \ubaa8\ud130 \uc81c\uc5b4 \ud074\ub798\uc2a4 ---
class MotorDriver:
    def __init__(self):
        self.PWMA = 0
        self.AIN1 = 1
        self.AIN2 = 2
        self.PWMB = 5
        self.BIN1 = 3
        self.BIN2 = 4
        # PCA9685 debug=False \uc124\uc815 -> I2C \ub808\uc9c0\uc2a4\ud130 \ub85c\uadf8\uac00 \ub728\uc9c0 \uc54a\ub3c4\ub85d 
        self.pwm = PCA9685(0x40, debug=False)
        self.pwm.setPWMFreq(50)

    def MotorRun(self, motor, direction, speed):
        speed = min(speed, 100)
        if motor == 0:  # \uc67c\ucabd \ubaa8\ud130
            self.pwm.setDutycycle(self.PWMA, int(speed))
            if direction == 'forward':
                self.pwm.setLevel(self.AIN1, 0)
                self.pwm.setLevel(self.AIN2, 1)
            else:
                self.pwm.setLevel(self.AIN1, 1)
                self.pwm.setLevel(self.AIN2, 0)
        else:  # \uc624\ub978\ucabd \ubaa8\ud130
            self.pwm.setDutycycle(self.PWMB, int(speed))
            if direction == 'forward':
                self.pwm.setLevel(self.BIN1, 0)
                self.pwm.setLevel(self.BIN2, 1)
            else:
                self.pwm.setLevel(self.BIN1, 1)
                self.pwm.setLevel(self.BIN2, 0)

    def MotorStop(self, motor=None):
        # motor\uac00 None\uc774\uba74 \ubaa8\ub4e0 \ubaa8\ud130 \uc815\uc9c0
        if motor is None:
            self.pwm.setDutycycle(self.PWMA, 0)
            self.pwm.setDutycycle(self.PWMB, 0)
        elif motor == 0:
            self.pwm.setDutycycle(self.PWMA, 0)
        else:
            self.pwm.setDutycycle(self.PWMB, 0)

# --- PID \ucee8\ud2b8\ub864\ub7ec \ud074\ub798\uc2a4 ---
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

# --- \ube68\uac04\uc0c9 \ub77c\uc778 \uac80\ucd9c \ud568\uc218 ---
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

    # mask \ub514\ubc84\uae45 \ud654\uba74
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

# --- QR \ucf54\ub4dc \uac80\ucd9c \ud568\uc218 ---
def detect_qr_code(frame):
    qr_detector = cv2.QRCodeDetector()
    data, points, _ = qr_detector.detectAndDecode(frame)
    if points is not None and data:
        pts = points[0]
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        return True, (cx, cy), data
    return False, None, None

# \ud68c\uc804 \ud568\uc218
def rotate_90_degrees(motor):
    motor.MotorRun(0, 'forward', 80)
    motor.MotorRun(1, 'backward', 80)
    time.sleep(1)  # 90\ub3c4 \ud68c\uc804\uc5d0 \ud544\uc694\ud55c \uc2dc\uac04 \uc870\uc815
    motor.MotorStop() 

# ------------------------
# [\ub77c\uc778\ud2b8\ub798\ud0b9 \uba54\uc778 \ud568\uc218]
#  - \uc774 \ud568\uc218\ub294 PATH \uc218\uc2e0 \ud6c4\uc5d0\ub9cc \ud638\ucd9c\ub428
# ------------------------
def line_following_with_qr():
    global mqtt_received_command, mqtt_received_path

    # \uc5ec\uae30\uc11c\ubd80\ud130 \uc2e4\uc81c \ud558\ub4dc\uc6e8\uc5b4 \ucd08\uae30\ud654 (\ub85c\uadf8\ub294 \uc5ec\uae30\uc11c\ubd80\ud130 \uc2dc\uc791)
    motor = MotorDriver()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.2)
   
    if not cap.isOpened():
        print("\uce74\uba54\ub77c\ub97c \uc5f4 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.")
        return

    ret, frame = cap.read()
    if not ret:
        print("\ud504\ub808\uc784\uc744 \uc77d\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.")
        return

    frame_height, frame_width = frame.shape[:2]
    frame_center = frame_width // 2

    # PID \ubc0f \uc18d\ub3c4 \uc124\uc815
    pid = PID(kp=0.1, ki=0.0, kd=0.01)
    original_speed = 40 # cm/s
    slow_speed = 8      # QR \uac10\uc9c0\ub97c \uc704\ud55c \uac10\uc18d \uc2dc \uc18d\ub3c4 
    target_speed = original_speed
    prev_time = time.time()
    prev_correction = 0

    # \uc0c1\ud0dc \uc815\uc758
    STATE_WAIT_START = 0    # MQTT \ud1b5\uc2e0 \uc644\ub8cc \uc804 \ub300\uae30 (\ucd9c\ubc1c\uc9c0 QR \uc5c6\uc570)
    STATE_ACTIVE     = 1    # \ub77c\uc778\ud2b8\ub808\uc774\uc2f1
    STATE_STOP       = 2    # \uc815\uc9c0
    state = STATE_WAIT_START
    start_active_time = None
    distance_traveled = 0

    # \ub514\ubc84\uae45\uc6a9 \ucf54\ub4dc. \ub9c8\uc9c0\ub9c9 \uac70\ub9ac \ucd9c\ub825 \uc2dc\uac01
    last_distance_print = time.time()

    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            # \ucd08\uc74c\ud30c \uc13c\uc11c\ub85c 1\ucd08\ub9c8\ub2e4 \uac70\ub9ac \uce21\uc815
            distance = get_distance()
            if current_time - last_distance_print >= 1.0:
                print(f"[DEBUG] \ucd08\uc74c\ud30c \uc13c\uc11c \uce21\uc815 \uac70\ub9ac: {distance} cm")
                last_distance_print = current_time

            # 30cm \uc774\ub0b4 \ubb3c\uccb4 \uac10\uc9c0 \uc2dc \uc774\uc0c1 \ubb3c\uccb4\ub85c \ud310\ub2e8.
            # \ubaa8\ud130 \uc815\uc9c0 \ubc0f MQTT \uc804\uc1a1 
            if distance < 30:
                print("\uc774\uc0c1 \ubb3c\uccb4\uac00 \uac10\uc9c0\ub429\ub2c8\ub2e4. \uce74\uba54\ub77c\ub97c \ud655\uc778\ud574\uc8fc\uc138\uc694.")
                motor.MotorStop()
                mqtt_client.publish(TOPIC_OBSTACLE, json.dumps({"distance": distance}))
                time.sleep(1)
                continue

            ret, frame = cap.read()
            if not ret:
                print("\ud504\ub808\uc784 \uc77d\uae30 \uc2e4\ud328")
                break
            
            # MQTT \uc6d0\uaca9 \uba85\ub839 \ucc98\ub9ac (STOP, RESUME, TURN)
            if mqtt_received_command is not None:
                if mqtt_received_command == 'STOP':
                    print("Remote STOP \uba85\ub839 \uc2e4\ud589")
                    motor.MotorStop()
                    state = STATE_STOP
                    mqtt_received_command = None
                    # \uc6d0\uaca9 \uc815\uc9c0 \uc2dc, \ud654\uba74\uc5d0 \uc0c1\ud0dc \ud45c\uc2dc \ud6c4 \ub2e4\uc74c \ub8e8\ud504\ub85c
                    cv2.putText(frame, "REMOTE STOP", (10, 150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.imshow("Frame", frame)
                    cv2.waitKey(1)
                    continue

                elif mqtt_received_command == 'RESUME':
                        print("Remote RESUME \uba85\ub839 \uc2e4\ud589")
                        state = STATE_ACTIVE
                        if start_active_time is None:
                            start_active_time = current_time
                        mqtt_received_command = None
                
                elif mqtt_received_command == 'TURN':
                        print("Remote TURN \uba85\ub839 \uc2e4\ud589")
                        motor.MotorStop()
                        rotate_90_degrees(motor)
                        mqtt_received_command = None

            # \uc0c1\ud0dc\uc5d0 \ub530\ub978 \ub3d9\uc791 \ucc98\ub9ac 
            if state == STATE_WAIT_START:
                    # MQTT \ud1b5\uc2e0\uc774 \uc644\ub8cc\ub418\uba74 \ubc14\ub85c \ub77c\uc778\ud2b8\ub798\uc2f1 \uc2dc\uc791
                    if mqtt_received_path:
                        print("MQTT \ud1b5\uc2e0 \uc644\ub8cc \u2013 \ud65c\uc131 \uc0c1\ud0dc \uc804\ud658 (\ub77c\uc778\ud2b8\ub798\ud0b9 \uc2dc\uc791)")
                        state = STATE_ACTIVE
                        start_active_time = current_time
                    else:
                        cv2.putText(frame, "Waiting for MQTT", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        motor.MotorStop()

            elif state == STATE_ACTIVE:
                # \ub204\uc801 \uc774\ub3d9\uac70\ub9ac\uc5d0 \ub530\ub77c \ubaa9\ud45c \uc18d\ub3c4 \ubcc0\uacbd (\uc774\ub3d9\uac70\ub9accm = \ub2e8\uc21c\uc18d\ub3c4 * \uc2dc\uac04)
                # \ub204\uc801 \uc774\ub3d9\uac70\ub9ac \uacc4\uc0b0 (cm \ub2e8\uc704, \ub2e8\uc21c \uc18d\ub3c4 * \uc2dc\uac04)
                distance_traveled = (current_time - start_active_time) * original_speed
                
                # distance_travled cv2 imshow
                cv2.putText(frame, f"Distance: {distance_traveled:.1f} cm", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                if distance_traveled < 150:
                    target_speed = original_speed
                else:
                    target_speed = slow_speed

                # 50cm \uc774\uc0c1 \uc774\ub3d9\ud55c \ud6c4 QR \ucf54\ub4dc \uac10\uc9c0 \uc2dc\ub3c4
                if distance_traveled >= 150:
                    qr_detected, qr_centroid, qr_data = detect_qr_code(frame)
                    if qr_detected:
                    	 # QR \ucf54\ub4dc \uac10\uc9c0 -> STRAIGHT
                        # print("\ub77c\uc778\ud2b8\ub798\ud0b9 \uc911 QR \ucf54\ub4dc \uac10\uc9c0 \u2013 \uc815\uc9c0 \ubc0f \uba85\ub839 \ub300\uae30")
                        # motor.MotorStop()
                        # MQTT\ub85c QR \uc815\ubcf4 \uc804\uc1a1
                        # qr_info = {"position": qr_centroid, "data": qr_data}
                        # mqtt_client.publish(TOPIC_QR_INFO, json.dumps(qr_info))
                        # time.sleep(1)
                        # \uc7ac\uc2dc\uc791: \uc0c1\ud0dc\ub97c ACTIVE\ub85c \uc804\ud658\ud558\uace0 \uc774\ub3d9\uac70\ub9ac \uce21\uc815 \ucd08\uae30\ud654
                        # state = STATE_ACTIVE
                        # start_active_time = time.time()
                        # target_speed = original_speed
                        # continue
                        print("QR DETECT -> 90 TURN")
                        motor.MotorStop()
                        qr_info = {"position": qr_centroid, "data": qr_data}
                        mqtt_client.publish(TOPIC_QR_INFO, json.dumps(qr_info))
                        # TURN
                        rotate_90_degrees(motor)
                        time.sleep(1)
                        # \uc7ac\uc2dc\uc791: \uc0c1\ud0dc\ub97c ACTIVE\ub85c \uc804\ud658\ud558\uace0 \uc774\ub3d9\uac70\ub9ac \uce21\uc815 \ucd08\uae30\ud654
                        start_active_time = time.time()
                        target_speed = original_speed
                        continue
                
                # \ube68\uac04\uc0c9 \ub77c\uc778 \uac80\ucd9c \ubc0f PID \ubcf4\uc815
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
                    # \ubcf4\uc815\uac12\uc758 \uae09\uaca9\ud55c \ubcc0\ud654 \uc81c\ud55c
                    max_delta = 2
                    delta = correction - prev_correction
                    if abs(delta) > max_delta:
                        correction = prev_correction + max_delta * np.sign(delta)
                    prev_correction = correction

                    # \ub450 \ubaa8\ud130 \ubaa8\ub450 \uc804\uc9c4\uc2dc\ud0a4\ub418, \uc18d\ub3c4 \ucc28\uc774\ub97c \ud1b5\ud574 \ud68c\uc804 \ubcf4\uc815  
                    # (\ucd5c\uc18c \uc18d\ub3c4(min_speed)\ub97c \uc720\uc9c0\ud558\uc5ec \ud55c\ucabd \ubaa8\ud130\uac00 \uac70\uc758 \uba48\ucd94\uc9c0 \uc54a\ub3c4\ub85d \ud568)
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
                    # # \ub77c\uc778 \ubbf8\uac80\ucd9c \uc2dc \uc774\uc804 \ubcf4\uc815\uac12\uc744 \uc11c\uc11c\ud788 \uac10\uc1e0\ud558\uba70 \uc804\uc9c4
                    # prev_correction *= 0.9
                    # left_speed = target_speed + prev_correction
                    # right_speed = target_speed - prev_correction
                    # left_speed = max(4, min(100, left_speed))
                    # right_speed = max(4, min(100, right_speed))
                    # motor.MotorRun(0, 'forward', left_speed)
                    # motor.MotorRun(1, 'forward', right_speed)
                    # cv2.putText(frame, "Line not detected", (10, 30),
                    #             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                    # \ub3cc\ubc1c \uc0c1\ud669: \uc804\uccb4 \ud654\uba74\uc5d0\uc11c \ube68\uac04\uc0c9 \ub77c\uc778\uc774 \uac80\ucd9c\ub418\uc9c0 \uc54a\uc73c\uba74 emergency
                    print("\ub3cc\ubc1c \uc0c1\ud669: \ube68\uac04\uc0c9 \ub77c\uc778 \ubbf8\uac80\ucd9c!")
                    motor.MotorStop()
                    mqtt_client.publish(TOPIC_OBSTACLE, json.dumps({"emergency": True}))
                    time.sleep(1)
                    continue

                
            elif state == STATE_STOP:
                motor.MotorStop()
                cv2.putText(frame, "Stopped, waiting for command", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                # \uc6d0\uaca9 \uc815\uc9c0 \uc2dc, \ubcc4\ub3c4\uc758 \uc785\ub825 \ub300\uae30 \ub8e8\ud2f4 \uc5c6\uc774 MQTT\ub85c RESUME \uba85\ub839\uc744 \ubc1b\uc73c\uba74 \uc7ac\uc2dc\uc791
                print("\uc815\uc9c0 \uc0c1\ud0dc: RESUME \uc785\ub825 \uc2dc \uc7ac\uac00\ub3d9")
                cmd = input()
                if cmd.strip().upper() == "RESUME":
                    print("\uc7ac\uc2dc\uc791 \uba85\ub839 \uc218\uc2e0 \u2013 \ud65c\uc131 \uc0c1\ud0dc\ub85c \uc804\ud658")
                    state = STATE_ACTIVE
                    start_active_time = time.time()  # \uc774\ub3d9\uac70\ub9ac \uae30\uc900 \ucd08\uae30\ud654
                else:
                    print("\uc54c \uc218 \uc5c6\ub294 \uba85\ub839. \uacc4\uc18d \uc815\uc9c0\ud569\ub2c8\ub2e4.")

            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("Ctrl+C \uc785\ub825, \ubaa8\ud130\ub97c \uc815\uc9c0\ud569\ub2c8\ub2e4.")
    finally:
        motor.MotorStop()
        cap.release()
        cv2.destroyAllWindows()
        GPIO.cleanup()
# ------------------------
# [\uba54\uc778 \ud568\uc218]
#  - 1) MQTT PATH \uc218\uc2e0 \uc804\uae4c\uc9c0 \ub300\uae30
#  - 2) PATH\uac00 \uc218\uc2e0\ub418\uba74 \ub77c\uc778\ud2b8\ub798\ud0b9 \ud568\uc218 \ud638\ucd9c
# ------------------------
def main():
    global mqtt_path_received
    print("[MAIN] MQTT\uc5d0\uc11c PATH\ub97c \uae30\ub2e4\ub9ac\ub294 \uc911...")
    # PATH \uc218\uc2e0\ub420 \ub54c\uae4c\uc9c0 \ub300\uae30
    while not mqtt_path_received:
        time.sleep(1)

    print("[MAIN] PATH \uc218\uc2e0\ub428! \ub77c\uc778\ud2b8\ub798\ud0b9 \uc2dc\uc791...")
    line_following_with_qr()

if __name__ == '__main__':
    main()