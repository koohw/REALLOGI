import requests
from datetime import datetime
import xmltodict

# 1) 지역별 (nx, ny) 좌표 딕셔너리
# 참고로, 기상청 단기예보 기준 격자 좌표를 사용 (일부 예시값).
LOCATION_COORDS = {
    "서울":  (60, 127),
    "부산":  (98, 76),
    "대구":  (89, 90),
    "광주":  (58, 74),
    "대전":  (67, 100),
    "인천":  (55, 124),
    "울산":  (102, 84),
    "세종":  (66, 103),
    "제주":  (52, 38)
    # 필요에 따라 다른 도시도 추가
}

# 2) 날짜/시간 구하기
def get_base_date():
    """
    현재 시각을 기준으로 기상청 API 요청시 base_date를 구한다.
    예: 20230101
    """
    return datetime.now().strftime("%Y%m%d")

def get_base_time():
    """
    기상청 초단기 예보 기준 (매 시각 30분) 에 맞춰 base_time을 구한다.
    """
    now = datetime.now()
    if now.minute < 45:
        # 45분 전이면 직전 시간의 '30분'으로 사용
        hour = now.hour - 1 if now.hour > 0 else 23
        return f"{hour:02d}30"
    else:
        # 45분 이후면 현재 시간의 '30분'
        return f"{now.hour:02d}30"

# 3) 기상청 API 호출
def get_weather_data(city_name: str) -> dict:
    """
    city_name(예: "서울")을 받아서, 해당 지역의 날씨정보를 딕셔너리 형태로 반환.
    """
    # 서비스키(본인 발급키 사용)
    SERVICE_KEY = "47LaaHxHRXV84O2NSfDTaFh2Tsz6V%2BbKOflVFji3DFI9TWuVqpVVVPEfrZQ%2BJsBGRTzXpv6iSWnQJTUz8APRmQ%3D%3D"
    # 엔드포인트
    URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"

    # 1) 도시 -> 격자 좌표
    nx, ny = LOCATION_COORDS.get(city_name, (60, 127))  # 기본 서울(60,127)로 처리

    # 2) 요청 파라미터
    params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": "1",
        "numOfRows": "1000",
        "dataType": "XML",  # or JSON
        "base_date": get_base_date(),
        "base_time": get_base_time(),
        "nx": nx,
        "ny": ny,
    }

    # 3) API 요청
    response = requests.get(URL, params=params)
    # 4) XML -> dict 변환
    dict_data = xmltodict.parse(response.text)

    # 5) 필요한 데이터 추출
    weather_data = {}
    try:
        items = dict_data["response"]["body"]["items"]["item"]
        for item in items:
            category = item["category"]
            fcstValue = item["fcstValue"]

            if category == "T1H":  # 기온
                weather_data["temp"] = fcstValue
            elif category == "REH":  # 습도
                weather_data["humidity"] = fcstValue
            elif category == "PTY":  # 강수형태 (비, 눈)
                weather_data["pty"] = fcstValue
            elif category == "SKY":  # 하늘상태 (맑음, 구름많음 등)
                weather_data["sky"] = fcstValue
    except KeyError:
        pass

    return weather_data

# 4) 날씨정보 해석 후 출력용 문자열 만들기
def get_weather_string(city_name: str) -> str:
    """
    get_weather_data() 로부터 받은 정보로
    "맑음", "눈", "비" 등을 텍스트로 조합한 문자열을 만들어 반환.
    """
    data = get_weather_data(city_name)
    
    if not data:
        return f"{city_name} 날씨 정보를 가져오지 못했습니다."

    # 기온, 습도
    temp = data.get("temp", "N/A")
    humidity = data.get("humidity", "N/A")

    # 하늘상태
    sky_code = data.get("sky", "0")   # 1(맑음), 3(구름많음), 4(흐림) ...
    pty_code = data.get("pty", "0")   # 0(없음), 1(비), 2(비/눈), 3(눈)...

    # 하늘상태 문자열화
    sky_str = ""
    if pty_code == "0":  # 강수 없음
        if sky_code == "1":
            sky_str = "맑음"
        elif sky_code == "3":
            sky_str = "구름많음"
        elif sky_code == "4":
            sky_str = "흐림"
        else:
            sky_str = "알 수 없음"
    elif pty_code == "1":
        sky_str = "비"
    elif pty_code == "2":
        sky_str = "비/눈"
    elif pty_code == "3":
        sky_str = "눈"
    elif pty_code == "5":
        sky_str = "빗방울"
    elif pty_code == "6":
        sky_str = "빗방울눈날림"
    elif pty_code == "7":
        sky_str = "눈날림"

    result = (
        f"{city_name} 날씨 : {sky_str}\n"
        f"온도 : {temp}℃\n"
        f"습도 : {humidity}%"
    )
    return result

# 테스트용
if __name__ == "__main__":
    print(get_weather_string("서울"))
