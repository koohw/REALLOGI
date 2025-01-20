import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import cv2
import math

# CUDA 사용 여부 확인
use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
if use_cuda:
    print("CUDA가 활성화되었습니다.")
else:
    print("CUDA를 사용할 수 없습니다. CPU 모드로 전환합니다.")

def region_of_interest(img, vertices):
    mask = np.zeros_like(img)
    match_mask_color = 255
    cv2.fillPoly(mask, vertices, match_mask_color)
    masked_image = cv2.bitwise_and(img, mask)
    return masked_image

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

def pipeline(image):
    if use_cuda:
        # GPU에서 처리
        gpu_frame = cv2.cuda_GpuMat()
        gpu_frame.upload(image)

        # CUDA로 그레이스케일 변환 및 Canny 엣지 검출
        gpu_gray = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_RGB2GRAY)
        gpu_canny = cv2.cuda.createCannyEdgeDetector(100, 200)
        gpu_cannyed_image = gpu_canny.detect(gpu_gray)
        cannyed_image = gpu_cannyed_image.download()

    else:
        # CPU에서 처리
        gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        cannyed_image = cv2.Canny(gray_image, 100, 200)

    region_of_interest_vertices = [
        (0, image.shape[0]),
        (image.shape[1] / 2, image.shape[0] / 2),
        (image.shape[1], image.shape[0]),
    ]

    cropped_image = region_of_interest(cannyed_image, np.array([region_of_interest_vertices], np.int32))

    lines = cv2.HoughLinesP(cropped_image, rho=6, theta=np.pi / 60, threshold=160, lines=np.array([]), minLineLength=40, maxLineGap=25)

    if lines is None:
        return image

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

    min_y = image.shape[0] * (3 / 5)
    max_y = image.shape[0]

    line_image = np.copy(image)

    if len(left_line_x) > 0 and len(left_line_y) > 0:
        poly_left = np.poly1d(np.polyfit(left_line_y, left_line_x, deg=1))
        left_x_start = int(poly_left(max_y))
        left_x_end = int(poly_left(min_y))
        cv2.line(line_image, (left_x_start, int(max_y)), (left_x_end, int(min_y)), [255, 0, 0], 5)

    if len(right_line_x) > 0 and len(right_line_y) > 0:
        poly_right = np.poly1d(np.polyfit(right_line_y, right_line_x, deg=1))
        right_x_start = int(poly_right(max_y))
        right_x_end = int(poly_right(min_y))
        cv2.line(line_image, (right_x_start, int(max_y)), (right_x_end, int(min_y)), [255, 0, 0], 5)

    return line_image

from moviepy.editor import VideoFileClip

# Process the video
clip1 = VideoFileClip("solidWhiteRight_input.mp4")
white_clip = clip1.fl_image(pipeline)
white_clip.write_videofile("solidWhiteRight_output.mp4", audio=False)
