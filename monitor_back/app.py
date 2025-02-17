from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import json
import time
import threading
from datetime import datetime

from simulation import shared_data, data_lock, simulation_main, mqtt_client, TOPIC_COMMAND_TO_DEVICE


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

def compute_start_position(agv_key):
    """
    AGV의 시작 위치를 계산합니다.
    시뮬레이션에서는 시작 위치가 (ROWS-1, col)이며,
    예: AGV 1: (8, 0), AGV 2: (8, 2), AGV 3: (8, 4), AGV 4: (8, 6)
    """
    try:
        index = int(agv_key.split()[1]) - 1
    except Exception:
        index = 0
    col = (index * 2) % 7  # COLS가 7인 경우
    return (8, col)

def send_stop_command_to_agv(agv_key):
    """
    지정된 AGV(주로 AGV1)에 대해 MQTT로 STOP 명령을 전송합니다.
    """
    payload = {"command": "STOP"}
    result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
    if result[0] == 0:
        app.logger.info("[SIM] %s STOP 명령 전송 성공: %s", agv_key, payload)
    else:
        app.logger.error("[SIM] %s STOP 명령 전송 실패: %s", agv_key, payload)

@app.route("/api/agv/stop", methods=["POST"])
def stop_agv():
    """
    AGV 정지 명령:
      - 요청 데이터: { "agvIds": ["AGV001", "AGV002", ...] }
      - 해당 AGV의 상태를 "STOP"으로 변경하고,
        만약 AGV1(실제 하드웨어)이 포함되어 있으면 MQTT로 STOP 명령을 전송합니다.
    """
    data = request.get_json()
    agvIds = data.get("agvIds", [])
    results = []
    with data_lock:
        if not agvIds or any(x.upper() == "ALL" for x in agvIds):
            for agv_key in shared_data["positions"]:
                shared_data["statuses"][agv_key] = "STOP"
                results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "success"})
                if agv_key == "AGV 1":
                    send_stop_command_to_agv(agv_key)
        else:
            for agv_id in agvIds:
                key = convert_agv_id(agv_id)
                if key in shared_data["positions"]:
                    shared_data["statuses"][key] = "STOP"
                    results.append({"agv_id": agv_id, "status": "success"})
                    if key == "AGV 1":
                        send_stop_command_to_agv(key)
                else:
                    results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})
    return jsonify({"success": True, "message": "정지 명령이 전송되었습니다.", "results": results})

@app.route("/api/agv/resume", methods=["POST"])
def resume_agv():
    """
    AGV 재시작(RESUME) 명령:
      - 요청 데이터: { "agvIds": ["AGV001", "AGV002", ...] }
      - STOP 상태인 AGV에 대해 상태를 "RUNNING"으로 변경하여 경로 탐색을 재개합니다.
      - 만약 AGV1(실제 하드웨어)이 포함되어 있다면 MQTT로 RESUME 명령(예: "RESUME")을 전송합니다.
    """
    data = request.get_json()
    agvIds = data.get("agvIds", [])
    results = []
    with data_lock:
        if not agvIds or any(x.upper() == "ALL" for x in agvIds):
            for agv_key in shared_data["positions"]:
                if shared_data["statuses"][agv_key] == "STOP":
                    shared_data["statuses"][agv_key] = "RUNNING"
                    results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "success"})
                    if agv_key == "AGV 1":
                        # 예시로 RESUME 명령 전송 (필요에 따라 payload 수정)
                        payload = {"command": "RESUME"}
                        result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
                        if result[0] == 0:
                            app.logger.info("[SIM] %s RESUME 명령 전송 성공: %s", agv_key, payload)
                        else:
                            app.logger.error("[SIM] %s RESUME 명령 전송 실패: %s", agv_key, payload)
                else:
                    results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "error",
                                    "error": f"{agv_key}가 STOP 상태가 아닙니다."})
        else:
            for agv_id in agvIds:
                key = convert_agv_id(agv_id)
                if key in shared_data["positions"]:
                    if shared_data["statuses"][key] == "STOP":
                        shared_data["statuses"][key] = "RUNNING"
                        results.append({"agv_id": agv_id, "status": "success"})
                        if key == "AGV 1":
                            payload = {"command": "RESUME"}
                            result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
                            if result[0] == 0:
                                app.logger.info("[SIM] %s RESUME 명령 전송 성공: %s", key, payload)
                            else:
                                app.logger.error("[SIM] %s RESUME 명령 전송 실패: %s", key, payload)
                    else:
                        results.append({"agv_id": agv_id, "status": "error", "error": "AGV가 정지 상태가 아닙니다."})
                else:
                    results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})
    return jsonify({"success": True, "message": "재시작(RESUME) 명령이 전송되었습니다.", "results": results})

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
                    except Exception:
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

