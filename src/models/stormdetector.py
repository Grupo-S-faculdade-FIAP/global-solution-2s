import cv2
import torch
import numpy as np
import pathlib
from pathlib import Path

pathlib.PosixPath = pathlib.WindowsPath

BASE_DIR = Path(__file__).parent
weights_path = str(BASE_DIR / 'weights' / 'best.pt')
image_path = str(BASE_DIR.parent.parent / 'data' / 'model-dataset' / 'images' / 'test' / 'test-storm.png')

model = torch.hub.load('ultralytics/yolov5', 'custom', weights_path, force_reload=True)
model.conf = 0.04

print(f"Weights: {weights_path}")
print(f"Image:   {image_path}")

im = cv2.imread(image_path)
if im is None:
    raise FileNotFoundError(f"Image not found: {image_path}")
results = model(im)
print(results)
frame = np.squeeze(results.render())
frame = cv2.resize(frame, (1280, 720))
cv2.imshow('Deteccao', frame)
cv2.waitKey(0)
cv2.destroyAllWindows()