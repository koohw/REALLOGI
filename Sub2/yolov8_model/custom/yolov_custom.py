import yaml
import ultralytics
from ultralytics import YOLO

data = {
    'train': "/home/orin/Downloads/yolov8/train/images",
    'val': "/home/orin/Downloads/yolov8/valid/images",
    'test': "/home/orin/Downloads/yolov8/test/images",
    'names': ['fire', 'smoke'],
    'nc': 2
}

with open("/home/orin/Downloads/yolov8/data.yaml", "w") as f:
    yaml.dump(data, f)

with open("/home/orin/Downloads/yolov8/data.yaml", "r") as f:
    data = yaml.safe_load(f)

ultralytics.checks()
model = YOLO('yolov8n.pt').to('cuda')  
data_path = '/home/orin/Downloads/yolov8/data.yaml'
epochs = 50
model.train(data=data_path, epochs=epochs, device='cuda')  


result = model.predict(source="/home/orin/Downloads/yolov8/test/images", save=True, device='cuda')  
