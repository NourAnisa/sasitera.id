import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader, random_split
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns

sys.stdout.reconfigure(encoding='utf-8')

# Set device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[*] Menggunakan device: {device}")

# Path dataset
dataset_dir = r"Dataset Motif Kain Sasirangan\preprocessing"
if not os.path.exists(dataset_dir):
    dataset_dir = r"Dataset Motif Kain Sasirangan\Raw"

print(f"[*] Memuat dataset dari: {dataset_dir}")

# Transformasi data
data_transforms = {
    'train': transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ]),
    'val': transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ]),
}

# Load dataset
full_dataset = datasets.ImageFolder(dataset_dir)
classes = full_dataset.classes
print(f"[*] Kelas motif ditemukan: {classes}")

# Split 80% train, 20% val
train_size = int(0.8 * len(full_dataset))
val_size = len(full_dataset) - train_size
train_data, val_data = random_split(full_dataset, [train_size, val_size], generator=torch.Generator().manual_seed(42))

# Assign transforms
class DatasetWrapper(torch.utils.data.Dataset):
    def __init__(self, subset, transform=None):
        self.subset = subset
        self.transform = transform
        
    def __getitem__(self, index):
        x, y = self.subset[index]
        if self.transform:
            x = self.transform(x)
        return x, y
        
    def __len__(self):
        return len(self.subset)

train_dataset = DatasetWrapper(train_data, data_transforms['train'])
val_dataset = DatasetWrapper(val_data, data_transforms['val'])

train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)

print(f"[*] Jumlah data latih: {len(train_dataset)}, Data uji: {len(val_dataset)}")

# Bangun model MobileNetV2 transfer learning
model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
for param in model.features.parameters():
    param.requires_grad = False  # Freeze feature extractor

# Ganti classifier
model.classifier[1] = nn.Sequential(
    nn.Linear(model.last_channel, 128),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(128, len(classes))
)

model = model.to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.classifier.parameters(), lr=0.001)

# Training loop
epochs = 15
print("[*] Memulai pelatihan model CNN...")

train_losses, val_losses = [], []
train_accs, val_accs = [], []

for epoch in range(epochs):
    model.train()
    running_loss, correct = 0.0, 0
    for inputs, labels in train_loader:
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item() * inputs.size(0)
        _, preds = torch.max(outputs, 1)
        correct += torch.sum(preds == labels.data)
        
    train_loss = running_loss / len(train_dataset)
    train_acc = (correct.double() / len(train_dataset)).item()
    
    # Validation
    model.eval()
    val_loss, val_correct = 0.0, 0
    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            val_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            val_correct += torch.sum(preds == labels.data)
            
    val_loss = val_loss / len(val_dataset)
    val_acc = (val_correct.double() / len(val_dataset)).item()
    
    train_losses.append(train_loss)
    val_losses.append(val_loss)
    train_accs.append(train_acc)
    val_accs.append(val_acc)
    
    print(f"Epoch [{epoch+1}/{epochs}] Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")

# Evaluasi Akhir & Confusion Matrix
model.eval()
all_preds, all_labels = [], []
with torch.no_grad():
    for inputs, labels in val_loader:
        inputs = inputs.to(device)
        outputs = model(inputs)
        _, preds = torch.max(outputs, 1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.numpy())

print("\n=== CLASSIFICATION REPORT ===")
print(classification_report(all_labels, all_preds, target_names=classes))

# Simpan Model
os.makedirs("models", exist_ok=True)
model_path = os.path.join("models", "sasirangan_mobilenetv2.pth")
torch.save({
    'model_state_dict': model.state_dict(),
    'classes': classes,
    'accuracy': val_accs[-1]
}, model_path)
print(f"[✓] Model berhasil disimpan ke: {model_path}")

# Plot Kurva Pelatihan & Confusion Matrix
os.makedirs("static/img", exist_ok=True)

plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(train_accs, label='Train Accuracy', color='#10B981', lw=2)
plt.plot(val_accs, label='Val Accuracy', color='#3B82F6', lw=2)
plt.title('Training & Validation Accuracy', fontsize=12, fontweight='bold')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()
plt.grid(True, alpha=0.3)

plt.subplot(1, 2, 2)
plt.plot(train_losses, label='Train Loss', color='#EF4444', lw=2)
plt.plot(val_losses, label='Val Loss', color='#F59E0B', lw=2)
plt.title('Training & Validation Loss', fontsize=12, fontweight='bold')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('static/img/training_curves.png', dpi=300)
plt.close()

# Plot Confusion Matrix
cm = confusion_matrix(all_labels, all_preds)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=classes, yticklabels=classes)
plt.title('Confusion Matrix Klasifikasi Motif Sasirangan', fontsize=11, fontweight='bold')
plt.xlabel('Prediksi')
plt.ylabel('Aktual')
plt.tight_layout()
plt.savefig('static/img/confusion_matrix.png', dpi=300)
plt.close()
print("[✓] Grafik evaluasi berhasil disimpan ke static/img/")
