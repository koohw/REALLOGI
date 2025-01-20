import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import torchvision.models as models

# CUDA가 가능한지 확인하고 사용 가능하면 GPU로 설정
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 데이터셋 변환 및 로드
transform = transforms.Compose([
    transforms.Resize((224, 224)),  # ResNet은 224x224 크기의 이미지를 사용합니다
    transforms.RandomHorizontalFlip(),
    transforms.RandomCrop(224, padding=4),
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
])

trainset = torchvision.datasets.ImageFolder(root='./data/train', transform=transform)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=64, shuffle=True, num_workers=2)

testset = torchvision.datasets.ImageFolder(root='./data/test', transform=transform)
testloader = torch.utils.data.DataLoader(testset, batch_size=64, shuffle=False, num_workers=2)

classes = trainset.classes  # 클래스 이름 자동 설정 ('cup', 'mouse')

# ResNet-18 모델 불러오기 및 수정
net = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
num_ftrs = net.fc.in_features
net.fc = nn.Linear(num_ftrs, 2)  # 'cup'과 'mouse'는 2개의 클래스이므로 출력층을 수정

# 모델을 CUDA로 이동
net = net.to(device)

# 손실 함수와 옵티마이저 정의
criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(net.parameters(), lr=0.001, momentum=0.9)

# 네트워크 학습
for epoch in range(2):  # 학습 횟수 2번
    running_loss = 0.0
    for i, data in enumerate(trainloader, 0):
        inputs, labels = data  # 입력 데이터와 라벨 가져오기

        # 입력 데이터를 CUDA로 이동
        inputs, labels = inputs.to(device), labels.to(device)
        
        optimizer.zero_grad()  # 파라미터 그라디언트 초기화

        # 순전파, 역전파, 최적화 수행
        outputs = net(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        # 통계 출력
        running_loss += loss.item()
        if i % 2 == 0:  # 200 미니배치마다 출력
            print(f'[{epoch + 1}, {i + 1:5d}] loss: {running_loss / 200:.3f}')
            running_loss = 0.0

print('Training Finished')

# 학습된 모델 저장
PATH = './resnet18_cup_mouse.pth'
torch.save(net.state_dict(), PATH)

# 테스트 데이터에 대한 네트워크 평가
correct = 0
total = 0
with torch.no_grad():
    for data in testloader:
        images, labels = data
        
        # 테스트 데이터도 CUDA로 이동
        images, labels = images.to(device), labels.to(device)
        
        outputs = net(images)
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

print(f'Accuracy of the network on the test images: {100 * correct / total:.2f}%')

# 클래스별 정확도 계산
correct_pred = {classname: 0 for classname in classes}
total_pred = {classname: 0 for classname in classes}

# 변화도는 필요하지 않으므로 비활성화
with torch.no_grad():
    for data in testloader:
        images, labels = data
        
        # 테스트 데이터도 CUDA로 이동
        images, labels = images.to(device), labels.to(device)
        
        outputs = net(images)
        _, predictions = torch.max(outputs, 1)
        # 각 클래스별로 올바른 예측 수를 집계
        for label, prediction in zip(labels, predictions):
            if label == prediction:
                correct_pred[classes[label]] += 1
            total_pred[classes[label]] += 1

# 각 클래스별 정확도 출력
for classname, correct_count in correct_pred.items():
    accuracy = 100 * float(correct_count) / total_pred[classname]
    print(f'Accuracy for class: {classname:5s} is {accuracy:.1f} %')
