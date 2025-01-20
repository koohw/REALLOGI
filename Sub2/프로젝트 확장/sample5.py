import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import cv2
import math

# CUDA 사용 가능 여부 확인
use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
if use_cuda:
    print("CUDA가 활성화되었습니다.")
else:
    print("CUDA를 사용할 수 없습니다. CPU 모드로 전환합니다.")

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

# 이미지 로드
image = mpimg.imread('solidWhiteCurve.jpg')
height, width = image.shape[0], image.shape[1]

# GPU로 이미지 업로드
if use_cuda:
    # GPU에서 이미지 작업 수행
    gpu_frame = cv2.cuda_GpuMat()
    gpu_frame.upload(image)

    # GPU에서 그레이스케일 변환
    gpu_gray = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2GRAY)  # BGR에서 그레이스케일로 변환

    # GPU에서 Canny 엣지 검출
    gpu_canny = cv2.cuda.createCannyEdgeDetector(100, 200)  # Canny 엣지 검출 생성
    gpu_edges = gpu_canny.detect(gpu_gray)  # Canny 엣지 검출 수행

    # 결과를 다시 CPU로 다운로드
    cannyed_image = gpu_edges.download()  # GPU 결과를 CPU 메모리로 복사

else:
    # CPU에서 그레이스케일 변환
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # CPU에서 Canny 엣지 검출
    cannyed_image = cv2.Canny(gray_image, 100, 200)


# 관심 영역 정의
region_of_interest_vertices = [
    (0, height),
    (width / 2, height / 2),
    (width, height),
]

# 관심 영역 적용
cropped_image = region_of_interest(cannyed_image, np.array([region_of_interest_vertices], np.int32))

# Hough 변환
lines = cv2.HoughLinesP(cropped_image, rho=6, theta=np.pi / 60, threshold=160, lines=np.array([]), minLineLength=40, maxLineGap=25)

# 선을 왼쪽과 오른쪽으로 구분
left_line_x, left_line_y, right_line_x, right_line_y = [], [], [], []
if lines is not None:  # Check if lines were detected
    for line in lines:
        for x1, y1, x2, y2 in line:
            slope = (y2 - y1) / (x2 - x1)
            if math.fabs(slope) < 0.5:  # 기울기가 작은 선은 무시
                continue
            if slope <= 0:  # 왼쪽 선 그룹
                left_line_x.extend([x1, x2])
                left_line_y.extend([y1, y2])
            else:  # 오른쪽 선 그룹
                right_line_x.extend([x1, x2])
                right_line_y.extend([y1, y2])

# 선 그리기
if left_line_x and left_line_y and right_line_x and right_line_y:
    min_y, max_y = height * (3 / 5), height
    poly_left = np.poly1d(np.polyfit(left_line_y, left_line_x, deg=1))
    left_x_start, left_x_end = int(poly_left(max_y)), int(poly_left(min_y))
    poly_right = np.poly1d(np.polyfit(right_line_y, right_line_x, deg=1))
    right_x_start, right_x_end = int(poly_right(max_y)), int(poly_right(min_y))

    line_image = draw_lines(image, [
        [[left_x_start, max_y, left_x_end, min_y],
         [right_x_start, max_y, right_x_end, min_y]]
    ], thickness=5)

    # 결과 출력
    plt.figure()
    plt.imshow(line_image)
    plt.show()
else:
    print("선이 감지되지 않았습니다.")

