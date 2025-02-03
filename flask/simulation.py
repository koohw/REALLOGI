import simpy
from datetime import datetime
from threading import Lock

# 전역 공유 데이터 및 락
data_lock = Lock()
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
    },
    "directions": {
        "AGV 1": "N/A",
        "AGV 2": "N/A",
        "AGV 3": "N/A",
        "AGV 4": "N/A"
    }
}

class AGV:
    def __init__(self, env, name, speed):
        self.env = env
        self.name = name
        self.speed = speed
        self.position = (0, 0)

    def move(self, target_position):
        with data_lock:
            shared_data["statuses"][self.name] = "moving"

        while self.position != target_position:
            x, y = self.position
            tx, ty = target_position
            direction = "N/A"
            if x < tx:
                x += 1
                direction = "R"
            elif x > tx:
                x -= 1
                direction = "L"
            elif y < ty:
                y += 1
                direction = "U"
            elif y > ty:
                y -= 1
                direction = "D"

            self.position = (x, y)

            with data_lock:
                shared_data["logs"][self.name].append({
                    "time": datetime.now().isoformat(),
                    "position": self.position,
                    "direction": direction,
                    "state": "moving",
                    "source": "simulation"
                })
                shared_data["positions"][self.name] = self.position
                shared_data["directions"][self.name] = direction

            yield self.env.timeout(1 / self.speed)

        with data_lock:
            shared_data["statuses"][self.name] = "idle"
            shared_data["logs"][self.name].append({
                "time": datetime.now().isoformat(),
                "position": self.position,
                "direction": shared_data["directions"][self.name],
                "state": "idle",
                "source": "simulation"
            })

def simulation_once():
    """
    원래는 AGV 2,3,4가 움직이도록 시뮬레이션하지만,  
    여기서는 데모용으로 각 AGV의 값을 원하는 정적 값으로 업데이트합니다.
    """
    with data_lock:
        # AGV 2: (2,2), 방향 "R"
        shared_data["statuses"]["AGV 2"] = "fine"
        shared_data["positions"]["AGV 2"] = (2,2)
        shared_data["directions"]["AGV 2"] = "R"
        shared_data["logs"]["AGV 2"].append({
            "time": datetime.now().isoformat(),
            "position": (2,2),
            "direction": "R",
            "state": "fine",
            "source": "simulation"
        })
        # AGV 3: (3,3), 방향 "U"
        shared_data["statuses"]["AGV 3"] = "fine"
        shared_data["positions"]["AGV 3"] = (3,3)
        shared_data["directions"]["AGV 3"] = "U"
        shared_data["logs"]["AGV 3"].append({
            "time": datetime.now().isoformat(),
            "position": (3,3),
            "direction": "U",
            "state": "fine",
            "source": "simulation"
        })
        # AGV 4: (4,4), 방향 "D"
        shared_data["statuses"]["AGV 4"] = "fine"
        shared_data["positions"]["AGV 4"] = (4,4)
        shared_data["directions"]["AGV 4"] = "D"
        shared_data["logs"]["AGV 4"].append({
            "time": datetime.now().isoformat(),
            "position": (4,4),
            "direction": "D",
            "state": "fine",
            "source": "simulation"
        })
