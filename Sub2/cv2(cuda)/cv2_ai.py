import cv2
import numpy as np
import os

# CUDA가 가능한지 확인
use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
if use_cuda:
    print("CUDA가 활성화되었습니다.")
else:
    print("CUDA를 사용할 수 없습니다. CPU 모드로 전환합니다.")

cup_image_path = 'cup/'
mouse_image_path = 'mouse/'
img_size = (64, 64)
features = []
labels = []

# 이미지 로드 및 처리 (CUDA 활용)
def process_image(image_path, label):
    for filename in os.listdir(image_path):
        img = cv2.imread(os.path.join(image_path, filename))
        if img is not None:
            img = cv2.resize(img, img_size)
            if use_cuda:
                # GPU 메모리로 이미지를 올림
                gpu_img = cv2.cuda.GpuMat()
                gpu_img.upload(img)
                
                # GPU에서 BGR -> HSV 변환
                gpu_hsv = cv2.cuda.cvtColor(gpu_img, cv2.COLOR_BGR2HSV)
                
                # 다시 HSV -> BGR로 변환하여 원래 색상으로 복구
                gpu_bgr = cv2.cuda.cvtColor(gpu_hsv, cv2.COLOR_HSV2BGR)
                
                # CPU 메모리로 다운로드
                processed_img = gpu_bgr.download()
            else:
                # CPU 모드에서는 BGR -> HSV -> BGR 변환
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                processed_img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            
            features.append(processed_img.flatten())  # 변환된 이미지를 1차원 배열로
            labels.append(label)

# 컵 이미지 처리
process_image(cup_image_path, 0)

# 마우스 이미지 처리
process_image(mouse_image_path, 1)

# NumPy 배열로 변환
features = np.array(features, dtype=np.float32)
labels = np.array(labels, dtype=np.int32)

# SVM 학습
svm = cv2.ml.SVM_create()
svm.setKernel(cv2.ml.SVM_LINEAR)
svm.setType(cv2.ml.SVM_C_SVC)
svm.setC(1)
svm.train(features, cv2.ml.ROW_SAMPLE, labels)

# 학습된 모델 저장
svm.save('svm_model.yml')

# 테스트 이미지 처리 (CUDA 활용)
test_image = cv2.imread('1.jpg')
test_image = cv2.resize(test_image, img_size)

if use_cuda:
    gpu_test_img = cv2.cuda.GpuMat()
    gpu_test_img.upload(test_image)
    
    # BGR -> HSV -> BGR 변환
    gpu_hsv_test_image = cv2.cuda.cvtColor(gpu_test_img, cv2.COLOR_BGR2HSV)
    gpu_bgr_test_image = cv2.cuda.cvtColor(gpu_hsv_test_image, cv2.COLOR_HSV2BGR)
    
    test_image_processed = gpu_bgr_test_image.download()
else:
    hsv_test_image = cv2.cvtColor(test_image, cv2.COLOR_BGR2HSV)
    test_image_processed = cv2.cvtColor(hsv_test_image, cv2.COLOR_HSV2BGR)

test_feature = test_image_processed.flatten().astype(np.float32)

# 예측 수행
_, result = svm.predict(np.array([test_feature]))

# 결과 출력
if result[0][0] == 0:
    print("The image is classified as a cup.")
else:
    print("The image is classified as a mouse.")
