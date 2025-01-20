from flask import Flask, Response, render_template, request
import cv2

app = Flask(__name__)

def gen_frames():
    camera = cv2.VideoCapture(0)  # 0번 카메라 (Jetson Orin의 기본 카메라)
   
    # CUDA 사용 가능 여부 확인
    use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
   
    while True:
        success, frame = camera.read()  # 카메라 프레임 읽기
        if not success:
            break
        else:
            if use_cuda:
                # GPU로 프레임 업로드
                gpu_frame = cv2.cuda_GpuMat()
                gpu_frame.upload(frame)
                # GPU 처리된 프레임을 다시 CPU로 다운로드
                frame = gpu_frame.download()
           
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # MJPEG 스트리밍 방식으로 프레임 전송
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234)
