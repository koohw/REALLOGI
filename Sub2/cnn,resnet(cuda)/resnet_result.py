import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image

# CUDA가 가능한지 확인하고 사용 가능한 경우 GPU로 설정
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

image_path = '1.jpg'
image = Image.open(image_path)
image = transform(image).unsqueeze(0)

# 이미지를 CUDA로 이동
image = image.to(device)

# ResNet-18 모델 불러오기 및 수정
net = models.resnet18()

# 출력층 수정
num_ftrs = net.fc.in_features
net.fc = nn.Linear(num_ftrs, 2)

# 모델을 CUDA로 이동
net = net.to(device)

# 저장된 모델 불러오기
net.load_state_dict(torch.load('resnet18_cup_mouse.pth'))

# 평가 모드 설정
net.eval()

# 추론 수행
with torch.no_grad():  # 필요 없는 그라디언트 계산 방지
    outputs = net(image)
    _, predicted = torch.max(outputs, 1)

classes = ['cup', 'mouse']
print(f'The image is classified as: {classes[predicted.item()]}')
