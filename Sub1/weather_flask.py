from flask import Flask, render_template_string
import requests
from datetime import datetime
import xmltodict

app = Flask(__name__)

# 날씨 관련 함수들

def get_current_date_string():
    current_date = datetime.now().date()
    return current_date.strftime("%Y%m%d")

def get_current_hour_string():
    now = datetime.now()
    if now.minute < 45:
        if now.hour == 0:
            base_time = "2330"
        else:
            pre_hour = now.hour - 1
            if pre_hour < 10:
                base_time = "0" + str(pre_hour) + "30"
            else:
                base_time = str(pre_hour) + "30"
    else:
        if now.hour < 10:
            base_time = "0" + str(now.hour) + "30"
        else:
            base_time = str(now.hour) + "30"
    
    return base_time

keys = 'OL50yS2bAuUcgyuwzS5FO0KTzXxzVmiSCbkZYq4ZvpSU93YQd2uixQCfihbvy7+maJVI8b5ka2S8KQL8wrWUng=='
url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst'

params = {
    'serviceKey': keys,
    'pageNo': '1',
    'numOfRows': '1000',
    'dataType': 'XML',
    'base_date': get_current_date_string(),
    'base_time': get_current_hour_string(),
    'nx': '55',  # 서울의 X 좌표
    'ny': '127'  # 서울의 Y 좌표
}

def forecast():
    # 웹 API 호출
    res = requests.get(url, params=params)
    xml_data = res.text
    dict_data = xmltodict.parse(xml_data)

    weather_data = dict()
    try:
        for item in dict_data['response']['body']['items']['item']:
            # 기온
            if item['category'] == 'T1H':
                weather_data['tmp'] = item['fcstValue']
            # 습도
            if item['category'] == 'REH':
                weather_data['hum'] = item['fcstValue']
            # 하늘상태
            if item['category'] == 'SKY':
                weather_data['sky'] = item['fcstValue']
            # 강수형태
            if item['category'] == 'PTY':
                weather_data['sky2'] = item['fcstValue']
    except KeyError as e:
        print(f"Error: Key not found in response: {e}")
        return {}

    return weather_data

def proc_weather():
    dict_sky = forecast()

    str_sky = "서울 "
    if dict_sky['sky'] != None or dict_sky['sky2'] != None:
        str_sky = str_sky + "날씨 : "
        if dict_sky['sky2'] == '0':
            if dict_sky['sky'] == '1':
                str_sky = str_sky + "맑음"
            elif dict_sky['sky'] == '3':
                str_sky = str_sky + "구름많음"
            elif dict_sky['sky'] == '4':
                str_sky = str_sky + "흐림"
        elif dict_sky['sky2'] == '1':
            str_sky = str_sky + "비"
        elif dict_sky['sky2'] == '2':
            str_sky = str_sky + "비와 눈"
        elif dict_sky['sky2'] == '3':
            str_sky = str_sky + "눈"
        elif dict_sky['sky2'] == '5':
            str_sky = str_sky + "빗방울이 떨어짐"
        elif dict_sky['sky2'] == '6':
            str_sky = str_sky + "빗방울과 눈이 날림"
        elif dict_sky['sky2'] == '7':
            str_sky = str_sky + "눈이 날림"
        str_sky = str_sky + "\n"
    if dict_sky['tmp'] != None:
        str_sky = str_sky + "온도 : " + dict_sky['tmp'] + 'ºC \n'
    if dict_sky['hum'] != None:
        str_sky = str_sky + "습도 : " + dict_sky['hum'] + '%'

    return str_sky


# Flask 라우트 정의
@app.route('/')
def home():
    weather_info = proc_weather()  # 날씨 정보 가져오기
    return render_template_string("""
        <html>
        <head>
            <title>서울 날씨</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; }
                .weather { margin-top: 50px; font-size: 20px; }
            </style>
        </head>
        <body>
            <h1>현재 서울 날씨</h1>
            <div class="weather">{{ weather_info }}</div>
        </body>
        </html>
    """, weather_info=weather_info)

if __name__ == '__main__':
    app.run(debug=True)
