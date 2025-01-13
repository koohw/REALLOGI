import RPi.GPIO as GPIO
from time import sleep
pir_pin = 17
GPIO.setmode(GPIO.BCM)        # GPIO 핀 번호 설정 (BCM 모드 사용)
GPIO.setup(pir_pin, GPIO.IN)  # 입력 모드로 설정 (터치 센서)
while True:
    motion_detected = GPIO.input(pir_pin)
    print(motion_detected)
    sleep(0.1)
