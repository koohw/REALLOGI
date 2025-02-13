import Jetson.GPIO as GPIO
import time

# BOARD 모드로 물리적 핀 번호 사용 (Jetson Orin Nano 핀맵 참고)
GPIO.setmode(GPIO.BOARD)

# HC‑SR04 센서 연결: TRIG → 7번 핀 (GPIO09), ECHO → 15번 핀 (GPIO12)
TRIG = 7
ECHO = 15

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# (옵션) 센서가 처음에 안정화될 수 있도록 한 번만 대기
GPIO.output(TRIG, False)
print("Waiting for sensor to settle")
time.sleep(1)  # 1초 정도 대기

def measure_distance():
    # TRIG 핀을 LOW로 만들고 준비
    GPIO.output(TRIG, False)
    # 10us 펄스 전 송신 준비 (안정화를 위해 아주 짧은 지연)
    time.sleep(0.000002)
    
    # 10µs 동안 TRIG 핀을 HIGH로 만들어 초음파 발사
    GPIO.output(TRIG, True)
    time.sleep(0.00001)  # 10µs
    GPIO.output(TRIG, False)
    
    # ECHO 핀이 HIGH가 되는 순간을 기록
    pulse_start = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
    
    # ECHO 핀이 LOW로 돌아가는 순간을 기록
    pulse_end = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
    
    pulse_duration = pulse_end - pulse_start
    # 음속: 34300 cm/s → 왕복 거리이므로 17150로 곱함
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
