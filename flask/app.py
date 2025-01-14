from flask import Flask, render_template, request
from weather import weather_city, city  # weather.py 파일 가져오기

app = Flask(__name__)

@app.route('/', methods=["GET", "POST"])
def index():
    if request.method == "POST":
        city_name = request.form.get('city')  # 선택된 도시 가져오기
        if city_name in city:  # 유효한 도시인지 확인
            weather_info = weather_city(city_name)  # 날씨 정보 가져오기
        else:
            weather_info = "도시를 선택해주세요."
        return render_template("index.html", weather_info=weather_info)

    return render_template("index.html")  # 초기 페이지

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234)
