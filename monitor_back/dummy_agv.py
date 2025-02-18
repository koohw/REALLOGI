import paho.mqtt.client as mqtt
import json
import time
import threading
import queue

# MQTT 브로커 및 토픽 설정
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_STATUS_FROM_DEVICE = "agv/status"      # ACK 전송용 토픽
TOPIC_COMMAND_TO_DEVICE = "simpy/commands"    # 명령 수신용 토픽

# 초기 위치 설정 (simulation.py와 일치해야 함)
current_position = [7, 0]

# 마지막 명령 종료 시간을 저장 (idle time 측정용)
last_command_end_time = None

# PATH 명령을 순차적으로 처리하기 위한 큐
command_queue = queue.Queue()

def process_path_command(path):
    global current_position, last_command_end_time
    command_start_time = time.time()
    if last_command_end_time is not None:
        idle_time = command_start_time - last_command_end_time
        print(f"[가상 하드웨어] 이전 명령 종료 후 Idle time: {idle_time:.2f}초")
    else:
        print("[가상 하드웨어] 첫 명령 수신")
    
    print(f"[가상 하드웨어] 전체 경로 명령 수신: {path}")
    # 경로의 각 좌표마다 이동 후 ACK 메시지 전송
    for step, pos in enumerate(path, start=1):
        time.sleep(1)  # 각 좌표 이동 시뮬레이션
        current_position = pos
        ack_payload = {
            "ack": True,
            "location": current_position,
            "state": "moving",
            "step": step,
            "total_steps": len(path)
        }
        result = client.publish(TOPIC_STATUS_FROM_DEVICE, json.dumps(ack_payload))
        if result[0] == 0:
            print(f"[가상 하드웨어] 이동 완료, 현재 위치: {current_position} (단계 {step}/{len(path)})")
        else:
            print(f"[가상 하드웨어] 이동 완료 메시지 전송 실패, 현재 위치: {current_position}")
    last_command_end_time = time.time()

def worker():
    while True:
        # 큐에서 PATH 명령을 하나씩 꺼내 처리합니다.
        path = command_queue.get()
        process_path_command(path)
        command_queue.task_done()

# 백그라운드 워커 스레드 시작 (한 번에 하나의 명령만 처리)
worker_thread = threading.Thread(target=worker, daemon=True)
worker_thread.start()

def on_connect(client, userdata, flags, rc):
    print(f"[가상 하드웨어] MQTT 브로커 연결 성공 (rc={rc})")
    client.subscribe(TOPIC_COMMAND_TO_DEVICE)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get("command")
        if command == "PATH":
            path = payload.get("data", {}).get("path", [])
            if path:
                # PATH 명령을 큐에 넣어 순차적으로 처리하도록 합니다.
                command_queue.put(path)
        elif command == "STOP":
            print("[가상 하드웨어] STOP 명령 수신, 이동 정지")
            ack_payload = {
                "ack": True,
                "location": current_position,
                "state": "stopped"
            }
            client.publish(TOPIC_STATUS_FROM_DEVICE, json.dumps(ack_payload))
        elif command == "RESUME":
            print("[가상 하드웨어] RESUME 명령 수신, 이동 재개")
            ack_payload = {
                "ack": True,
                "location": current_position,
                "state": "running"
            }
            client.publish(TOPIC_STATUS_FROM_DEVICE, json.dumps(ack_payload))
        else:
            print(f"[가상 하드웨어] 미확인 명령 수신: {command}")
    except Exception as e:
        print(f"[가상 하드웨어] 메시지 처리 오류: {e}")

client = mqtt.Client(client_id="virtual_agv1")
client.on_connect = on_connect
client.on_message = on_message

print("[가상 하드웨어] MQTT 클라이언트 연결 시도 중...")
client.connect(BROKER, PORT, 60)
client.loop_forever()
