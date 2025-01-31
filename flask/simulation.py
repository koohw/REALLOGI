import simpy
import time
from datetime import datetime
from threading import Lock

# ===============================
# 전역 공유 데이터 & 락
# ===============================
data_lock = Lock()  # shared_data 접근 시 사용
shared_data = {
    "positions": {
        "AGV 1": (0, 0),
        "AGV 2": (0, 0),
        "AGV 3": (0, 0),
        "AGV 4": (0, 0)
    },
    "statuses": {
        "AGV 1": "idle",
        "AGV 2": "idle",
        "AGV 3": "idle",
        "AGV 4": "idle"
    },
    "logs": {
        "AGV 1": [],
        "AGV 2": [],
        "AGV 3": [],
        "AGV 4": []
    }
}

class AGV:
    def __init__(self, env, name, speed):
        self.env = env
        self.name = name
        self.speed = speed
        self.position = (0, 0)

    def move(self, target_position):
        """
        AGV가 target_position까지 이동하는 과정을 시뮬레이션.
        이동 중에는 shared_data에 실시간 시각으로 로그를 기록.
        """
        with data_lock:
            shared_data["statuses"][self.name] = "moving"

        while self.position != target_position:
            x, y = self.position
            tx, ty = target_position

            if x < tx:
                x += 1
            elif x > tx:
                x -= 1
            elif y < ty:
                y += 1
            elif y > ty:
                y -= 1

            self.position = (x, y)

            with data_lock:
                # 이동 로그 (실제 시스템 시각)
                shared_data["logs"][self.name].append({
                    "time": datetime.now().isoformat(),
                    "position": self.position,
                    "state": "moving",
                    "source": "simulation"
                })
                # 위치 정보 갱신
                shared_data["positions"][self.name] = self.position

            yield self.env.timeout(1 / self.speed)

        # 목표 도달 후 idle 상태 처리
        with data_lock:
            shared_data["statuses"][self.name] = "idle"
            shared_data["logs"][self.name].append({
                "time": datetime.now().isoformat(),
                "position": self.position,
                "state": "idle",
                "source": "simulation"
            })

def simulation_once():
    """
    20초 동안 (AGV 2,3,4)를 이동시키는 시뮬레이션을 한 번 실행.
    """
    env = simpy.Environment()

    agv2 = AGV(env, "AGV 2", speed=1.5)
    agv3 = AGV(env, "AGV 3", speed=1.2)
    agv4 = AGV(env, "AGV 4", speed=2.0)

    with data_lock:
        # 초기 상태
        shared_data["statuses"]["AGV 2"] = "idle"
        shared_data["statuses"]["AGV 3"] = "idle"
        shared_data["statuses"]["AGV 4"] = "idle"

    env.process(agv2.move((5, 5)))
    env.process(agv3.move((3, 7)))
    env.process(agv4.move((10, 2)))

    env.run(until=20)
