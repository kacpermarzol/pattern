import torch
from PIL import Image
from torchvision import transforms
from torchsummary import summary
import numpy as np
import timm
import os
import torch.nn as nn
from tqdm import tqdm

import matplotlib.pyplot as plt
from torchvision import datasets
import matplotlib.pyplot as plt

from vit_rollout import VITAttentionRollout
from torch.utils.data import DataLoader
import resnet
import imagenet
import newmodel
from utils import create_teacher, create_student


if __name__ == '__main__':
    if torch.cuda.is_available():
        device = torch.device('cuda')
        torch.set_default_tensor_type('torch.cuda.FloatTensor')
    else:
        device = torch.device('cpu')
    print(device)

    model_teacher = create_teacher()
    model_teacher.to(device)

    model_student = create_student()
    model_student = model_student.to(device)

    model = newmodel.NewModel(model_teacher, model_student)
    model = model.to(device)

    transform = transforms.Compose([
        transforms.Resize((224,224)),
        # transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])


    # on your device
    data_folder = './data/ILSVRC2012_img_val'
    imagenet_data = imagenet.ImageNet(data_folder, transform)

    # on server
    # data_folder = '/shared/sets/datasets/vision/ImageNet'
    # imagenet_data = torchvision.datasets.ImageNet(data_folder, split='val', transform=transform)

    train_dataloader = DataLoader(imagenet_data, batch_size=1, shuffle=True, generator=torch.Generator(device=device))

    optimizer = torch.optim.Adam(model_student.parameters(), lr=0.0001)
    criterion = torch.nn.MSELoss().to(device)

    losses= []
    steps = []

    for epoch in range(10):
        print("EPOCH: ", epoch+1)
        for i, (image, _ ) in tqdm(enumerate(train_dataloader), total=len(train_dataloader)):
            image = image.to(device)
            optimizer.zero_grad()
            output, target = model(image)
            output = output.reshape(14,14)
            loss = criterion(target, output)
            loss.backward()
            optimizer.step()
            if (i+1) % 500 == 0:
                losses.append(loss.item())
                steps.append(epoch * 50000 + i+1)
            if (i+1) % 10000 == 0:
                print(f"STEP: {i+1}, loss: {loss.item()}")
                fig, axes = plt.subplots(1, 3, figsize=(10, 5))
                axes[0].imshow(image[0].permute(1, 2, 0).cpu().detach())
                axes[1].imshow(target.cpu())
                axes[2].imshow(output.cpu().detach())
                plt.savefig(f"train{epoch}_{i}.png")
                plt.close(fig)

        plt.plot(steps, losses)
        plt.title(f'Loss over time (after {epoch+1} epoch)')
        plt.xlabel('Step')
        plt.ylabel('Loss')
        plt.savefig(f'Loss{epoch+1}.png')
        plt.close()
        torch.save(model_student.state_dict(), 'model_state.pth')


    # plt.plot(steps, losses)
    # plt.title('Loss over time')
    # plt.xlabel('Step')
    # plt.ylabel('Loss')
    # plt.savefig("Loss.png")
    # plt.close()


