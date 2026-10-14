"""ResNet18 전이 학습: 어디까지 얼리고(freeze) 어디부터 학습할지 정한다.

전략          학습하는 부분                      사전학습 가중치
scratch       전체 (무작위 초기화)                없음 — '직접 학습' 비교군
linear_probe  분류기(fc)만                        있음 — Linear Probing
partial       마지막 블록(layer4) + fc            있음
full          전체                                있음 — Fine-tuning

얼린 부분의 BatchNorm은 eval 모드로 고정한다. 사진 몇 장짜리 미니배치 통계로 ImageNet에서 배운
평균·분산을 덮어쓰면 얼렸다는 의미가 없어지기 때문이다.
"""
import torch
from torch import nn
from torchvision import models

STRATEGIES = ("scratch", "linear_probe", "partial", "full")
STRATEGY_LABELS = {"scratch": "직접 학습(무작위 초기화)", "linear_probe": "Linear Probing(fc만)",
                   "partial": "부분 미세 조정(layer4+fc)", "full": "전체 Fine-tuning"}
BLOCKS = ("conv1", "bn1", "layer1", "layer2", "layer3", "layer4", "fc")
TRAINABLE = {"scratch": BLOCKS, "linear_probe": ("fc",), "partial": ("layer4", "fc"), "full": BLOCKS}


class TransferNet(nn.Module):
    def __init__(self, n_classes, strategy="linear_probe", dropout=0.0):
        super().__init__()
        if strategy not in STRATEGIES:
            raise ValueError(strategy)
        weights = None if strategy == "scratch" else models.ResNet18_Weights.IMAGENET1K_V1
        self.net = models.resnet18(weights=weights)
        self.net.fc = nn.Sequential(nn.Dropout(dropout), nn.Linear(self.net.fc.in_features, n_classes))
        self.strategy = strategy
        self.trainable_blocks = TRAINABLE[strategy]
        for name in BLOCKS:
            for p in getattr(self.net, name).parameters():
                p.requires_grad = name in self.trainable_blocks

    def train(self, mode=True):
        super().train(mode)
        if mode:  # 얼린 블록의 BatchNorm은 ImageNet 통계를 그대로 쓴다
            for name in BLOCKS:
                if name not in self.trainable_blocks:
                    getattr(self.net, name).eval()
        return self

    def forward(self, x):
        return self.net(x)

    def features(self, x):
        """fc 직전 512차원 특징."""
        n = self.net
        x = n.maxpool(n.relu(n.bn1(n.conv1(x))))
        x = n.layer4(n.layer3(n.layer2(n.layer1(x))))
        return torch.flatten(n.avgpool(x), 1)

    def param_groups(self, lr_head, lr_backbone):
        """분류기와 몸통에 다른 학습률을 준다 (사전학습 몸통은 작게 움직인다)."""
        head = [p for p in self.net.fc.parameters() if p.requires_grad]
        body = [p for name in BLOCKS if name != "fc" for p in getattr(self.net, name).parameters() if p.requires_grad]
        groups = [{"params": head, "lr": lr_head}]
        if body:
            groups.append({"params": body, "lr": lr_head if self.strategy == "scratch" else lr_backbone})
        return groups


def count_parameters(model):
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    return trainable, total
