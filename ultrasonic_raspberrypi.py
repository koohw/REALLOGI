import Jetson.GPIO as GPIO
import time

# Jetson Orin Nano에서 사용할 GPIO 핀 번호 설정
TRIG = 11  # 예제용 TRIG 핀 (적절한 핀으로 변경 가능)
ECHO = 12  # 예제용 ECHO 핀 (적절한 핀으로 변경 가능)

GPIO.setmode(GPIO.BOARD)  # Jetson Orin Nano에서는 BOARD 모드 사용
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def measure_distance():
    GPIO.output(TRIG, False)
    time.sleep(2)  # 센서 안정화 시간
    print("Sensor initialized.")

    GPIO.output(TRIG, True)
    time.sleep(0.00001)  # 10μs 대기
    GPIO.output(TRIG, False)
    print("TRIG signal sent.")

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    while GPIO.input(ECHO) == 1:
        print('echo error2')
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    distance = round(distance, 2)
    return distance

try:
    while True:
        dist = measure_distance()
        print(f"Distance: {dist} cm")
        time.sleep(1)
except KeyboardInterrupt:
    print("Measurement stopped by user")
    GPIO.cleanup()
