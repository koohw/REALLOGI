"""
app.py
- Flask 서버 (HTTPS)
- 시뮬레이션(AGV 2,3,4) 단발성 실행
- MQTT(AGV 1) 스레드
- shared_data를 안전하게 업데이트하기 위한 콜백
"""

# from flask import Flask, render_template, jsonify
# import threading, os
# from datetime import datetime

# # simulation.py에서 공유 데이터, 락, 시뮬레이션 함수를 가져옴
# from simulation import shared_data, data_lock, simulation_once

# # MQTT(AGV 1) 코드
# from mqtt_agv1 import run_mqtt_agv1_forever

# app = Flask(__name__)

# def agv1_update_callback(agv_id, position):
#     """
#     MQTT 스레드(AGV 1)에서 x+1 이동 시마다 호출.
#     여기서 shared_data에 "실제 시각" 로그를 기록하여
#     안전하게 AGV 1 상태 업데이트.
#     """
#     with data_lock:
#         # AGV1 상태 및 위치 갱신
#         shared_data["statuses"][agv_id] = "moving"
#         shared_data["positions"][agv_id] = position

#         # 로그 추가 (실제 시각)
#         shared_data["logs"][agv_id].append({
#             "time": datetime.now().isoformat(),
#             "position": position,
#             "state": "moving",
#             "source": "mqtt"
#         })

# @app.route('/')
# def index():
#     return render_template("index.html")

# @app.route('/api/logs')
# def get_logs():
#     # 락을 잡고 데이터를 읽으면 더 안전
#     # with data_lock:
#     #     return jsonify(shared_data["logs"])
#     # error 핸들링 추가
#     try:
#         with data_lock:
#             return jsonify(shared_data["logs"])
#     except Exception as e:
#         return jsonify({"error" : str(e)}), 500

# @app.route('/api/positions')
# def get_positions():
#     with data_lock:
#         return jsonify(shared_data["positions"])

# if __name__ == '__main__':
#     # 1) AGV 2,3,4 단발성 시뮬레이션
#     sim_thread = threading.Thread(target=simulation_once, daemon=True)
#     sim_thread.start()
#     # 2) AGV 1 (MQTT) 스레드
#     mqtt_thread = threading.Thread(
#         target=run_mqtt_agv1_forever,
#         args=(agv1_update_callback,),
#         daemon=True
#     )
#     mqtt_thread.start()

#     # 3) HTTPS로 Flask 서버 실행
#     ssl_cert_file = os.path.join(os.path.dirname(__file__), 'cert.pem')
#     ssl_key_file = os.path.join(os.path.dirname(__file__), 'key.pem')

#     app.run(
#         host='0.0.0.0',
#         port=5000,
#         ssl_context=(ssl_cert_file, ssl_key_file)
#     )






### sse

"""
app.py
- Flask 서버 (HTTPS)
- 시뮬레이션(AGV 2,3,4) 단발성 실행
- MQTT(AGV 1) 스레드
- shared_data를 안전하게 업데이트하기 위한 콜백
- SSE로 공유 데이터를 프론트엔드에 실시간 전송
"""

from flask import Flask, Response
from flask_cors import CORS
import json
import time
import random
from datetime import datetime

app = Flask(__name__)
CORS(app)  # 모든 도메인에서 요청 허용

# 맵 크기
GRID_ROWS = 10
GRID_COLS = 10

# 이동 가능 방향
DIRECTIONS = ["L", "R", "U", "D", "NONE"]

# AGV 초기 상태
agvs = [
    {
        "agv_id": 1,
        "agv_name": "agv1",
        "state": "fine",
        "issue": "",
        "location_x": 1,
        "location_y": 1,
        "direction": "L",  # 초기 방향
        "realtime": datetime.now().isoformat()
    },
    {
        "agv_id": 2,
        "agv_name": "agv2",
        "state": "fine",
        "issue": "",
        "location_x": 2,
        "location_y": 2,
        "direction": "R",
        "realtime": datetime.now().isoformat()
    },
    {
        "agv_id": 3,
        "agv_name": "agv3",
        "state": "fine",
        "issue": "",
        "location_x": 3,
        "location_y": 3,
        "direction": "U",
        "realtime": datetime.now().isoformat()
    },
    {
        "agv_id": 4,
        "agv_name": "agv4",
        "state": "fine",
        "issue": "",
        "location_x": 4,
        "location_y": 4,
        "direction": "D",
        "realtime": datetime.now().isoformat()
    },
]

def move_agv(agv):
    """
    AGV 하나의 위치와 방향을 업데이트합니다.
    (랜덤하게 방향 결정, 그에 따라 location_x, location_y 변경)
    """
    direction = random.choice(DIRECTIONS)
    x, y = agv["location_x"], agv["location_y"]

    if direction == "L" and x > 0:
        x -= 1
    elif direction == "R" and x < GRID_COLS - 1:
        x += 1
    elif direction == "U" and y > 0:
        y -= 1
    elif direction == "D" and y < GRID_ROWS - 1:
        y += 1

    agv["location_x"] = x
    agv["location_y"] = y
    agv["direction"] = direction
    agv["realtime"] = datetime.now().isoformat()  # 최신 시각 기록

def event_stream():
    """
    SSE 스트림 함수.
    매 1초마다 각 AGV 위치/방향을 업데이트한 뒤, 원하는 JSON 형식으로 yield합니다.
    """
    while True:
        # AGV 4대를 순회하며 위치/방향 업데이트
        for agv in agvs:
            move_agv(agv)

        # 최종 JSON 데이터
        data = {
            "success": True,
            "agv_number": len(agvs),
            "agv": agvs
        }

        # SSE 규약: "data: <JSON 문자열>\n\n"
        yield f"data: {json.dumps(data)}\n\n"
        time.sleep(1)  # 1초 간격으로 전송

@app.route("/api/agv-stream")
def sse():
    """
    SSE 엔드포인트. 
    /api/agv-stream 주소로 접속하면 event_stream() 제너레이터를 통해
    실시간 JSON 데이터를 받아볼 수 있습니다.
    """
    return Response(event_stream(), content_type="text/event-stream")

if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
