import RPi.GPIO as GPIO
from time import sleep
GPIO.setmode(GPIO.BCM) # GPIO 핀 번호 설정 (BCM 모드 사용)
GPIO.setup(17, GPIO.OUT)  # 입력 모드로 설정
GPIO.setup(27, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)
GPIO.output(17, True)  #17 led on
sleep(1)
GPIO.output(17, False) #17 led off
sleep(1)
GPIO.output(27, True)  #27 led on
sleep(1)
GPIO.output(27, False) #27 led off
sleep(1)
GPIO.output(22, True)  #22 led on
sleep(1)
GPIO.output(22, False) #22 led off
sleep(1)
