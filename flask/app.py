from flask import Flask, render_template, request
from weather import get_weather_string

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    weather_info = None
    selected_city = None

    if request.method == 'POST':
        selected_city = request.form.get('city')  # select 태그의 name="city"
        weather_info = get_weather_string(selected_city)

    return render_template('index.html', weather_info=weather_info, city=selected_city)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=1234, debug=True)
