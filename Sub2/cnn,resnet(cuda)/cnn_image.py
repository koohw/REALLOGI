import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import torch.nn.functional as F

# CUDA 사용 가능한지 확인 후 하단의 모델을 GPU로 이동
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Using device: {device}')

# 데이터 전처리
transform = transforms.Compose([
    transforms.Resize((64, 64)),  # 이미지 크기를 64x64로 조정
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

trainset = torchvision.datasets.ImageFolder(root='./data/train', transform=transform)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=4, shuffle=True, num_workers=2)
testset = torchvision.datasets.ImageFolder(root='./data/test', transform=transform)
testloader = torch.utils.data.DataLoader(testset, batch_size=4, shuffle=False, num_workers=2)

classes = trainset.classes

class SimpleCNN(nn.Module):
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 16, 3, padding=1)  # 1번째 합성곱 계층 (입력 채널: 3, 출력 채널: 16)
        self.pool = nn.MaxPool2d(2, 2)  # 맥스 풀링 계층
        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)  # 2번째 합성곱 계층 (입력 채널: 16, 출력 채널: 32)
        self.fc1 = nn.Linear(32 * 16 * 16, 120)  # 완전 연결 계층 (입력 특징 수: 32*16*16, 출력: 120)
        self.fc2 = nn.Linear(120, 84)  # 완전 연결 계층 (입력 특징 수: 120, 출력: 84)
        self.fc3 = nn.Linear(84, len(classes))  # 출력 계층 (입력 특징 수: 84, 출력: 클래스 수)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))  # 1번째 합성곱 -> ReLU -> 풀링
        x = self.pool(F.relu(self.conv2(x)))  # 2번째 합성곱 -> ReLU -> 풀링
        x = x.view(-1, 32 * 16 * 16)  # 평탄화
        x = F.relu(self.fc1(x))  # 1번째 완전 연결 -> ReLU
        x = F.relu(self.fc2(x))  # 2번째 완전 연결 -> ReLU
        x = self.fc3(x)  # 출력 계층
        return x

# 모델을 GPU로 이동
net = SimpleCNN().to(device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(net.parameters(), lr=0.001, momentum=0.9)

# 학습
for epoch in range(2):  # 모델 학습 2회
    running_loss = 0.0
    for i, data in enumerate(trainloader, 0):
        inputs, labels = data
        inputs, labels = inputs.to(device), labels.to(device)  # 데이터를 GPU로 이동
        optimizer.zero_grad()
        outputs = net(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
        if i % 2 == 0:  # 2번 학습 할 때 미니배치 로그를 출력
            print(f'[{epoch + 1}, {i + 1:5d}] loss: {running_loss / 100:.3f}')
            running_loss = 0.0
print('Finished Training')

# 모델 저장
PATH = './cnn_cup_mouse.pth'
torch.save(net.state_dict(), PATH)

# 테스트
correct = 0
total = 0
with torch.no_grad():
    for data in testloader:
        images, labels = data
        images, labels = images.to(device), labels.to(device)  # 데이터를 GPU로 이동
        outputs = net(images)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

print(f'Accuracy of the network on the test images: {100 * correct / total}%')

# 클래스별 정확도 출력
correct_pred = {classname: 0 for classname in classes}
total_pred = {classname: 0 for classname in classes}

with torch.no_grad():
    for data in testloader:
        images, labels = data
        images, labels = images.to(device), labels.to(device)  # 데이터를 GPU로 이동
        outputs = net(images)
        _, predictions = torch.max(outputs, 1)
        for label, prediction in zip(labels, predictions):
            if label == prediction:
                correct_pred[classes[label]] += 1
            total_pred[classes[label]] += 1

for classname, correct_count in correct_pred.items():
    accuracy = 100 * float(correct_count) / total_pred[classname]
    print(f'Accuracy for class: {classname:5s} is {accuracy:.1f} %')
