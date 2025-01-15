from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# API 기본 URL 및 키 (여기에 본인의 API 키를 입력하세요)
API_KEY = "1aGTq5x4%2BDfUaWGvfpycqPQtW1HzEAAp4iG22BCOu9rSkEjtNHmzSKPO2wBpBYrDbx%2BR3J%2B0%2BUut5%2BFrsMstpQ%3D%3D"
BASE_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/weather', methods=['GET'])
def weather():
    # 지역 및 날짜 데이터
    region = request.args.get('region', '서울')
    base_date = request.args.get('base_date', '20250115')  # 예: YYYYMMDD 형식
    base_time = "0500"  # 기상청 발표 시간

    # API 요청 파라미터
    params = {
        "serviceKey": API_KEY,
        "numOfRows": 10,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": 60,  # 예제 위치 (서울)
        "ny": 127
    }

    # API 호출
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        weather_data = response.json()
        return render_template("weather.html", data=weather_data)
    else:
        return f"Error: {response.status_code}"

if __name__ == '__main__':
    app.run(debug=True)
