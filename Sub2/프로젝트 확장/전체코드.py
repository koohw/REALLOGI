import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import cv2
import math  # 기울기 계산 시 사용
import os
from moviepy.editor import VideoFileClip

# CUDA 사용 가능한지 확인
if not cv2.cuda.getCudaEnabledDeviceCount():
    raise Exception("CUDA가 지원되지 않습니다. OpenCV가 CUDA로 컴파일되었는지 확인하세요.")

# 이미지 로드
image = mpimg.imread('solidWhiteCurve.jpg')

# 관심 영역 정의 및 관심 영역 크롭
height, width, _ = image.shape
region_of_interest_vertices = [
    (0, height),
    (width / 2, height / 2),
    (width, height),
]

# 관심 영역 추출 함수
def region_of_interest(img, vertices):
    mask = np.zeros_like(img)
    
    # 이미지가 2차원(그레이스케일)인지 3차원(RGB)인지 확인
    if len(img.shape) > 2:
        channel_count = img.shape[2]
        match_mask_color = (255,) * channel_count
    else:
        match_mask_color = 255  # 그레이스케일 이미지인 경우
    
    cv2.fillPoly(mask, vertices, match_mask_color)
    masked_image = cv2.bitwise_and(img, mask)
    return masked_image

# 선을 오버레이로 렌더링
def draw_lines(img, lines, color=[255, 0, 0], thickness=3):
    if lines is None:
        return
    img = np.copy(img)
    line_img = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
    for line in lines:
        for x1, y1, x2, y2 in line:
            cv2.line(line_img, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)
    img = cv2.addWeighted(img, 0.8, line_img, 1.0, 0.0)
    return img

# 그레이스케일 및 Canny 엣지 검출을 CUDA로 수행
def process_image_with_cuda(image):
    # GPU로 이미지 업로드
    gpu_image = cv2.cuda_GpuMat()
    gpu_image.upload(image)
    
    # 그레이스케일 변환 (CUDA)
    gpu_gray = cv2.cuda.cvtColor(gpu_image, cv2.COLOR_RGB2GRAY)
    
    # Canny 엣지 검출 (CUDA)
    gpu_canny = cv2.cuda.createCannyEdgeDetector(100, 200)
    gpu_edges = gpu_canny.detect(gpu_gray)
    
    # GPU에서 CPU로 결과 다운로드
    edges = gpu_edges.download()

    return edges

# 처리 시작
cropped_image = region_of_interest(image, np.array([region_of_interest_vertices], np.int32))

# CUDA를 이용하여 그레이스케일 및 Canny 에지 검출
cannyed_image = process_image_with_cuda(cropped_image)

# 관심 영역 다시 적용
cropped_image = region_of_interest(cannyed_image, np.array([region_of_interest_vertices], np.int32))

# Hough 변환을 사용한 선 검출
lines = cv2.HoughLinesP(cropped_image, rho=6, theta=np.pi / 60, threshold=160, lines=np.array([]), minLineLength=40, maxLineGap=25)

# 선을 왼쪽과 오른쪽으로 구분
left_line_x = []
left_line_y = []
right_line_x = []
right_line_y = []
for line in lines:
    for x1, y1, x2, y2 in line:
        slope = (y2 - y1) / (x2 - x1)  # 기울기 계산
        if math.fabs(slope) < 0.5:  # 기울기가 작으면 무시
            continue
        if slope <= 0:  # 기울기가 음수이면 왼쪽 그룹
            left_line_x.extend([x1, x2])
            left_line_y.extend([y1, y2])
        else:  # 그렇지 않으면 오른쪽 그룹
            right_line_x.extend([x1, x2])
            right_line_y.extend([y1, y2])

# 선을 왼쪽과 오른쪽으로 구분
min_y = image.shape[0] * (3 / 5)  # 수평선 바로 아래
max_y = image.shape[0]  # 이미지의 하단
poly_left = np.poly1d(np.polyfit(left_line_y, left_line_x, deg=1))
left_x_start = int(poly_left(max_y))
left_x_end = int(poly_left(min_y))
poly_right = np.poly1d(np.polyfit(right_line_y, right_line_x, deg=1))
right_x_start = int(poly_right(max_y))
right_x_end = int(poly_right(min_y))

line_image = draw_lines(image, [
    [[left_x_start, max_y, left_x_end, min_y],
     [right_x_start, max_y, right_x_end, min_y]]
], thickness=5)

plt.figure(figsize=(10, 5))  # 원본 이미지와 처리된 이미지 나란히 시각화
plt.subplot(1, 2, 1)          # 원본 이미지
plt.imshow(image)
plt.title("Original Image")

plt.subplot(1, 2, 2)  # 처리된 이미지
plt.imshow(line_image)
plt.title("Processed Image")
plt.show()

# 비디오 주석 추가
white_output = 'solidWhiteRight_output.mp4'
clip1 = VideoFileClip("solidWhiteRight_input.mp4")

# pipeline 함수 정의
def pipeline(frame):
    cropped_image = region_of_interest(frame, np.array([region_of_interest_vertices], np.int32))
    cannyed_image = process_image_with_cuda(cropped_image)
    cropped_image = region_of_interest(cannyed_image, np.array([region_of_interest_vertices], np.int32))
    
    lines = cv2.HoughLinesP(cropped_image, rho=6, theta=np.pi / 60, threshold=160, lines=np.array([]), minLineLength=40, maxLineGap=25)
    
    # 선 그리기 및 반환
    if lines is not None:
        left_line_x = []
        left_line_y = []
        right_line_x = []
        right_line_y = []
        for line in lines:
            for x1, y1, x2, y2 in line:
                slope = (y2 - y1) / (x2 - x1)
                if math.fabs(slope) < 0.5:
                    continue
                if slope <= 0:
                    left_line_x.extend([x1, x2])
                    left_line_y.extend([y1, y2])
                else:
                    right_line_x.extend([x1, x2])
                    right_line_y.extend([y1, y2])

        min_y = frame.shape[0] * (3 / 5)
        max_y = frame.shape[0]
        if left_line_x and right_line_x:
            poly_left = np.poly1d(np.polyfit(left_line_y, left_line_x, deg=1))
            left_x_start = int(poly_left(max_y))
            left_x_end = int(poly_left(min_y))
            poly_right = np.poly1d(np.polyfit(right_line_y, right_line_x, deg=1))
            right_x_start = int(poly_right(max_y))
            right_x_end = int(poly_right(min_y))
            frame = draw_lines(frame, [
                [[left_x_start, max_y, left_x_end, min_y],
                 [right_x_start, max_y, right_x_end, min_y]]
            ], thickness=5)
    
    return frame

white_clip = clip1.fl_image(pipeline)
white_clip.write_videofile(white_output, audio=False)
