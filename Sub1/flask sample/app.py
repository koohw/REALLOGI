from flask import Flask, render_template, request

app = Flask(__name__)


@app.route('/',methods=["GET"])             # 서버코드에서 가장 먼저 실행되는 코드
def index():
    return render_template("index.html")    # index.html을 첫 페이지로 설정


@app.route('/button', methods=['POST'])     # 버튼 클릭 시 호출되는 함수
def button():
    user_input = request.form['inputText']  # 입력한 값을 가져옴
    print("입력 값", user_input)            # 'inputText'는 html에 설정된 name 값
    
    numt_list = []
    for i in range(1,int(user_input)+1):    # 약수 구하기
        if int(user_input)%i == 0:
            numt_list.append(i)
    print("출력 값", numt_list)
    return render_template("index.html",user_input=numt_list)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234)                      