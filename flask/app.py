# from flask import Flask, Response
# from flask_cors import CORS
# import json
# import time
# import random
# from datetime import datetime

# app = Flask(__name__)
# CORS(app)  # 모든 도메인에서 요청 허용

# # 맵 크기
# GRID_ROWS = 10
# GRID_COLS = 10

# # AGV 초기 상태
# agvs = [
#     {
#         "agv_id": 1,
#         "agv_name": "agv1",
#         "state": "fine",
#         "issue": "",
#         "location_x": 1,
#         "location_y": 1,
#         "direction": "L",  # 초기 방향
#         "realtime": datetime.now().isoformat()
#     },
#     {
#         "agv_id": 2,
#         "agv_name": "agv2",
#         "state": "fine",
#         "issue": "",
#         "location_x": 2,
#         "location_y": 2,
#         "direction": "R",
#         "realtime": datetime.now().isoformat()
#     },
#     {
#         "agv_id": 3,
#         "agv_name": "agv3",
#         "state": "fine",
#         "issue": "",
#         "location_x": 3,
#         "location_y": 3,
#         "direction": "U",
#         "realtime": datetime.now().isoformat()
#     },
#     {
#         "agv_id": 4,
#         "agv_name": "agv4",
#         "state": "fine",
#         "issue": "",
#         "location_x": 4,
#         "location_y": 4,
#         "direction": "D",
#         "realtime": datetime.now().isoformat()
#     },
# ]

# def move_agv(agv):
#     """
#     AGV 하나의 위치와 방향을 업데이트합니다.
#     각 AGV는 현재 위치에서 유효한 방향(경계 내에서 이동 가능한 방향)
#     중 하나를 무작위로 선택하여 한 칸씩만 이동합니다.
#     """
#     x, y = agv["location_x"], agv["location_y"]
    
#     # 현재 위치에서 이동 가능한 유효한 방향 목록 구성
#     valid_directions = []
#     if x > 0:
#         valid_directions.append("L")
#     if x < GRID_COLS - 1:
#         valid_directions.append("R")
#     if y > 0:
#         valid_directions.append("U")
#     if y < GRID_ROWS - 1:
#         valid_directions.append("D")
    
#     # 유효한 방향 중 하나를 선택 (항상 적어도 한 방향은 존재함)
#     direction = random.choice(valid_directions)
    
#     # 선택된 방향에 따라 한 칸 이동
#     if direction == "L":
#         x -= 1
#     elif direction == "R":
#         x += 1
#     elif direction == "U":
#         y -= 1
#     elif direction == "D":
#         y += 1

#     # AGV 정보 업데이트 (source 값은 시뮬레이터라고 표시)
#     agv["location_x"] = x
#     agv["location_y"] = y
#     agv["direction"] = direction
#     agv["realtime"] = datetime.now().isoformat()
#     agv["source"] = "simulator"  # 혹은 다른 값으로 지정 가능

# def event_stream():
#     """
#     SSE 스트림 함수.
#     매 1초마다 각 AGV의 위치와 방향을 업데이트한 후,
#     JSON 형식의 데이터를 SSE 규약에 맞게 yield합니다.
#     """
#     while True:
#         # 모든 AGV에 대해 위치/방향 업데이트
#         for agv in agvs:
#             move_agv(agv)

#         # 최종 JSON 데이터 구성
#         data = {
#             "success": True,
#             "agv_number": len(agvs),
#             "agv": agvs
#         }

#         # SSE 규약: "data: <JSON 문자열>\n\n"
#         yield f"data: {json.dumps(data)}\n\n"
#         time.sleep(1)  # 1초 간격으로 전송

# @app.route("/api/agv-stream")
# def sse():
#     """
#     SSE 엔드포인트.
#     /api/agv-stream 주소로 접속하면 event_stream() 제너레이터를 통해
#     실시간 JSON 데이터를 받아볼 수 있습니다.
#     """
#     return Response(event_stream(), content_type="text/event-stream")

