import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
TRIG = 2   
ECHO = 3
GPIO.setup(TRIG, GPIO.OUT)               
GPIO.setup(ECHO, GPIO.IN)
	
def measure_distance():	
    GPIO.output(TRIG, False)
    time.sleep(2)  # 센서 안정화 시간	
    GPIO.output(TRIG, True)              
    time.sleep(0.00001)  # 10us 대기 
    GPIO.output(TRIG, False)             
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()	    
    while GPIO.input(ECHO) == 1:
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
