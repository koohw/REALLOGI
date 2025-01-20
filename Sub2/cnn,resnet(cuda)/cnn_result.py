import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image

# CUDA 사용 가능한지 확인
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Using device: {device}')

class SimpleCNN(nn.Module):
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
        self.fc1 = nn.Linear(32 * 16 * 16, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 2)

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = x.view(-1, 32 * 16 * 16)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

# 데이터 전처리
transform = transforms.Compose([
    transforms.Resize((64, 64)),
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

image_path = '2.jpg'
image = Image.open(image_path)
image = transform(image).unsqueeze(0)

# 이미지를 GPU로 이동
image = image.to(device)

# 모델을 GPU로 이동
net = SimpleCNN().to(device)
net.load_state_dict(torch.load('cnn_cup_mouse.pth', map_location=device))
net.eval()

# 추론
outputs = net(image)
_, predicted = torch.max(outputs, 1)

# 클래스 이름
classes = ['cup', 'mouse']
print(f'The image is classified as: {classes[predicted.item()]}')
