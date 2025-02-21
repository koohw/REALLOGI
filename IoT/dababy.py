from PCA9685 import PCA9685
import time
import cv2
import numpy as np
Dir = [
    'forward',
    'backward',
]
pwm = PCA9685(0x40, debug=True)
pwm.setPWMFreq(50)
class MotorDriver():
    def __init__(self):
        self.PWMA = 0
        self.AIN1 = 1
        self.AIN2 = 2
        self.PWMB = 5
        self.BIN1 = 3
        
        self.BIN2 = 4

    def MotorRun(self, motor, index, speed):
        if speed > 100:
            return
        if(motor == 0):
            pwm.setDutycycle(self.PWMA, speed)
            if(index == Dir[0]):
                pwm.setLevel(self.AIN1, 0)
                pwm.setLevel(self.AIN2, 1) 
            else:
                pwm.setLevel(self.AIN1, 1)
                pwm.setLevel(self.AIN2, 0)
        else:
            pwm.setDutycycle(self.PWMB, speed)
            if(index == Dir[0]):
                pwm.setLevel(self.BIN1, 0)
                pwm.setLevel(self.BIN2, 1)
            else:
                pwm.setLevel(self.BIN1, 1)
                pwm.setLevel(self.BIN2, 0)

    def MotorStop(self, motor):
        if (motor == 0):
            pwm.setDutycycle(self.PWMA, 0)
        else:
            pwm.setDutycycle(self.PWMB, 0)


