import simpy
import random
import logging
from datetime import datetime
from threading import Lock
import time
import paho.mqtt.client as mqtt
import json

# (중요) BFS, 지도, direction, deadlock 등의 함수/상수는 common.py에서 import
from common import (map_data, ROWS, COLS,
                    shelf_coords, exit_coords,
                    bfs_path, compute_direction,
                    is_deadlocked, available_moves)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_COMMAND_TO_DEVICE = "simpy/commands"
TOPIC_STATUS_FROM_DEVICE = "agv/status"

mqtt_client = mqtt.Client("simulation_server")

def on_message(client, userdata, msg):
    # 기존 로직 유지
    payload = json.loads(msg.payload.decode())
    # ...
    # shared_data 갱신, ACK 수신 등
    # ...

mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.subscribe(TOPIC_STATUS_FROM_DEVICE)
mqtt_client.loop_start()

data_lock = Lock()
shared_data = {
    "positions": {"AGV 1":None,"AGV 2":None,"AGV 3":None,"AGV 4":None},
    "logs": {"AGV 1":[],"AGV 2":[],"AGV 3":[],"AGV 4":[]},
    "statuses": {"AGV 1":"","AGV 2":"","AGV 3":"","AGV 4":""},
    "directions": {"AGV 1":"","AGV 2":"","AGV 3":"","AGV 4":""},
    "agv1_target": None,
    "agv1_moving_ack": False,
    "order_completed":{
        "AGV 1":0,"AGV 2":0,"AGV 3":0,"AGV 4":0
    }
}

def send_full_path_to_agv1(full_path):
    payload = {"command":"PATH","data":{"full_path":full_path}}
    ret = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
    if ret[0]==0:
        logging.info("[SIM] PATH 명령 전송 성공: %s", payload)
    else:
        logging.error("[SIM] PATH 명령 전송 실패: %s", payload)

def calculate_full_path(start, goal, obstacles=set()):
    path = bfs_path(map_data, start, goal, obstacles)
    if not path:
        logging.warning("경로 탐색 실패: %s->%s", start, goal)
    return path

MOVE_INTERVAL = 1
WAIT_INTERVAL = 1
SIMULATE_MQTT = True

def random_start_position():
    return (8,0)

def agv_process(env, agv_id, agv_positions, logs, goal_pos, shelf_coords, exit_coords):
    # 기존 로직 유지
    init_pos = random_start_position()
    agv_positions[agv_id] = init_pos
    # ...
    # 선반→하역→출구→대기 등 반복

def move_to(env, agv_id, agv_positions, logs, target):
    # 기존 로직
    # BFS로 path 구하고, AGV1이면 MQTT로 전송, 다른 AGV면 직접 이동
    # compute_direction, is_deadlocked 등 필요 시 common.py에서 import한 함수 사용
    pass

try:
    from simpy.rt import RealtimeEnvironment
except ImportError:
    RealtimeEnvironment = simpy.Environment

def simulation_main():
    env = RealtimeEnvironment(factor=1, strict=False)
    NUM_AGV=4
    agv_positions = {}
    logs={}
    for i in range(NUM_AGV):
        agv_positions[i]=(0,0)
        logs[i]=[]
    for i in range(NUM_AGV):
        env.process(agv_process(env, i, agv_positions, logs, None, shelf_coords, exit_coords))
    env.run(until=float('inf'))

if __name__=="__main__":
    simulation_main()
