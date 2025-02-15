# # app.py

# from flask import Flask, Response
# from flask_cors import CORS
# import json
# import time
# import threading
# from datetime import datetime

# # simulation.py에서 공유 데이터, 락, simulation_main 함수를 import
# # simulation.py 내부에 "AGV1 MQTT 통신 + AGV2~4 시뮬레이션"이 구현되어 있다고 가정
# from simulation import shared_data, data_lock, simulation_main

# app = Flask(__name__)
# CORS(app)

# def event_stream():
#     default_keys = ["AGV 1", "AGV 2", "AGV 3", "AGV 4"]
#     while True:
#         with data_lock:
#             overall_eff_sum = 0
#             count = 0
#             for key in default_keys:
#                 if shared_data["order_completed"][key] > 0:
#                     overall_eff_sum += shared_data["efficiency"].get(key, 0)
#                     count += 1
#             overall_efficiency = overall_eff_sum / count if count else 0

#             # history는 최신 데이터로 덮어쓰도록 함
#             shared_data["overall_efficiency_history"] = [(datetime.now().isoformat(), overall_efficiency)]

#             agv_list = []
#             for key in default_keys:
#                 pos = shared_data["positions"].get(key)
#                 state = shared_data["statuses"].get(key, "")
#                 direction = shared_data["directions"].get(key, "")
#                 logs_list = shared_data["logs"].get(key, [])
#                 realtime = logs_list[-1].get("time", "") if logs_list and isinstance(logs_list[-1], dict) else ""
#                 try:
#                     agv_id = int(key.split()[-1])
#                 except:
#                     agv_id = 0
#                 agv_name = f"agv{agv_id}"
#                 loc_x = pos[0] if pos else ""
#                 loc_y = pos[1] if pos else ""
#                 agv_data = {
#                     "agv_id": agv_id,
#                     "agv_name": agv_name,
#                     "state": state,
#                     "issue": "",
#                     "location_x": loc_x,
#                     "location_y": loc_y,
#                     "direction": direction,
#                     "realtime": realtime,
#                     "efficiency": shared_data["efficiency"].get(key, 0)
#                 }
#                 agv_list.append(agv_data)

#             data = {
#                 "success": True,
#                 "agv_number": len(agv_list),
#                 "agvs": agv_list,
#                 "order_success": shared_data.get("order_completed", {}),
#                 "overall_efficiency": overall_efficiency,
#                 "overall_efficiency_history": shared_data["overall_efficiency_history"]
#             }
#         yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
#         time.sleep(1)



# @app.route("/api/agv-stream")
# def sse():
#     return Response(event_stream(), content_type="text/event-stream")

# def start_background_threads():
#     """
#     백그라운드 쓰레드:
#     1) 시뮬레이션 메인 (simulation_main) 실행
#     """
#     sim_thread = threading.Thread(target=simulation_main, daemon=True)
#     sim_thread.start()

# if __name__ == '__main__':
#     start_background_threads()
#     app.run(debug=False, use_reloader=False, port=5000)








# app.py

from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import json
import time
import threading
from datetime import datetime

from simulation import shared_data, data_lock, simulation_main

app = Flask(__name__)
CORS(app)

def convert_agv_id(agv_str):
    """
    "AGV001" 형태 -> "AGV 1" 으로 변환
    """
    if agv_str.upper() == "ALL":
        return "ALL"
    try:
        num = int(agv_str.replace("AGV", ""))
        return f"AGV {num}"
    except Exception:
        return agv_str

@app.route("/api/agv-stream")
def sse():
    def event_stream():
        default_keys = ["AGV 1", "AGV 2", "AGV 3", "AGV 4"]
        while True:
            with data_lock:
                overall_eff_sum = 0
                count = 0
                for key in default_keys:
                    if shared_data["order_completed"][key] > 0:
                        overall_eff_sum += shared_data["efficiency"].get(key, 0)
                        count += 1
                overall_efficiency = overall_eff_sum / count if count else 0

                # 최신 효율만 반영하는 로직
                shared_data["overall_efficiency_history"] = [(datetime.now().isoformat(), overall_efficiency)]
                agv_list = []
                for key in default_keys:
                    pos = shared_data["positions"].get(key)
                    state = shared_data["statuses"].get(key, "")
                    direction = shared_data["directions"].get(key, "")
                    logs_list = shared_data["logs"].get(key, [])
                    realtime = logs_list[-1].get("time", "") if logs_list and isinstance(logs_list[-1], dict) else ""
                    try:
                        agv_id = int(key.split()[-1])
                    except:
                        agv_id = 0
                    agv_name = f"agv{agv_id}"
                    loc_x = pos[0] if pos else ""
                    loc_y = pos[1] if pos else ""
                    agv_data = {
                        "agv_id": key.replace(" ", "0"),
                        "agv_name": agv_name,
                        "state": state,
                        "issue": "",
                        "location_x": loc_x,
                        "location_y": loc_y,
                        "direction": direction,
                        "realtime": realtime,
                        "efficiency": shared_data["efficiency"].get(key, 0)
                    }
                    agv_list.append(agv_data)

                data = {
                    "success": True,
                    "agv_number": len(agv_list),
                    "agvs": agv_list,
                    "order_success": shared_data.get("order_completed", {}),
                    "overall_efficiency": overall_efficiency,
                    "overall_efficiency_history": shared_data["overall_efficiency_history"]
                }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            time.sleep(1)
    return Response(event_stream(), content_type="text/event-stream")


