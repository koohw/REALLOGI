import Jetson.GPIO as GPIO
import time
import requests
from PCA9685 import PCA9685

# GPIO 핀 설정
GPIO.setmode(GPIO.BOARD)
TRIG = 7
ECHO = 15
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# 모터 드라이버 초기화
Motor = None

# 서버 URL (실제 서버 주소로 변경)
SERVER_URL = "http://192.168.0.100:5000/emergency"

# 돌발상황 감지 임계값 (30cm)
EMERGENCY_DISTANCE = 30  

# 센서 안정화 대기
time.sleep(1)


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


def stop_vehicle():
    """ 차량 정지 """
    if Motor:
        Motor.MotorStop()
    print("[ALERT] 돌발상황 감지! 차량 정지!")


def send_emergency_signal():
    """ 서버로 돌발상황 발생 신호 전송 """
    try:
        response = requests.post(SERVER_URL, json={"status": "emergency"})
        if response.status_code == 200:
            print("[INFO] 서버로 돌발상황 발생 신호 전송 완료")
        else:
            print("[ERROR] 서버 응답 실패:", response.status_code)
    except Exception as e:
        print("[ERROR] 서버 전송 오류:", str(e))


def wait_for_server_command():
    """ 서버에서 명령을 받을 때까지 대기 """
    while True:
        try:
            response = requests.get(SERVER_URL)
            if response.status_code == 200:
                command = response.json().get("command")
                print(f"[INFO] 서버에서 받은 명령: {command}")
                return command
            else:
                print("[ERROR] 서버 응답 실패:", response.status_code)
        except Exception as e:
            print("[ERROR] 서버 요청 오류:", str(e))
        time.sleep(2)


try:
    Motor = MotorDriver()
    Motor.MotorRun(0, 'forward', 50)
    Motor.MotorRun(1, 'forward', 50)

    while True:
        dist = measure_distance()
        print(f"Distance: {dist} cm")

        if dist <= EMERGENCY_DISTANCE:
            stop_vehicle()
            send_emergency_signal()
            command = wait_for_server_command()
            
            if command == "resume":
                print("[INFO] 다시 주행 시작")
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 50)
            elif command == "return":
                print("[INFO] 복귀 모드 실행")
                Motor.MotorRun(0, 'backward', 50)
                Motor.MotorRun(1, 'backward', 50)
                time.sleep(3)  # 3초간 후진 후 정지
                Motor.MotorStop()
            else:
                print("[WARNING] 알 수 없는 명령, 대기 유지")
        
        time.sleep(0.5)

except KeyboardInterrupt:
    print("Measurement stopped by user")
    GPIO.cleanup()
