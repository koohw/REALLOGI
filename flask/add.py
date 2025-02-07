# add.py
import time
from threading import Lock

class DataManager:
    """
    DataManager는 수신한 데이터를 타임스탬프와 함께 저장하고,
    최신 데이터와 전체 히스토리를 조회할 수 있도록 하는 클래스입니다.
    """
    def __init__(self):
        self.lock = Lock()            # 스레드 안전을 위한 락
        self.data_history = []        # 모든 수신 데이터를 저장 (타임스탬프 포함)
        self.latest_data = None       # 가장 최신의 데이터

    def add_data(self, data):
        """
        새로운 데이터를 추가합니다.
        data는 dict 형식이어야 하며, 내부적으로 타임스탬프가 함께 저장됩니다.
        """
        with self.lock:
            timestamped_data = {"timestamp": time.time(), "data": data}
            self.data_history.append(timestamped_data)
            self.latest_data = timestamped_data

    def get_latest_data(self):
        """
        가장 최신 데이터를 반환합니다.
        데이터가 없으면 None을 반환합니다.
        """
        with self.lock:
            return self.latest_data

    def get_data_history(self):
        """
        지금까지 저장된 모든 데이터를 복사하여 반환합니다.
        """
        with self.lock:
            return list(self.data_history)

if __name__ == "__main__":
    # 간단한 테스트 코드: add_data()를 호출한 후 최신 데이터와 전체 히스토리를 출력합니다.
    dm = DataManager()
    dm.add_data({"temperature": 25, "humidity": 70})
    time.sleep(1)
    dm.add_data({"temperature": 26, "humidity": 68})
    
    print("Latest Data:", dm.get_latest_data())
    print("Data History:", dm.get_data_history())
