from flask import Flask, render_template, request
import requests
from datetime import datetime

app = Flask(__name__)

# API URL 및 인증키
API_URL = 'https://www.koreaexim.go.kr/site/program/financial/exchangeJSON'
API_KEY = '98IzSyf3L8LYPEhydcM8b8cjFoqkGuwi'  

@app.route('/', methods=["GET"])
def index():
    return render_template("index.html")  # 메인 페이지 렌더링

@app.route('/button', methods=['POST'])
def button():
    # 사용자가 입력한 날짜 가져오기 (기본값: 오늘 날짜)
    search_date = request.form.get('searchdate', datetime.now().strftime('%Y%m%d'))

    # API 요청 파라미터
    params = {
        'authkey': API_KEY,
        'searchdate': search_date,
        'data': 'AP01'
    }

    try:
        # API 호출
        response = requests.get(API_URL, params=params)
        response.raise_for_status()  # HTTP 에러 발생 시 예외 처리

        # JSON 응답 파싱
        data = response.json()

        # 디버깅: 응답 데이터 출력
        print("API 응답 데이터:", data)

        if not data:
            error_message = f"{search_date}에 대한 데이터가 없습니다."
            return render_template("index.html", error_message=error_message)

        # RESULT 코드 확인
        result_code = data[0].get('result')
        if result_code == 1:  # 성공
            exchange_data = [
                {
                    '통화코드': item.get('cur_unit'),
                    '국가/통화명': item.get('cur_nm'),
                    '전신환(송금받으실때)': item.get('ttb'),
                    '전신환(송금보내실때)': item.get('tts'),
                    '매매기준율': item.get('deal_bas_r')
                }
                for item in data
            ]
            return render_template("index.html", exchange_data=exchange_data)
        else:
            error_message = f"API 오류: RESULT 코드 {result_code} (인증키 또는 요청 파라미터를 확인하세요)"
            return render_template("index.html", error_message=error_message)

    except Exception as e:
        error_message = f"요청 중 오류 발생: {str(e)}"
        return render_template("index.html", error_message=error_message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234)
