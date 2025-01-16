import requests
from datetime import datetime
import xmltodict




def get_current_date_string():
    current_date = datetime.now().date()
    return current_date.strftime("%Y%m%d")

def get_current_hour_string():
    now = datetime.now()
    if now.minute<45: # base_time와 base_date 구하는 함수
        if now.hour==0:
            base_time = "2330"
        else:
            pre_hour = now.hour-1
            if pre_hour<10:
                base_time = "0" + str(pre_hour) + "30"
            else:
                base_time = str(pre_hour) + "30"
    else:
        if now.hour < 10:
            base_time = "0" + str(now.hour) + "30"
        else:
            base_time = str(now.hour) + "30"

    return base_time

city = {'서울': {'x':'60', 'y':'127'}, '대전': {'x':'67', 'y':'100'}, '광주': {'x':'58', 'y':'74'}, 
    '구미': {'x':'84', 'y':'96'}, '부산': {'x':'98', 'y':'76'}}

keys = 'udHuJKXIgDobNcIjiPJ7PBRgRABi92wsmAHpwVc7hhQJzZg%2FUIkMyJpzjc0xnGWNe8vEIXAk%2FTQfLcmQ0wfT1g%3D%3D'
# url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst'
params ={'serviceKey' : keys, 
            'pageNo' : '1', 
            'numOfRows' : '1000', 
            'dataType' : 'XML', 
            'base_date' : get_current_date_string(), 
            'base_time' : get_current_hour_string(), 
            'nx' : '55', 
            'ny' : '127' }


    

def forecast():
    # 값 요청 (웹 브라우저 서버에서 요청 - url주소와 파라미터)
    url = f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst?serviceKey={params['serviceKey']}&pageNo={params['pageNo']}&numOfRows={params['numOfRows']}&dataType={params['dataType']}&base_date={params['base_date']}&base_time={params['base_time']}&nx={params['nx']}&ny={params['ny']}"
    # res = requests.get(url, params = params)
    res = requests.get(url)
    #XML -> 딕셔너리
    xml_data = res.text
    dict_data = xmltodict.parse(xml_data)
    #값 가져오기
    weather_data = dict()
    # print(dict_data['response']['body']['items']['item']['nx'], dict_data['response']['body']['items']['item']['ny'])
    for item in dict_data['response']['body']['items']['item']:
        # 기온
        if item['category'] == 'T1H':
            weather_data['tmp'] = item['fcstValue']
        # 습도
        if item['category'] == 'REH':
            weather_data['hum'] = item['fcstValue']
        # 하늘상태: 맑음(1) 구름많은(3) 흐림(4)
        if item['category'] == 'SKY':
            weather_data['sky'] = item['fcstValue']
        # 강수형태: 없음(0), 비(1), 비/눈(2), 눈(3), 빗방울(5), 빗방울눈날림(6), 눈날림(7)
        if item['category'] == 'PTY':
            weather_data['sky2'] = item['fcstValue']

    return weather_data

def proc_weather(city_name):
    dict_sky = forecast()

    str_sky = city_name
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

    return str_sky, dict_sky['tmp'], dict_sky['hum']
    
def weather_city(city_name):
    params['nx'] = city[city_name]['x']
    params['ny'] = city[city_name]['y']
    result, tmp, hum = proc_weather(city_name)
    print(result)
    return result, tmp, hum

resut, tmp, hum = weather_city('서울')
I2C_ADDR = 0x27
lcd = CharLCD('PCF8574', I2C_ADDR, port=1)
lcd.write_string(tmp + ' C')
time.sleep(5)   
lcd.cursor_pos = (1, 4)  
lcd.write_string(hum+' %')   
time.sleep(5)  
lcd.clear()

'''
서울 날씨 : 맑음
온도 : 19ºC
습도 : 95%
'''