@app.route("/api/agv/stop", methods=["POST"])
def stop_agv():
    """
    stop 명령:
      1) agvIds를 받음 (["AGV001", "AGV002"] ...)
      2) 만약 ALL 이나 빈 리스트면 전체 정지
    """
    data = request.get_json()
    agvIds = data.get("agv_id", [])  # e.g. ["AGV001", "ALL"]

    results = []
    with data_lock:
        # 만약 agvIds가 비었거나 "ALL"이 포함되어 있으면 전체 AGV 정지
        if not agvIds or any(x.upper() == "ALL" for x in agvIds):
            # 전체 AGV (AGV 1..4) 일괄 정지
            for agv_key in shared_data["positions"]:
                shared_data["statuses"][agv_key] = "STOP"
                results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "success"})
        else:
            # 특정 AGV만
            for agv_id in agvIds:
                key = convert_agv_id(agv_id)
                if key == "ALL":
                    # 이미 위에서 처리
                    continue
                if key in shared_data["positions"]:
                    shared_data["statuses"][key] = "STOP"
                    results.append({"agv_id": agv_id, "status": "success"})
                else:
                    results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})

    return jsonify({"success": True, "message": "정지 명령이 전송되었습니다.", "results": results})


@app.route("/api/agv/return", methods=["POST"])
def return_agv():
    """
    return 명령:
      - agvIds에 대해 해당 AGV들을 (0,0) 위치로 목표 재설정
      - agvIds가 비었거나 ALL이면 전체 AGV 복귀
    """
    data = request.get_json()
    agvIds = data.get("agv_id", [])
    results = []
    return_location = (0, 0)

    with data_lock:
        if not agvIds or any(x.upper() == "ALL" for x in agvIds):
            # 전체 복귀
            for agv_key in shared_data["positions"]:
                shared_data["target"][agv_key] = return_location
                # 정지 상태였다면 RUNNING으로 바꿔 주행 재개
                shared_data["statuses"][agv_key] = "RUNNING"
                results.append({
                    "agv_id": agv_key.replace("AGV ", "AGV"),
                    "status": "success",
                    "return_location": {"x": return_location[0], "y": return_location[1]}
                })
        else:
            # 일부 AGV
            for agv_id in agvIds:
                key = convert_agv_id(agv_id)
                if key in shared_data["positions"]:
                    shared_data["target"][key] = return_location
                    # 정지였다면 RUNNING
                    shared_data["statuses"][key] = "RUNNING"
                    results.append({
                        "agv_id": agv_id,
                        "status": "success",
                        "return_location": {"x": return_location[0], "y": return_location[1]}
                    })
                else:
                    results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})

    return jsonify({"success": True, "message": "복귀 명령이 전송되었습니다.", "results": results})


@app.route("/api/agv/restart", methods=["POST"])
def restart_agv():
    """
    restart 명령:
      - agvIds가 비었거나 ALL이면 전체 재가동
      - 특정 agv만
      - STOP 상태가 아니라면 에러
    """
    data = request.get_json()
    agvIds = data.get("agv_id", [])
    results = []

    with data_lock:
        if not agvIds or any(x.upper() == "ALL" for x in agvIds):
            # 전체 재가동
            for agv_key in shared_data["positions"]:
                if shared_data["statuses"][agv_key] == "STOP":
                    shared_data["statuses"][agv_key] = "RUNNING"
                    results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "success"})
                else:
                    results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "error",
                                    "error": f"{agv_key}가 STOP 상태가 아닙니다."})
        else:
            # 일부 AGV
            for agv_id in agvIds:
                key = convert_agv_id(agv_id)
                if key in shared_data["positions"]:
                    if shared_data["statuses"][key] == "STOP":
                        shared_data["statuses"][key] = "RUNNING"
                        results.append({"agv_id": agv_id, "status": "success"})
                    else:
                        results.append({"agv_id": agv_id, "status": "error", "error": "AGV가 정지 상태가 아닙니다."})
                else:
                    results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})

    return jsonify({"success": True, "message": "재가동 명령이 전송되었습니다.", "results": results})


def start_background_threads():
    sim_thread = threading.Thread(target=simulation_main, daemon=True)
    sim_thread.start()

if __name__ == '__main__':
    start_background_threads()
    app.run(debug=False, use_reloader=False, port=5000)
