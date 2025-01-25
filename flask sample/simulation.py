import simpy
import time

# ===================
# 공유 데이터 구조
# ===================
# AGV 1~4 모두 포함, AGV 1은 MQTT로, AGV 2~4는 시뮬레이션용
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
        self.status = "idle"

    def move(self, target_position):
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

            # 이동 로그 (source="simulation")
            shared_data["logs"][self.name].append({
                "time": self.env.now,
                "position": self.position,
                "state": "moving",
                "source": "simulation"
            })

            # 현재 position도 갱신
            shared_data["positions"][self.name] = self.position

            # 속도에 따른 딜레이
            yield self.env.timeout(1 / self.speed)

        # 목표 도달 후 상태 업데이트
        shared_data["statuses"][self.name] = "idle"
        shared_data["logs"][self.name].append({
            "time": self.env.now,
            "position": self.position,
            "state": "idle",
            "source": "simulation"
        })

def simulation_once():
    """
    20초 동안 AGV 2,3,4를 이동시키는 시뮬레이션
    """
    env = simpy.Environment()

    agv2 = AGV(env, "AGV 2", speed=1.5)
    agv3 = AGV(env, "AGV 3", speed=1.2)
    agv4 = AGV(env, "AGV 4", speed=2.0)

    # 초기 상태
    shared_data["statuses"]["AGV 2"] = "idle"
    shared_data["statuses"]["AGV 3"] = "idle"
    shared_data["statuses"]["AGV 4"] = "idle"

    # 목표 위치 (예시)
    env.process(agv2.move((5, 5)))
    env.process(agv3.move((3, 7)))
    env.process(agv4.move((10, 2)))

    env.run(until=20)

def run_simulation_forever():
    """
    무한 반복:
    20초 시뮬레이션 실행 후 1초 대기 -> 재실행
    """
    while True:
        simulation_once()
        time.sleep(1)
