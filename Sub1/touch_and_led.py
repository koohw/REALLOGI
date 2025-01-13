import RPi.GPIO as GPIO
from time import sleep
GPIO.setmode(GPIO.BCM)   # GPIO 핀 번호 설정(BCM 모드 사용)
GPIO.setup(17, GPIO.IN)  # 입력 모드로 설정(터치 센서 입력 핀)
GPIO.setup(2, GPIO.OUT)  # 출력 모드로 설정(LED 출력 핀)
while True:
    motion_detected = GPIO.input(17)
    print(motion_detected)
    if motion_detected == 1:
        GPIO.output(2, True)
    else:
        GPIO.output(2, False)
    sleep(0.1)
