import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import cv2

# CUDA 사용 가능한지 확인
use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
if use_cuda:
    print("CUDA가 활성화되었습니다.")
else:
    print("CUDA를 사용할 수 없습니다. CPU 모드로 실행됩니다.")

image = mpimg.imread('solidWhiteCurve.jpg')
print('This image is:', type(image), 'with dimensions:', image.shape)
plt.imshow(image)
plt.show()

height, width, _ = image.shape

region_of_interest_vertices = [
    (0, height),
    (width / 2, height / 2),
    (width, height),
]

def region_of_interest(img, vertices):
    # GPU 또는 CPU 모드로 실행
    if use_cuda:
        # 이미지를 GPU 메모리로 업로드
        gpu_img = cv2.cuda_GpuMat()
        gpu_img.upload(img)
        
        mask = np.zeros_like(img)
        channel_count = img.shape[2]
        match_mask_color = (255,) * channel_count

        # 마스크 생성
        gpu_mask = cv2.cuda_GpuMat()
        gpu_mask.upload(mask)
        
        # ROI 영역을 GPU에서 처리
        cv2.fillPoly(mask, vertices, match_mask_color)
        gpu_mask.upload(mask)  # 다시 GPU로 업로드
        
        # 비트 연산을 GPU에서 처리
        gpu_result = cv2.cuda.bitwise_and(gpu_img, gpu_mask)
        
        # 결과 이미지를 CPU로 다운로드
        masked_image = gpu_result.download()
    else:
        mask = np.zeros_like(img)
        channel_count = img.shape[2]
        match_mask_color = (255,) * channel_count
        cv2.fillPoly(mask, vertices, match_mask_color)
        masked_image = cv2.bitwise_and(img, mask)

    return masked_image

cropped_image = region_of_interest(
    image,
    np.array([region_of_interest_vertices], np.int32),
)
plt.figure()
plt.imshow(cropped_image)
plt.show()
