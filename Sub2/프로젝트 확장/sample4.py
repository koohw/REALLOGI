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

# Load the image
image = mpimg.imread('solidWhiteCurve.jpg')
height, width = image.shape[0], image.shape[1]
region_of_interest_vertices = [
    (0, height),
    (width / 2, height / 2),
    (width, height),
]

# Define region of interest function
def region_of_interest(img, vertices):
    mask = np.zeros_like(img)
    match_mask_color = 255
    cv2.fillPoly(mask, vertices, match_mask_color)
    masked_image = cv2.bitwise_and(img, mask)
    return masked_image

# Define draw lines function
def draw_lines(img, lines, color=[255, 0, 0], thickness=3):
    if lines is None:
        return img
    img = np.copy(img)
    line_img = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
    for line in lines:
        for x1, y1, x2, y2 in line:
            cv2.line(line_img, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)
    img = cv2.addWeighted(img, 0.8, line_img, 1.0, 0.0)
    return img


# GPU에서 이미지 처리
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
    np.array([region_of_interest_vertices], np.int32),
)

# Hough 변환
lines = cv2.HoughLinesP(
    cropped_image,
    rho=6,
    theta=np.pi / 60,
    threshold=160,
    lines=np.array([]),
    minLineLength=40,
    maxLineGap=25
)

# 직선 그리기
line_image = draw_lines(image, lines)

# 결과 출력
plt.figure()
plt.imshow(line_image)
plt.show()

