import Jetson.GPIO as GPIO
import time
import paho.mqtt.client as mqtt
import json
from PCA9685 import PCA9685

# GPIO 핀 설정
GPIO.setmode(GPIO.BOARD)
TRIG = 7
ECHO = 15
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# MQTT 설정
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_AGV_TO_SIMPY = "agv/status"
TOPIC_SIMPY_TO_AGV = "simpy/commands"

# 돌발상황 감지 임계값 (30cm)
EMERGENCY_DISTANCE = 30  

# 센서 안정화 대기
time.sleep(1)

# AGV 상태
is_stopped = False

# MQTT 클라이언트 설정
client = mqtt.Client(protocol=mqtt.MQTTv311)

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(TOPIC_SIMPY_TO_AGV)

def on_message(client, userdata, msg):
    global is_stopped
    command = json.loads(msg.payload)
    print(f"Received command: {command}")
   
    if command['command'] == 'RESUME':
        print("[INFO] 다시 주행 시작")
        is_stopped = False
        Motor.MotorRun(0, 'forward', 50)
        Motor.MotorRun(1, 'forward', 50)
    elif command['command'] == 'STOP':
        print("[INFO] 차량 정지")
        is_stopped = True
        Motor.MotorStop()
    elif command['command'] == 'RETURN':
        print("[INFO] 복귀 모드 실행")
        is_stopped = True
        Motor.MotorRun(0, 'backward', 50)
        Motor.MotorRun(1, 'backward', 50)
        time.sleep(3)  # 3초간 후진 후 정지
        Motor.MotorStop()
    else:
        print("[WARNING] 알 수 없는 명령, 대기 유지")

client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_start()

class MotorDriver():
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
            return
        if motor == 0:
            self.pwm.setDutycycle(self.PWMA, speed)
            if direction == 'forward':
                self.pwm.setLevel(self.AIN1, 0)
                self.pwm.setLevel(self.AIN2, 1)
            else:
                self.pwm.setLevel(self.AIN1, 1)
                self.pwm.setLevel(self.AIN2, 0)
        else:
            self.pwm.setDutycycle(self.PWMB, speed)
            if direction == 'forward':
                self.pwm.setLevel(self.BIN1, 0)
                self.pwm.setLevel(self.BIN2, 1)
            else:
                self.pwm.setLevel(self.BIN1, 1)
                self.pwm.setLevel(self.BIN2, 0)

    def MotorStop(self):
        self.pwm.setDutycycle(self.PWMA, 0)
        self.pwm.setDutycycle(self.PWMB, 0)

def measure_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.000002)
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
   
    pulse_end = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return round(distance, 2)

def stop_vehicle():
    global is_stopped
    is_stopped = True
    Motor.MotorStop()
    print("[ALERT] 돌발상황 감지! 차량 정지!")

def send_emergency_signal():
    emergency_data = json.dumps({"status": "emergency"})
    client.publish(TOPIC_AGV_TO_SIMPY, emergency_data)
    print("[INFO] MQTT로 돌발상황 발생 신호 전송 완료")

try:
    Motor = MotorDriver()
    Motor.MotorRun(0, 'forward', 50)
    Motor.MotorRun(1, 'forward', 50)

    while True:
        dist = measure_distance()
        print(f"Distance: {dist} cm")

        if dist <= EMERGENCY_DISTANCE and not is_stopped:
            stop_vehicle()
            send_emergency_signal()
       
        time.sleep(0.5)

except KeyboardInterrupt:
    print("Measurement stopped by user")
    Motor.MotorStop()
    GPIO.cleanup()
    client.loop_stop()
    client.disconnect()


