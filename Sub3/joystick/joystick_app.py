from flask import Flask, Response, render_template, request
import cv2
from adafruit_motor import motor
from adafruit_pca9685 import PCA9685
import board
import busio
import time
from ultralytics import YOLO
from adafruit_servokit import ServoKit
import torch
# Load the YOLOv8 model

model = YOLO("yolov8n.pt").to('cuda' if torch.cuda.is_available() else 'cpu')
class_names = model.names

class PWMThrottleHat:
    def __init__(self, pwm, channel):
        self.pwm = pwm
        self.channel = channel
        self.pwm.frequency = 60

    def set_throttle(self, throttle):
        pulse = int(0xFFFF * abs(throttle))  # 16-bit duty cycle
        if throttle > 0:
            # Forward
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0xFFFF
        elif throttle < 0:
            # Backward
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0xFFFF
            self.pwm.channels[self.channel + 3].duty_cycle = 0
        else:
            # Stop
            self.pwm.channels[self.channel + 5].duty_cycle = 0
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0

# I2C 버스 설정
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 60


# PWMThrottleHat 인스턴스 생성
motor_hat = PWMThrottleHat(pca, channel=0)
# 서보 모터 제어 설정
kit = ServoKit(channels=16, i2c=i2c, address=0x60)
pan = 100
kit.servo[0].angle = pan

def i2c_scan(i2c):
    while not i2c.try_lock():
        pass
    try:
        devices = i2c.scan()
        return devices
    finally:
        i2c.unlock()

# 전역 변수로 현재 카메라 모드를 설정
inputText = ""
app = Flask(__name__)

def gen_frames():
    cap = cv2.VideoCapture(0)
    
    while True:
        success, frame = cap.read()  # 카메라 프레임 읽기
        if not success:
            break

        if torch.cuda.is_available():
            gpu_frame = cv2.cuda_GpuMat()
            gpu_frame.upload(frame)  # GPU로 프레임 업로드
            frame = gpu_frame.download()  # GPU에서 처리가 끝난 후 다시 다운로드
            
        results = model(frame)
        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy()  # Bounding box coordinates
            confs = result.boxes.conf.cpu().numpy()  # Confidence scores
            classes = result.boxes.cls.cpu().numpy()  # Class IDs
            
            for box, conf, cls in zip(boxes, confs, classes):
                x1, y1, x2, y2 = box
                class_name = class_names[int(cls)]
                if len(inputText) == 0:
                    label = f"{class_name} {conf:.2f}"
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                elif inputText.lower() == class_name.lower():
                    label = f"{class_name} {conf:.2f}"
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                    cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    break
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/joystick', methods=['POST'])
def joystick():
    global camera_mode, inputText, motor_hat, pan  # 전역 변수 사용 선언
    motor_hat = PWMThrottleHat(pca, channel=0)
    direction = request.form['direction']
    if direction == "up":
        print(f"Direction received: {direction}")
        motor_hat.set_throttle(0.5)  # Forward at 50% speed
    elif direction == "down":
        print(f"Direction received: {direction}")
        motor_hat.set_throttle(-0.5)  # Backward at 50% speed
    elif direction == "left":
        pan -= 10  # 왼쪽으로 이동
        if pan < 80:
            pan = 80
        kit.servo[0].angle = pan
    elif direction == "right":
        pan += 10  # 오른쪽으로 이동
        if pan > 130:
            pan = 130
        kit.servo[0].angle = pan
    elif direction == "stop":
        print("Switching to normal camera mode")
        motor_hat.set_throttle(0)
    elif direction == "o":
        inputText = request.form['inputText']
        print(inputText)
    return '', 204  # 빈 응답, 페이지를 리로드하지 않도록 함

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234)