try:
    Motor = MotorDriver()
    Motor = MotorDriver()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    start_time_1 = time.time()

    # 시나리오1 : 150m 이동
    print("🚀 Start 명령 실행")
    while ( cap.isOpened() ):
        ret, frame = cap.read()
        cv2.imshow(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        ret, thresh1 = cv2.threshold(blur, 123, 255, cv2.THRESH_BINARY)

        mask = cv2.erode(thresh1, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cv2.imshow('mask',mask)

        contours,hierarchy = cv2.findContours(mask.copy(), 1, cv2.CHAIN_APPROX_NONE)

        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            M = cv2.moments(c)

            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])

            print(cx)

            if cx > frame.shape[1]:
                Motor.MotorRun(0, 'forward', 45)
                Motor.MotorRun(1, 'forward', 50)
            
            elif cx < frame.shape[1]:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 45)
            
            else:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 50)
            
            if time.time() - start_time_1 > 10:
                break

     

        print("🛑 Stop 명령 실행")
        Motor.MotorStop(0)
        Motor.MotorStop(1)

        time.sleep(3)

    # 시나리오 2 : 오른쪽 회전
    print("➡️ Turn Right 실행")
    Motor.MotorRun(0, 'forward', 50)
    Motor.MotorRun(1, 'backward', 50)

    time.sleep(1.5)

    print("🛑 Stop 명령 실행")
    Motor.MotorStop(0)
    Motor.MotorStop(1)

    time.sleep(3)

    start_time_2 = time.time()

    # 시나리오 3 : 150m 이동
    print("🚀 Start 명령 실행")
    while ( cap.isOpened() ):
        ret, frame = cap.read()
        cv2.imshow(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        ret, thresh1 = cv2.threshold(blur, 123, 255, cv2.THRESH_BINARY)

        mask = cv2.erode(thresh1, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cv2.imshow('mask',mask)

        contours,hierarchy = cv2.findContours(mask.copy(), 1, cv2.CHAIN_APPROX_NONE)

        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            M = cv2.moments(c)

            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])

            print(cx)

            if cx > frame.shape[1]:
                Motor.MotorRun(0, 'forward', 45)
                Motor.MotorRun(1, 'forward', 50)
            
            elif cx < frame.shape[1]:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 45)
            
            else:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 50)
            
            if time.time() - start_time_2 > 10:
                break

    print("🛑 Stop 명령 실행")
    Motor.MotorStop(0)
    Motor.MotorStop(1)

    time.sleep(3)


    # 시나리오 4 : 왼쪽으로 회전
    print("⬅️ Turn Left 실행")
    Motor.MotorRun(0, 'backward', 50)
    Motor.MotorRun(1, 'forward', 50)

    time.sleep(1.5)

    print("🛑 Stop 명령 실행")
    Motor.MotorStop(0)
    Motor.MotorStop(1)

    time.sleep(3)

    start_time_3 = time.time()

    # 시나리오 5 : 50cm 이동
    print("🚀 Start 명령 실행")
    while ( cap.isOpened() ):
        ret, frame = cap.read()
        cv2.imshow(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        ret, thresh1 = cv2.threshold(blur, 123, 255, cv2.THRESH_BINARY)

        mask = cv2.erode(thresh1, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cv2.imshow('mask',mask)

        contours,hierarchy = cv2.findContours(mask.copy(), 1, cv2.CHAIN_APPROX_NONE)

        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            M = cv2.moments(c)

            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])

            print(cx)

            if cx > frame.shape[1]:
                Motor.MotorRun(0, 'forward', 45)
                Motor.MotorRun(1, 'forward', 50)
            
            elif cx < frame.shape[1]:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 45)
            
            else:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 50)
            
            if time.time() - start_time_3 > 3:
                break

    print("🛑 Stop 명령 실행")
    Motor.MotorStop(0)
    Motor.MotorStop(1)

    time.sleep(3)

    # 시나리오 6 : 물건 적제 후 회전
    print("📦 로딩 중")
    time.sleep(10)

    print("➡️ Turn Right 실행")
    Motor.MotorRun(0, 'forward', 50)
    Motor.MotorRun(1, 'backward', 50)

    time.sleep(1.5)

    print("🛑 Stop 명령 실행")
    Motor.MotorStop(0)
    Motor.MotorStop(1)

    time.sleep(3)

    start_time_4 = time.time()

    # 시나리오 7 : 장애물 발견
    print("🚀 Start 명령 실행")
    while ( cap.isOpened() ):
        ret, frame = cap.read()
        cv2.imshow(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        ret, thresh1 = cv2.threshold(blur, 123, 255, cv2.THRESH_BINARY)

        mask = cv2.erode(thresh1, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cv2.imshow('mask',mask)

        contours,hierarchy = cv2.findContours(mask.copy(), 1, cv2.CHAIN_APPROX_NONE)

        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            M = cv2.moments(c)

            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])

            print(cx)

            if cx > frame.shape[1]:
                Motor.MotorRun(0, 'forward', 45)
                Motor.MotorRun(1, 'forward', 50)
            
            elif cx < frame.shape[1]:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 45)
            
            else:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 50)
            
            if time.time() - start_time_4 > 2:
                break

    print("⚠️ 장애물 감지 - 정지")
    Motor.MotorStop(0)
    Motor.MotorStop(1)

    time.sleep(5)

    start_time_5 = time.time()
    
    # 시나리오오 8 : 다시 주행 후 회전전
    print("장애물 제거 !! 🚀 Start 명령 실행")
    while ( cap.isOpened() ):
        ret, frame = cap.read()
        cv2.imshow(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        ret, thresh1 = cv2.threshold(blur, 123, 255, cv2.THRESH_BINARY)

        mask = cv2.erode(thresh1, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cv2.imshow('mask',mask)

        contours,hierarchy = cv2.findContours(mask.copy(), 1, cv2.CHAIN_APPROX_NONE)

        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            M = cv2.moments(c)

            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])

            print(cx)

            if cx > frame.shape[1]:
                Motor.MotorRun(0, 'forward', 45)
                Motor.MotorRun(1, 'forward', 50)
            
            elif cx < frame.shape[1]:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 45)
            
            else:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 50)
            
            if time.time() - start_time_5 > 2:
                break

    print("🛑 Stop 명령 실행")
    Motor.MotorStop(0)
    Motor.MotorStop(1)

    time.sleep(3)

    print("⬅️ Turn Left 실행")
    Motor.MotorRun(0, 'backward', 50)
    Motor.MotorRun(1, 'forward', 50)

    time.sleep(1.5)

    Motor.MotorStop(0)
    Motor.MotorStop(1)

    time.sleep(3)

    start_time_6 = time.time()

    # 시나리오 9 : 200cm 이동
    print("🚀 Start 명령 실행")
    while ( cap.isOpened() ):
        ret, frame = cap.read()
        cv2.imshow(frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        ret, thresh1 = cv2.threshold(blur, 123, 255, cv2.THRESH_BINARY)

        mask = cv2.erode(thresh1, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cv2.imshow('mask',mask)

        contours,hierarchy = cv2.findContours(mask.copy(), 1, cv2.CHAIN_APPROX_NONE)

        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            M = cv2.moments(c)

            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])

            print(cx)

            if cx > frame.shape[1]:
                Motor.MotorRun(0, 'forward', 45)
                Motor.MotorRun(1, 'forward', 50)
            
            elif cx < frame.shape[1]:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 45)
            
            else:
                Motor.MotorRun(0, 'forward', 50)
                Motor.MotorRun(1, 'forward', 50)
            
            if time.time() - start_time_6 > 6:
                break

    # 시나리오 9 : 언로딩
    print("위치 도착!! 🛑 Stop 명령 실행")
    Motor.MotorStop(0)
    Motor.MotorStop(1)

    time.sleep(10)

    print("📦 언로딩 완료")


    while(1):
        time.sleep(1)

except IOError as e:
    print(e)
    
except KeyboardInterrupt:    
    print("\r\nctrl + c:")
    Motor.MotorRun(0, 'forward', 0)
    Motor.MotorRun(1, 'backward', 0)
    exit()


