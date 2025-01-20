import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import cv2

# CUDA가 가능한지 확인
use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
if use_cuda:
    print("CUDA가 활성화되었습니다.")
else:
    print("CUDA를 사용할 수 없습니다. CPU 모드로 전환합니다.")

def region_of_interest(img, vertices):
    mask = np.zeros_like(img)
    match_mask_color = 255  # 그레이스케일용으로 설정
    cv2.fillPoly(mask, vertices, match_mask_color)
    masked_image = cv2.bitwise_and(img, mask)
    return masked_image

image = mpimg.imread('solidWhiteCurve.jpg')
height, width, _ = image.shape
region_of_interest_vertices = [
    (0, height),
    (width / 2, height / 2),
    (width, height),
]

plt.figure()
plt.imshow(image)
plt.show()

if use_cuda:
    # GPU에서 이미지 작업 수행
    gpu_frame = cv2.cuda_GpuMat()
    gpu_frame.upload(image)

    # GPU에서 그레이스케일 변환
    gpu_gray = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_RGB2GRAY)

    # GPU에서 Canny 엣지 검출
    gpu_canny = cv2.cuda.createCannyEdgeDetector(100, 200)
    gpu_edges = gpu_canny.detect(gpu_gray)

    # 결과를 다시 CPU로 다운로드
    cannyed_image = gpu_edges.download()
else:
    # CPU에서 그레이스케일 변환
    gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    # CPU에서 Canny 엣지 검출
    cannyed_image = cv2.Canny(gray_image, 100, 200)


# Canny 처리 후 크롭 작업
cropped_image = region_of_interest(
    cannyed_image,
    np.array([region_of_interest_vertices], np.int32)
)

plt.figure()
plt.imshow(cropped_image, cmap='gray')
plt.show()

