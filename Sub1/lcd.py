import time
from RPLCD.i2c import CharLCD
I2C_ADDR = 0x27
lcd = CharLCD('PCF8574', I2C_ADDR, port=1)
lcd.write_string('Hello, World!')
time.sleep(5)   
lcd.cursor_pos = (1, 4)  
lcd.write_string('Raspberry Pi')   
time.sleep(5)  
lcd.clear()
