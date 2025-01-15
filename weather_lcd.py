import time
import requests
from datetime import datetime
import xmltodict
from RPLCD.i2c import CharLCD

# I2C 주소와 LCD 설정
I2C_ADDR = 0x27
lcd = CharLCD('PCF8574', I2C_ADDR, port=1)

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
params = {'serviceKey': keys,
          'pageNo': '1',
          'numOfRows': '1000',
          'dataType': 'XML',
          'base_date': get_current_date_string(),
          'base_time': get_current_hour_string(),
          'nx': '55',
          'ny': '127'}

def forecast():
    res = requests.get(url, params=params)
    xml_data = res.text
    dict_data = xmltodict.parse(xml_data)

    weather_data = dict()
    try:
        for item in dict_data['response']['body']['items']['item']:
            if item['category'] == 'T1H':
                weather_data['tmp'] = item['fcstValue']
            if item['category'] == 'REH':
                weather_data['hum'] = item['fcstValue']
            if item['category'] == 'SKY':
                weather_data['sky'] = item['fcstValue']
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

# LCD에 날씨 출력 함수
def display_weather_on_lcd():
    weather_info = proc_weather()

    # 화면 지우기
    lcd.clear()

    # 첫 번째 줄에 날씨 출력
    lcd.write_string(weather_info[:16])  # 최대 16자까지 출력

    # 두 번째 줄에 나머지 정보 출력
    lcd.cursor_pos = (1, 0)
    lcd.write_string(weather_info[16:])

# 주기적으로 날씨 정보 업데이트 및 출력
while True:
    display_weather_on_lcd()
    time.sleep(600)  # 10분마다 날씨 정보 업데이트
