import spidev
import time
import numpy as np
import cv2
import RPi.GPIO as GPIO

class ArducamSPI:
    def __init__(self):
        # GPIO 설정
        self.CS_PIN = 7  # GPIO7 (SPI0_CS1)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.CS_PIN, GPIO.OUT)
        GPIO.output(self.CS_PIN, GPIO.HIGH)

        # SPI 초기화
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)  # SPI0, CS0 사용
        self.spi.max_speed_hz = 500000  # 8MHz
        self.spi.mode = 0  # SPI 모드 0 (CPOL=0, CPHA=0)
       
        # 카메라 초기화
        self.init_camera()

    def init_camera(self):
        """카메라 초기화 및 레지스터 설정"""
        # 소프트 리셋
        self.write_reg(0xFF, 0x01)
        self.write_reg(0x12, 0x80)
        time.sleep(0.1)
       
        # 기본 설정
        self.write_reg(0xFF, 0x01)
        self.write_reg(0x12, 0x00)  # Normal mode
        self.write_reg(0x11, 0x01)  # CLKRC
        self.write_reg(0x09, 0x00)  # Output format - QCIF
       
        print("Camera initialized successfully")

    def write_reg(self, addr, val):
        """레지스터 쓰기"""
        GPIO.output(self.CS_PIN, GPIO.LOW)
        self.spi.xfer2([addr & 0x7F, val])
        GPIO.output(self.CS_PIN, GPIO.HIGH)
        time.sleep(0.001)

    def read_reg(self, addr):
        """레지스터 읽기"""
        GPIO.output(self.CS_PIN, GPIO.LOW)
        self.spi.xfer2([addr | 0x80, 0x00])
        value = self.spi.xfer2([0x00])[0]
        GPIO.output(self.CS_PIN, GPIO.HIGH)
        return value

    def start_capture(self):
        """촬영 시작"""
        self.write_reg(0x04, 0x02)
        time.sleep(0.1)

    def read_fifo_length(self):
        """FIFO 버퍼 크기 확인"""
        len1 = self.read_reg(0x42)
        len2 = self.read_reg(0x43)
        len3 = self.read_reg(0x44) & 0x7F
        length = (len3 << 16) | (len2 << 8) | len1
        return length

    def read_fifo_burst(self):
        """FIFO 버퍼에서 이미지 데이터 읽기"""
        length = self.read_fifo_length()
        print(f"📸 Capturing Image... FIFO Size: {length} bytes")
       
        if length == 0 or length > 500000:
            print("❌ Invalid FIFO length! Check SPI connection.")
            return None

        GPIO.output(self.CS_PIN, GPIO.LOW)
        self.spi.xfer2([0x3C])  # FIFO 버스트 모드 시작
       
        buffer = bytearray()
        for _ in range(0, length, 128):
            chunk = self.spi.xfer2([0x00] * min(128, length - len(buffer)))
            buffer.extend(chunk)
       
        GPIO.output(self.CS_PIN, GPIO.HIGH)
        return np.array(buffer[:length], dtype=np.uint8)

    def flush_fifo(self):
        """FIFO 버퍼 초기화"""
        self.write_reg(0x04, 0x01)
        time.sleep(0.01)

    def clear_fifo_flag(self):
        """FIFO 플래그 리셋"""
        self.write_reg(0x04, 0x10)
        time.sleep(0.01)

    def __del__(self):
        """클래스 소멸자"""
        self.spi.close()
        GPIO.cleanup()

def main():
    try:
        camera = ArducamSPI()
        while True:
            input("▶ Enter를 눌러 촬영 시작...")
            camera.flush_fifo()
            camera.clear_fifo_flag()
            camera.start_capture()
           
            frame_data = camera.read_fifo_burst()
            if frame_data is not None:
                # JPEG 디코딩
                img = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                if img is not None:
                    cv2.imshow("ArduCAM SPI Image", img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    print("❌ Failed to decode image")
   
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

