from flask import Flask, Response
from flask_cors import CORS  # CORS 모듈 임포트
import json
import time
import random

app = Flask(__name__)
CORS(app)  # 모든 도메인에서 오는 요청 허용
# 만약 특정 도메인만 허용하려면: CORS(app, origins=["http://localhost:3000"])

# 맵 크기
GRID_ROWS = 10
GRID_COLS = 10

# 이동 가능 방향
DIRECTIONS = ["L", "R", "U", "D", "NONE"]

# AGV 초기 상태 (SSE 서버에서는 단순 시뮬레이션용 데이터 사용)
agvs = [
    {"agv_id": 1, "agv_name": "AGV1", "state": "fine", "issue": "", "location_x": 1, "location_y": 1, "direction": "R"},
    {"agv_id": 2, "agv_name": "AGV2", "state": "fine", "issue": "", "location_x": 3, "location_y": 3, "direction": "U"},
    {"agv_id": 3, "agv_name": "AGV3", "state": "fine", "issue": "", "location_x": 5, "location_y": 5, "direction": "L"},
    {"agv_id": 4, "agv_name": "AGV4", "state": "fine", "issue": "", "location_x": 7, "location_y": 7, "direction": "D"},
]

def move_agv(agv):
    # 랜덤하게 방향 선택 후, 벽을 넘지 않도록 위치 업데이트
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

def event_stream():
    while True:
        for agv in agvs:
            move_agv(agv)  # 각 AGV의 위치를 업데이트
        data = {"success": True, "agv_number": len(agvs), "agv": agvs}
        yield f"data: {json.dumps(data)}\n\n"
        time.sleep(1)  # 1초마다 전송

@app.route("/api/agv-stream")
def sse():
    return Response(event_stream(), content_type="text/event-stream")

if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