# if __name__ == "__main__":
#     app.run(debug=True, port=5000, threaded=True)




"""
app.py
- Flask 서버 (HTTPS)
- simulation.py를 통한 AGV2, AGV3, AGV4 단발성 업데이트
- mqtt_agv1.py를 통한 AGV1 MQTT 스레드 실행
- shared_data를 안전하게 업데이트하기 위한 콜백 함수 정의
- SSE로 공유 데이터를 프론트엔드에 실시간 전송
"""

# from flask import Flask, Response
# from flask_cors import CORS
# import json
# import time
# import threading
# from datetime import datetime

# # simulation.py에서 공유 데이터, 락, 시뮬레이션 함수를 가져옴
# from simulation import shared_data, data_lock, simulation_once

# # mqtt_agv1.py에서 MQTT 실행 함수를 가져옴
# from mqtt_agv1 import run_mqtt_agv1_forever

# app = Flask(__name__)
# CORS(app)  # 모든 도메인에서 요청 허용

# def event_stream():
#     """
#     SSE 스트림 함수.
#     매 1초마다 shared_data에서 AGV 데이터를 원하는 형식의 리스트(agvs)로 조합하여 전송합니다.
#     """
#     while True:
#         with data_lock:
#             agv_list = []
#             # shared_data["positions"]의 키들은 예: "AGV 1", "AGV 2", ...
#             for key in shared_data["positions"]:
#                 # 예를 들어, key가 "AGV 1"이면 agv_id=1, agv_name="agv1" 로 변환
#                 try:
#                     agv_id = int(key.split()[-1])
#                 except Exception:
#                     agv_id = 0
#                 agv_name = f"agv{agv_id}"
                
#                 pos = shared_data["positions"][key]      # 튜플 형태 (x, y)
#                 state = shared_data["statuses"].get(key, "unknown")
#                 direction = shared_data["directions"].get(key, "")
#                 logs = shared_data["logs"].get(key, [])
#                 realtime = logs[-1]["time"] if logs else datetime.now().isoformat()
                
#                 agv_data = {
#                     "agv_id": agv_id,
#                     "agv_name": agv_name,
#                     "state": state,
#                     "issue": "",  # 필요시 이 값도 업데이트
#                     "location_x": pos[0],
#                     "location_y": pos[1],
#                     "direction": direction,
#                     "realtime": realtime
#                 }
#                 agv_list.append(agv_data)
            
#             data = {
#                 "success": True,
#                 "agv_number": len(agv_list),
#                 "agvs": agv_list
#             }
#         yield f"data: {json.dumps(data)}\n\n"
#         time.sleep(1)

# @app.route("/api/agv-stream")
# def sse():
#     """
#     SSE 엔드포인트.
#     /api/agv-stream 주소로 접속하면 실시간 공유 데이터를 받아볼 수 있습니다.
#     """
#     return Response(event_stream(), content_type="text/event-stream")

# def agv1_update_callback(agv_id, position, state="moving"):
#     """
#     MQTT 스레드에서 호출되는 콜백 함수.
#     AGV1의 위치가 업데이트될 때 shared_data를 갱신합니다.
#     """
#     with data_lock:
#         shared_data["positions"][agv_id] = position
#         shared_data["statuses"][agv_id] = state
#         shared_data["logs"][agv_id].append({
#             "time": datetime.now().isoformat(),
#             "position": position,
#             "state": "moving",
#             "source": "mqtt"
#         })
#         # MQTT 코드에서 AGV1은 오른쪽(R)으로 이동한다고 가정
#         shared_data["directions"][agv_id] = "R"

# if __name__ == '__main__':
#     # 1. simulation.py: AGV2, AGV3, AGV4의 데이터를 단발성 업데이트합니다.
#     simulation_once()
    
