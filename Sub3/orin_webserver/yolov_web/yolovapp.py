import torch  # CUDA를 사용하기 위한 torch 임포트
from flask import Flask, Response, render_template, request
import cv2
from ultralytics import YOLO

# 모델을 GPU 또는 CPU에 할당
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = YOLO("yolov8n.pt").to(device)
class_names = model.names

app = Flask(__name__)
inputText = ""

def gen_frames():
    cap = cv2.VideoCapture(0)
    
    while True:
        success, frame = cap.read()  # 카메라 프레임 읽기
        if not success:
            break

        if torch.cuda.is_available():
            gpu_frame = cv2.cuda_GpuMat()
            gpu_frame.upload(frame)  # GPU로 프레임 업로드
            frame = gpu_frame.download()  # GPU에서 처리가 끝난 후 다시 다운로드
            
        results = model(frame)
        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy()  # Bounding box coordinates
            confs = result.boxes.conf.cpu().numpy()  # Confidence scores
            classes = result.boxes.cls.cpu().numpy()  # Class IDs
            
            for box, conf, cls in zip(boxes, confs, classes):
                x1, y1, x2, y2 = box
                class_name = class_names[int(cls)]
                if len(inputText) == 0:
                    label = f"{class_name} {conf:.2f}"
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                elif inputText.lower() == class_name.lower():
                    label = f"{class_name} {conf:.2f}"
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                    cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    break
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/button', methods=['GET', 'POST'])
def button():
    global inputText
    inputText = request.form.get('inputText')
    print(inputText)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234)
