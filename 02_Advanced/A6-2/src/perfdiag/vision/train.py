"""전이 학습 학습·평가 루프.

- 입력 해상도 160px: CPU에서 224px보다 약 2배 빠르고, 이 데이터에서는 정확도 차이가 작다.
- 학습은 정해진 epoch만큼 끝까지 돌려 과적합 구간까지 곡선에 남긴다. 최종 가중치는 Validation 손실이
  가장 낮았던 epoch의 것으로 되돌린다 (Test는 보지 않는다).
- 매 epoch Train 전체를 증강 없이 eval 모드로 다시 평가해 Validation과 같은 조건의 Train 손실을 얻는다.
"""
import copy
import time
from dataclasses import asdict, dataclass

import numpy as np
import torch
import torch.nn.functional as F
from torchvision.transforms import v2

from ..common import set_seed
from ..diagnosis import diagnose_classification
from .models import TransferNet, count_parameters

IMAGE_SIZE = 160
MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)   # ImageNet 정규화


def eval_transform(size=IMAGE_SIZE):
    return v2.Compose([v2.Resize(round(size / 0.875), antialias=True), v2.CenterCrop(size),
                       v2.ToDtype(torch.float32, scale=True), v2.Normalize(MEAN, STD)])


AUGMENTATIONS = {
    # 기본: 위치·크기·좌우 변화
    "basic": lambda size: [v2.RandomResizedCrop(size, scale=(0.5, 1.0), antialias=True), v2.RandomHorizontalFlip()],
    # 오차 분석 후 처방: 조명·색 변화와 가림에 강하게
    "photometric": lambda size: [v2.RandomResizedCrop(size, scale=(0.35, 1.0), antialias=True),
                                 v2.RandomHorizontalFlip(), v2.RandomRotation(20),
                                 v2.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.3, hue=0.02)],
}


def train_transform(name="basic", size=IMAGE_SIZE):
    return v2.Compose([*AUGMENTATIONS[name](size), v2.ToDtype(torch.float32, scale=True), v2.Normalize(MEAN, STD)])


def to_tensor(images):
    """(n, H, W, 3) uint8 → (n, 3, H, W) uint8 텐서."""
    return torch.from_numpy(np.array(images, copy=True)).permute(0, 3, 1, 2)


@dataclass
class VisionConfig:
    strategy: str = "linear_probe"
    epochs: int = 25
    batch_size: int = 16
    lr_head: float = 1e-3
    lr_backbone: float = 1e-4
    weight_decay: float = 1e-4
    dropout: float = 0.0
    augmentation: str = "basic"
    image_size: int = IMAGE_SIZE
    seed: int = 0


@torch.no_grad()
def predict_proba(model, images, size=IMAGE_SIZE, batch_size=64):
    model.eval()
    transform = eval_transform(size)
    x = to_tensor(images)
    out = [F.softmax(model(transform(x[i:i + batch_size])), dim=1) for i in range(0, len(x), batch_size)]
    return torch.cat(out).numpy()


def scores(proba, targets):
    eps = 1e-12
    loss = float(-np.mean(np.log(proba[np.arange(len(targets)), targets] + eps)))
    error = float(np.mean(proba.argmax(1) != targets))
    return loss, error


def fit(train_set, validation_set, cfg, n_classes, log=print):
    set_seed(cfg.seed)
    model = TransferNet(n_classes, cfg.strategy, cfg.dropout)
    opt = torch.optim.AdamW(model.param_groups(cfg.lr_head, cfg.lr_backbone), weight_decay=cfg.weight_decay)
    transform = train_transform(cfg.augmentation, cfg.image_size)
    x_all, y_all = to_tensor(train_set.images), torch.as_tensor(train_set.targets)
    generator = torch.Generator().manual_seed(cfg.seed)
    history = {key: [] for key in ("train_loss", "validation_loss", "train_error", "validation_error")}
    best = (float("inf"), 0, None)
    start = time.perf_counter()
    for epoch in range(1, cfg.epochs + 1):
        model.train()
        order = torch.randperm(len(x_all), generator=generator)
        for i in range(0, len(order), cfg.batch_size):
            batch = order[i:i + cfg.batch_size]
            # 이미지마다 다른 무작위 증강을 적용한다
            x = torch.stack([transform(img) for img in x_all[batch]])
            loss = F.cross_entropy(model(x), y_all[batch])
            opt.zero_grad()
            loss.backward()
            opt.step()
        train_loss, train_error = scores(predict_proba(model, train_set.images, cfg.image_size), train_set.targets)
        val_loss, val_error = scores(predict_proba(model, validation_set.images, cfg.image_size),
                                     validation_set.targets)
        for key, value in zip(history, (train_loss, val_loss, train_error, val_error)):
            history[key].append(value)
        if val_loss < best[0]:
            best = (val_loss, epoch, copy.deepcopy(model.state_dict()))
        log(f"    epoch {epoch:>2}  Train loss {train_loss:.3f} err {train_error:.3f} | "
            f"Validation loss {val_loss:.3f} err {val_error:.3f}")
    model.load_state_dict(best[2])
    history.update(best_epoch=best[1], seconds=time.perf_counter() - start)
    return model, history


def run(train_set, validation_set, test_set, cfg, n_classes, log=print):
    model, history = fit(train_set, validation_set, cfg, n_classes, log)
    result = {"config": asdict(cfg), "history": history, "n_train": len(train_set.targets)}
    result["trainable_parameters"], result["total_parameters"] = count_parameters(model)
    for split, data in (("train", train_set), ("validation", validation_set), ("test", test_set)):
        proba = predict_proba(model, data.images, cfg.image_size)
        loss, error = scores(proba, data.targets)
        result[split] = {"loss": loss, "error": error, "accuracy": 1 - error}
        if split == "test":
            result["test_proba"] = proba
    diagnosis = diagnose_classification(result["train"]["error"], result["validation"]["error"])
    result["diagnosis"] = diagnosis.to_dict()
    return model, result
