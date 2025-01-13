from flask import Flask, render_template, request
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(2, GPIO.OUT)   #라즈베라파이 setup 설정


app = Flask(__name__)
GPIO.output(2, False)
@app.route('/',methods=["GET"])
def index():
    return render_template("index.html")

@app.route('/on', methods=['POST'])
def on():
    print("on")
    GPIO.output(2, True)
    return render_template("index.html")

@app.route('/off', methods=['POST'])
def off():
    print("off")
    GPIO.output(2, False)
    return render_template("index.html")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234)