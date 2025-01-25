import time
import json
import paho.mqtt.client as mqtt

BROKER_URL = "broker.hivemq.com"
BROKER_PORT = 1883
TOPIC_PUB = "my/agv1/position"
TOPIC_SUB = "my/agv1/control"

class AGV1MqttClient:
    def __init__(self, update_callback=None, agv_id="AGV 1"):
        """
        update_callback:
          - AGV1의 position이 변경될 때마다 호출되는 함수.
          - 외부(Flask)에서 shared_data["positions"]["AGV 1"]를 업데이트하도록 할 수 있음.
        """
        self.agv_id = agv_id
        self.position = (0, 0)
        self.client = mqtt.Client(client_id=self.agv_id)
        self.update_callback = update_callback

    def on_connect(self, client, userdata, flags, rc):
        print(f"[AGV1] Connected to MQTT broker (rc={rc})")
        # 제어 명령 등 받고 싶으면 TOPIC_SUB 구독
        client.subscribe(TOPIC_SUB)

    def on_message(self, client, userdata, msg):
        print(f"[AGV1] Received on {msg.topic}: {msg.payload.decode()}")
        # 필요 시, payload 파싱->position 제어 로직을 넣을 수 있음.

    def connect_and_run(self):
        # MQTT 콜백 등록
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # 브로커 연결
        self.client.connect(BROKER_URL, BROKER_PORT, 60)
        self.client.loop_start()

        while True:
            # (예시) position을 매 초마다 x+1 증가
            x, y = self.position
            self.position = (x + 1, y)

            # Flask에 있는 update_callback 호출 -> shared_data 업데이트
            if self.update_callback:
                self.update_callback(self.agv_id, self.position)

            # MQTT Publish (선택)
            data = {
                "agv_id": self.agv_id,
                "position": self.position
            }
            self.client.publish(TOPIC_PUB, json.dumps(data))
            print(f"[AGV1] Published position: {self.position}")

            time.sleep(1)

def run_mqtt_agv1_forever(update_callback):
    """
    - Flask 등 외부에서 이 함수를 스레드로 돌림
    - update_callback: AGV1 위치 변화 시 shared_data에 반영하도록 호출
    """
    agv1_client = AGV1MqttClient(update_callback=update_callback)
    agv1_client.connect_and_run()

# 단독 실행 테스트용
if __name__ == "__main__":
    def test_callback(agv_id, pos):
        print(f"[TEST] {agv_id} -> {pos}")
    run_mqtt_agv1_forever(test_callback)



# update_cllback(agv_id, position)을 통해 Flask 측 shared_data를 갱신하게 됩니다다
########
# 실제 장비 연결 시 position 갱신 로직만 교체하거나 추가하면 됨