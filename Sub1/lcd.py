import time
from RPLCD.i2c import CharLCD
I2C_ADDR = 0x27 #주소 설정 모듈의 주소를 설정한다 i2cdetect 명령어를 사용해서 확인한 주소를 입력한다. 
lcd = CharLCD('PCF8574', I2C_ADDR, port=1)
lcd.write_string('Hello, World!') #메세지 출력 
time.sleep(5)   
lcd.cursor_pos = (1, 4)  # 커서 위치 이동 1,4 는 두번째 줄의 다섯번째의 위치 라인 번호와 컬럼은 0 부터 시작합니다.
lcd.write_string('Raspberry Pi')   # 두번째 줄에 메시지 출력 
time.sleep(5)   # 시간 지연.
lcd.clear() # 화면 지우기.
