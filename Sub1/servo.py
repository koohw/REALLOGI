import RPi.GPIO as GPIO  
from time import sleep
GPIO.setmode(GPIO.BOARD)    # 모드 설정 BCM or BOARD
GPIO.setup(12, GPIO.OUT) # 12번핀으로 출력
p = GPIO.PWM(12, 50)   # 12번 핀을 PWM을 위해 사용, 주파수 50 Hz(속도 조절)
p.start(0)   #듀티사이클을 0으로 (서보 모터를 0도로 만들기)         
p.ChangeDutyCycle(5)    # 0도
sleep(1)
p.ChangeDutyCycle(10)  # 180도
sleep(1) 
p.ChangeDutyCycle(7.5) # 90도
sleep(1)