def start_background_threads():
    sim_thread = threading.Thread(target=simulation_main, daemon=True)
    sim_thread.start()

if __name__ == '__main__':
    start_background_threads()
    app.run(debug=False, use_reloader=False, port=5000)








# from flask import Flask, Response, request, jsonify
# from flask_cors import CORS
# import json
# import time
# import threading
# from datetime import datetime

# from simulation import shared_data, data_lock, simulation_main

# app = Flask(__name__)
# CORS(app)

# def convert_agv_id(agv_str):
#     """
#     "AGV001" 형태 -> "AGV 1" 으로 변환
#     """
#     if agv_str.upper() == "ALL":
#         return "ALL"
#     try:
#         num = int(agv_str.replace("AGV", ""))
#         return f"AGV {num}"
#     except Exception:
#         return agv_str

# def compute_start_position(agv_key):
#     """
#     AGV의 시작 위치를 계산합니다.
#     시뮬레이션에서는 시작 위치가 (ROWS-1, col)이며,
#     예를 들어, AGV 1: (8, 0), AGV 2: (8, 2), AGV 3: (8, 4), AGV 4: (8, 6)
#     """
#     try:
#         index = int(agv_key.split()[1]) - 1
#     except Exception:
#         index = 0
#     col = (index * 2) % 7  # COLS가 7인 경우
#     return (8, col)

# @app.route("/api/agv-stream")
# def sse():
#     def event_stream():
#         default_keys = ["AGV 1", "AGV 2", "AGV 3", "AGV 4"]
#         while True:
#             with data_lock:
#                 overall_eff_sum = 0
#                 count = 0
#                 for key in default_keys:
#                     if shared_data["order_completed"][key] > 0:
#                         overall_eff_sum += shared_data["efficiency"].get(key, 0)
#                         count += 1
#                 overall_efficiency = overall_eff_sum / count if count else 0

#                 # 최신 효율만 반영하는 로직
#                 shared_data["overall_efficiency_history"] = [(datetime.now().isoformat(), overall_efficiency)]
#                 agv_list = []
#                 for key in default_keys:
#                     pos = shared_data["positions"].get(key)
#                     state = shared_data["statuses"].get(key, "")
#                     direction = shared_data["directions"].get(key, "")
#                     logs_list = shared_data["logs"].get(key, [])
#                     realtime = logs_list[-1].get("time", "") if logs_list and isinstance(logs_list[-1], dict) else ""
#                     try:
#                         agv_id = int(key.split()[-1])
#                     except Exception:
#                         agv_id = 0
#                     agv_name = f"agv{agv_id}"
#                     loc_x = pos[0] if pos else ""
#                     loc_y = pos[1] if pos else ""
#                     agv_data = {
#                         "agv_id": key.replace(" ", "0"),
#                         "agv_name": agv_name,
#                         "state": state,
#                         "issue": "",
#                         "location_x": loc_x,
#                         "location_y": loc_y,
#                         "direction": direction,
#                         "realtime": realtime,
#                         "efficiency": shared_data["efficiency"].get(key, 0)
#                     }
#                     agv_list.append(agv_data)

#                 data = {
#                     "success": True,
#                     "agv_number": len(agv_list),
#                     "agvs": agv_list,
#                     "order_success": shared_data.get("order_completed", {}),
#                     "overall_efficiency": overall_efficiency,
#                     "overall_efficiency_history": shared_data["overall_efficiency_history"]
#                 }
#             yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
#             time.sleep(1)
#     return Response(event_stream(), content_type="text/event-stream")