#     # 2. mqtt_agv1.py: AGV1 MQTT 스레드를 실행합니다.
#     mqtt_thread = threading.Thread(
#         target=run_mqtt_agv1_forever,
#         args=(agv1_update_callback,),
#         daemon=True
#     )
#     mqtt_thread.start()

#     # 3. Flask 서버 실행 (HTTPS 사용 시 ssl_context 인자 추가)
#     app.run(debug=True, port=5000, threaded=True)




# mqtt 통신 데이터 서버


# app.py
from flask import Flask, Response
from flask_cors import CORS
import json
import time
import threading
from datetime import datetime

# [수정됨] simulation.py에서 공유 데이터, 락, simulation_run 함수를 import
from simulation import shared_data, data_lock, simulation_run
# [수정됨] agv_client.py 파일의 이름은 agv_client.py로 가정하고, run_mqtt_agv1_forever 함수를 import
from agv_client import run_mqtt_agv1_forever

app = Flask(__name__)
CORS(app)  # 모든 도메인에서 접근 허용

def event_stream():
    """
    SSE 스트림 함수.
    1초마다 shared_data에 기록된 모든 AGV의 상태 데이터를 JSON 형식으로 전송합니다.
    이때, AGV 1의 좌표는 MQTT 업데이트를 통해 갱신된 값이 반영됩니다.
    """
    while True:
        with data_lock:
            agv_list = []
            for key in shared_data["positions"]:
                try:
                    agv_id = int(key.split()[-1])
                except Exception:
                    agv_id = 0
                agv_name = f"agv{agv_id}"
                pos = shared_data["positions"][key]
                state = shared_data["statuses"].get(key, "unknown")
                direction = shared_data["directions"].get(key, "")
                logs = shared_data["logs"].get(key, [])
                realtime = logs[-1]["time"] if logs else datetime.now().isoformat()
                agv_data = {
                    "agv_id": agv_id,
                    "agv_name": agv_name,
                    "state": state,
                    "issue": "",
                    "location_x": pos[0],
                    "location_y": pos[1],
                    "direction": direction,
                    "realtime": realtime
                }
                agv_list.append(agv_data)
            data = {"success": True, "agv_number": len(agv_list), "agvs": agv_list}
        yield f"data: {json.dumps(data)}\n\n"
        time.sleep(1)

@app.route("/api/agv-stream")
def sse():
    return Response(event_stream(), content_type="text/event-stream")

def agv1_update_callback(agv_id, position, state="moving"):
    """
    MQTT 콜백 함수에서 호출되어, AGV 1의 상태를 shared_data에 업데이트합니다.
    이 함수는 오직 AGV 1의 좌표를 업데이트하므로, 시뮬레이터상의 AGV 1 데이터는 MQTT 데이터로 대체됩니다.
    [수정됨] AGV 1은 오른쪽("R")으로 이동한다고 가정
    """
    with data_lock:
        shared_data["positions"][agv_id] = position
        shared_data["statuses"][agv_id] = state
        shared_data["logs"][agv_id].append({
            "time": datetime.now().isoformat(),
            "position": position,
            "state": state,
            "source": "mqtt"
        })
        shared_data["directions"][agv_id] = "R"

if __name__ == '__main__':
    # [수정됨] simulation_run()를 별도 스레드로 실행하여 가상 AGV 2, 3, 4의 데이터를 지속적으로 업데이트
    simulation_thread = threading.Thread(target=simulation_run, daemon=True)
    simulation_thread.start()
    
    # [수정됨] agv_client.py의 MQTT 통신을 실행하여 AGV 1의 데이터를 업데이트 (실제 AGV1은 MQTT로 업데이트됨)
    mqtt_thread = threading.Thread(
        target=run_mqtt_agv1_forever,
        args=(agv1_update_callback,),
        daemon=True
    )
    mqtt_thread.start()
    
    # Flask 서버 실행: /api/agv-stream 엔드포인트로 실시간 JSON 데이터를 제공
    app.run(debug=True, port=5000, threaded=True)
