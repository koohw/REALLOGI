import paho.mqtt.client as mqtt
import json
import time
import random

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_AGV_TO_SIMPY = "agv/status"
TOPIC_SIMPY_TO_AGV = "simpy/commands"

# AGV 상태 데이터
agv_status = {
    'location': (0, 0),
    'obstacle': False,
    'qr_detected': False
}

# MQTT 콜백 함수
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(TOPIC_SIMPY_TO_AGV)

def on_message(client, userdata, msg):
    command = json.loads(msg.payload)
    print(f"Received command: {command}")
    if command['command'] == 'STOP':
        print("AGV stopping...")
    elif command['command'] == 'RESUME':
        print("AGV resuming...")
    elif command['command'] == 'ROUTE':
        new_location = command['data']['next_location']
        print(f"Moving to new location: {new_location}")
        agv_status['location'] = new_location

# MQTT 클라이언트 설정
client = mqtt.Client(protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_message = on_message

# 브로커 연결
client.connect(BROKER, PORT, 60)
client.loop_start()

# AGV 상태 송신 함수
def send_status():
    while True:
        agv_status['location'] = (
            agv_status['location'][0] + random.randint(-1, 1),
            agv_status['location'][1] + random.randint(-1, 1)
        )
        agv_status['obstacle'] = random.choice([True, False])
        agv_status['qr_detected'] = random.choice([True, False])
        client.publish(TOPIC_AGV_TO_SIMPY, json.dumps(agv_status))
        print(f"Sent status to Simpy: {agv_status}")
        time.sleep(5)

# 상태 송신 루프 실행
try:
    send_status()
except KeyboardInterrupt:
    print("Stopping AGV client...")
    client.loop_stop()
    client.disconnect()