# @app.route("/api/agv/stop", methods=["POST"])
# def stop_agv():
#     """
#     AGV 정지 명령:
#       - 요청 데이터: { "agvIds": ["AGV001", "AGV002", ...] }
#       - 해당 AGV의 상태를 "STOP"으로 변경하여 즉시 정지하도록 합니다.
#     """
#     data = request.get_json()
#     agvIds = data.get("agvIds", [])
#     results = []
#     with data_lock:
#         if not agvIds or any(x.upper() == "ALL" for x in agvIds):
#             for agv_key in shared_data["positions"]:
#                 shared_data["statuses"][agv_key] = "STOP"
#                 results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "success"})
#         else:
#             for agv_id in agvIds:
#                 key = convert_agv_id(agv_id)
#                 if key == "ALL":
#                     continue
#                 if key in shared_data["positions"]:
#                     shared_data["statuses"][key] = "STOP"
#                     results.append({"agv_id": agv_id, "status": "success"})
#                 else:
#                     results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})
#     return jsonify({"success": True, "message": "정지 명령이 전송되었습니다.", "results": results})

# @app.route("/api/agv/restart", methods=["POST"])
# def restart_agv():
#     """
#     AGV 재가동 명령:
#       - 요청 데이터: { "agvIds": ["AGV002", ...] }
#       - STOP 상태인 AGV에 대해 상태를 "RUNNING"으로 변경하면,
#         해당 AGV는 현재 위치에서 다시 경로 탐색을 시작합니다.
#     """
#     data = request.get_json()
#     agvIds = data.get("agvIds", [])
#     results = []
#     with data_lock:
#         if not agvIds or any(x.upper() == "ALL" for x in agvIds):
#             for agv_key in shared_data["positions"]:
#                 if shared_data["statuses"][agv_key] == "STOP":
#                     shared_data["statuses"][agv_key] = "RUNNING"
#                     results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "success"})
#                 else:
#                     results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "error",
#                                     "error": f"{agv_key}가 STOP 상태가 아닙니다."})
#         else:
#             for agv_id in agvIds:
#                 key = convert_agv_id(agv_id)
#                 if key in shared_data["positions"]:
#                     if shared_data["statuses"][key] == "STOP":
#                         shared_data["statuses"][key] = "RUNNING"
#                         results.append({"agv_id": agv_id, "status": "success"})
#                     else:
#                         results.append({"agv_id": agv_id, "status": "error", "error": "AGV가 정지 상태가 아닙니다."})
#                 else:
#                     results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})
#     return jsonify({"success": True, "message": "재가동 명령이 전송되었습니다.", "results": results})

# @app.route("/api/agv/return", methods=["POST"])
# def return_agv():
#     """
#     AGV 복귀 명령:
#       - 요청 데이터: { "agvIds": ["AGV001", ...] }
#       - 해당 AGV의 목표(target)를 처음 시작했던 위치로 재설정하고,
#         상태를 "RUNNING"으로 전환하여 복귀하도록 합니다.
#     """
#     data = request.get_json()
#     agvIds = data.get("agvIds", [])
#     results = []
#     with data_lock:
#         if not agvIds or any(x.upper() == "ALL" for x in agvIds):
#             for agv_key in shared_data["positions"]:
#                 return_location = compute_start_position(agv_key)
#                 shared_data["target"][agv_key] = return_location
#                 shared_data["statuses"][agv_key] = "RUNNING"
#                 results.append({
#                     "agv_id": agv_key.replace("AGV ", "AGV"),
#                     "status": "success",
#                     "return_location": {"x": return_location[0], "y": return_location[1]}
#                 })
#         else:
#             for agv_id in agvIds:
#                 key = convert_agv_id(agv_id)
#                 if key in shared_data["positions"]:
#                     return_location = compute_start_position(key)
#                     shared_data["target"][key] = return_location
#                     shared_data["statuses"][key] = "RUNNING"
#                     results.append({
#                         "agv_id": agv_id,
#                         "status": "success",
#                         "return_location": {"x": return_location[0], "y": return_location[1]}
#                     })
#                 else:
#                     results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})
#     return jsonify({"success": True, "message": "복귀 명령이 전송되었습니다.", "results": results})

# def start_background_threads():
#     sim_thread = threading.Thread(target=simulation_main, daemon=True)
#     sim_thread.start()

# if __name__ == '__main__':
#     start_background_threads()
#     app.run(debug=False, use_reloader=False, port=5000)
