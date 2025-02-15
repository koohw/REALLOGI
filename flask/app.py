# from flask import Flask, Response
# from flask_cors import CORS
# import json
# import time
# import threading
# from datetime import datetime

# # simulation.py에서 공유 데이터, 락, simulation_main 함수를 import합니다.
# from simulation import shared_data, data_lock, simulation_main
# # agv_client.py에서 MQTT 실행 함수를 import합니다.
# # from agv_client import run_server_mqtt

# app = Flask(__name__)
# CORS(app)

# def event_stream():
#     """
#     SSE 스트림 함수.
#     매 1초마다 shared_data에 저장된 모든 AGV의 상태 데이터를 JSON 형식으로 전송합니다.
#     데이터가 없으면 빈 문자열("")을 출력합니다.
#     """
#     default_keys = ["AGV 1", "AGV 2", "AGV 3", "AGV 4"]
#     while True:
#         with data_lock:
#             agv_list = []
#             for key in default_keys:
#                 pos = shared_data["positions"].get(key)
#                 state = shared_data.get("statuses", {}).get(key, "")
#                 direction = shared_data.get("directions", {}).get(key, "")
#                 logs_list = shared_data.get("logs", {}).get(key, [])
#                 realtime = (logs_list[-1]["time"]
#                             if logs_list and isinstance(logs_list[-1], dict) and "time" in logs_list[-1]
#                             else "")
#                 try:
#                     agv_id = int(key.split()[-1])
#                 except Exception:
#                     agv_id = 0
#                 agv_name = f"agv{agv_id}"
#                 if not pos:
#                     loc_x, loc_y = "", ""
#                 else:
#                     loc_x, loc_y = pos
#                 agv_data = {
#                     "agv_id": agv_id,
#                     "agv_name": agv_name,
#                     "state": state,
#                     "issue": "",
#                     "location_x": loc_x,
#                     "location_y": loc_y,
#                     "direction": direction,
#                     "realtime": realtime
#                 }
#                 agv_list.append(agv_data)
#             order_success = shared_data.get("order_completed", {})
#             data = {"success": True, 
#                     "agv_number": len(agv_list), 
#                     "agvs": agv_list,
#                     "order_success": order_success}
#         yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
#         time.sleep(1)

# @app.route("/api/agv-stream")
# def sse():
#     return Response(event_stream(), content_type="text/event-stream")

# def agv1_update_callback(agv_id, position, state="moving"):
#     with data_lock:
#         key = f"AGV {agv_id}"
#         shared_data["positions"][key] = position
#         shared_data.setdefault("statuses", {})[key] = state
#         shared_data.setdefault("logs", {}).setdefault(key, []).append({
#             "time": datetime.now().isoformat(),
#             "position": position,
#             "state": state,
#             "source": "mqtt"
#         })
#         shared_data.setdefault("directions", {})[key] = "R"

# def start_background_threads():
#     sim_thread = threading.Thread(target=simulation_main, daemon=True)
#     sim_thread.start()
    
#     mqtt_thread = threading.Thread(
#         target=run_server_mqtt,
#         args=(agv1_update_callback,),
#         daemon=True
#     )
#     mqtt_thread.start()

# if __name__ == '__main__':
#     start_background_threads()
#     app.run(debug=False, use_reloader=False, port=5000)


# app.py

from flask import Flask, Response
from flask_cors import CORS
import json
import time
import threading
from datetime import datetime

# simulation.py에서 공유 데이터, 락, simulation_main 함수를 import
# simulation.py 내부에 "AGV1 MQTT 통신 + AGV2~4 시뮬레이션"이 구현되어 있다고 가정
from simulation import shared_data, data_lock, simulation_main

app = Flask(__name__)
CORS(app)

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

            # history는 최신 데이터로 덮어쓰도록 함
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
                    "agv_id": agv_id,
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



@app.route("/api/agv-stream")
def sse():
    return Response(event_stream(), content_type="text/event-stream")

def start_background_threads():
    """
    백그라운드 쓰레드:
    1) 시뮬레이션 메인 (simulation_main) 실행
    """
    sim_thread = threading.Thread(target=simulation_main, daemon=True)
    sim_thread.start()

if __name__ == '__main__':
    start_background_threads()
    app.run(debug=False, use_reloader=False, port=5000)