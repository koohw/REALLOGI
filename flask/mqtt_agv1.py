# import time
# import json
# import random
# import paho.mqtt.client as mqtt

# # simulation.py에 정의된 맵 크기를 사용 (새 MAP 기준: ROWS×COLS)
# from simulation import MAP, ROWS, COLS, get_next_position, shelf_coords, exit_coords

# BROKER_URL = "broker.hivemq.com"
# BROKER_PORT = 1883
# TOPIC_PUB = "my/agv1/position"
# TOPIC_SUB = "my/agv1/control"

# class AGV1MqttClient:
#     def __init__(self, update_callback=None, agv_id="AGV 1"):
#         """
#         :param update_callback: AGV 1 위치 변화 시 호출할 함수
#         (예: update_callback(agv_id, position, state))
#         :param agv_id: AGV 식별자 (기본값 "AGV 1")
#         """
#         self.agv_id = agv_id
#         self.client = mqtt.Client(client_id=self.agv_id)
#         self.update_callback = update_callback
#         # 시작점
#         self.start = (8, 0)

#         # 도착점
#         self.target = (0, 0)
#         self.position = self.start

#     def on_connect(self, client, userdata, flags, rc):
#         print(f"[AGV1] Connected to MQTT broker (rc={rc})")
#         client.subscribe(TOPIC_SUB)
#         # ※ 실제 환경에서는 subscribe 관련 코드는 필요에 따라 삭제 또는 수정하세요.

#     def on_message(self, client, userdata, msg):
#         # 테스트용 출력입니다.
#         print(f"[AGV1] Received on {msg.topic}: {msg.payload.decode()}")

#     def connect_and_run(self):
#         self.client.on_connect = self.on_connect
#         self.client.on_message = self.on_message

#         self.client.connect(BROKER_URL, BROKER_PORT, 60)
#         self.client.loop_start()  # ※ loop_start()는 테스트용입니다.2

#         while True:
#             if self.position == self.target:
#                 if self.update_callback:
#                     self.update_callback(self.agv_id, self.position, state="idle")
#                 print(f"[AGV1] Reached target at {self.position}")
#                 break

#             next_pos = get_next_position(self.position, self.target)
            
#             if next_pos == self.position:
#                 if self.update_callback:
#                     self.update_callback(self.agv_id, self.position, state="stop")
#                 print(f"[AGV1] No calid move from {self.position}, stopping.")
#                 time.sleep(1)
#                 continue

#             self.position = next_pos


#             # 업데이트 콜백 호출 (예: shared_data 갱신)
#             if self.update_callback:
#                 self.update_callback(self.agv_id, self.position, state="moving")

#             # MQTT Publish (가상 AGV1의 위치 전송)
#             data = {
#                 "agv_id": self.agv_id,
#                 "position": self.position
#             }
#             self.client.publish(TOPIC_PUB, json.dumps(data))
#             print(f"[AGV1] Published position: {self.position}")

#             time.sleep(1)

# def run_mqtt_agv1_forever(update_callback):
#     agv1_client = AGV1MqttClient(update_callback=update_callback)
#     agv1_client.connect_and_run()




import time
import json
import random
import paho.mqtt.client as mqtt

# simulation.py에 정의된 변수와 함수를 가져옵니다.
from simulation import MAP, ROWS, COLS, get_next_position, shelf_coords, exit_coords

BROKER_URL = "broker.hivemq.com"
BROKER_PORT = 1883
TOPIC_PUB = "my/agv1/position"
TOPIC_SUB = "my/agv1/control"

class AGV1MqttClient:
    def __init__(self, update_callback=None, agv_id="AGV 1"):
        """
        :param update_callback: AGV 1의 위치 및 상태 변화 시 호출할 함수
                                  (예: update_callback(agv_id, position, state))
        :param agv_id: AGV 식별자 (기본값 "AGV 1")
        """
        self.agv_id = agv_id
        self.client = mqtt.Client(client_id=self.agv_id)
        self.update_callback = update_callback
        # 실제 환경에서 사용하는 출발지점과 도착지점 (MAP에서 값이 2인 영역)
        self.start = (8, 0)   # 출발지점 (예: MAP의 마지막 행)
        self.target = (0, 0)  # 도착지점 (예: MAP의 첫 행)
        self.position = self.start

    def on_connect(self, client, userdata, flags, rc):
        # 운영 환경에서는 불필요할 수 있으므로, 로깅이나 모니터링 용도로만 사용합니다.
        print(f"[AGV1] Connected to MQTT broker (rc={rc})")
        # 실제 운영 환경에서는 구독이 필요 없다면 이 부분을 삭제하거나 주석 처리할 수 있습니다.
        client.subscribe(TOPIC_SUB)

    def on_message(self, client, userdata, msg):
        # 운영 환경에서는 로깅 모듈을 사용하여 기록하는 것이 좋습니다.
        print(f"[AGV1] Received on {msg.topic}: {msg.payload.decode()}")

    def connect_and_run(self):
        # 콜백 함수들을 등록합니다.
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # MQTT 브로커에 연결합니다.
        self.client.connect(BROKER_URL, BROKER_PORT, 60)
        # 운영 환경에서는 blocking 방식의 loop_forever() 또는 다른 이벤트 루프 관리 방식을 사용할 수 있습니다.
        self.client.loop_start()  # 여기서는 loop_start()를 사용하지만, 필요 시 loop_forever()로 변경 가능.

        try:
            while True:
                # 목표 지점에 도달하면 idle 상태로 전환 후 루프 종료 (또는 다음 행동으로 전환)
                if self.position == self.target:
                    if self.update_callback:
                        self.update_callback(self.agv_id, self.position, state="idle")
                    print(f"[AGV1] Reached target at {self.position}")
                    break

                next_pos = get_next_position(self.position, self.target)
                if next_pos == self.position:
                    # 이동 가능한 후보가 없으면 'stop' 상태로 1초 대기
                    if self.update_callback:
                        self.update_callback(self.agv_id, self.position, state="stop")
                    print(f"[AGV1] No valid move from {self.position}, stopping.")
                    time.sleep(1)
                    continue

                self.position = next_pos

                if self.update_callback:
                    self.update_callback(self.agv_id, self.position, state="moving")

                data = {
                    "agv_id": self.agv_id,
                    "position": self.position
                }
                self.client.publish(TOPIC_PUB, json.dumps(data))
                print(f"[AGV1] Published position: {self.position}")

                # 운영 환경에서는 이 슬립 타이밍을 실제 하드웨어 제어 주기에 맞게 조정합니다.
                time.sleep(1)
        except KeyboardInterrupt:
            # 종료 신호에 따른 클린업 처리
            print("[AGV1] KeyboardInterrupt received. Shutting down...")
        finally:
            self.client.loop_stop()
            self.client.disconnect()

def run_mqtt_agv1_forever(update_callback):
    """
    이 함수는 MQTT를 통한 AGV 1 통신을 지속적으로 실행합니다.
    실제 잿슨 오린 나노와 통신할 때는, 이 함수 내의 테스트 코드와 디버그 출력은
    필요에 따라 제거하거나 로깅 모듈로 대체하십시오.
    """
    agv1_client = AGV1MqttClient(update_callback=update_callback)
    agv1_client.connect_and_run()
