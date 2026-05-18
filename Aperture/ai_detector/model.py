"""Detector backbones — ImageNet-pretrained, head replaced for 2-class output."""
from __future__ import annotations

from typing import Literal

import torch.nn as nn
from torchvision import models

ModelName = Literal["efficientnet_b0", "resnet50", "vit_b_16"]


def get_model(name: str, num_classes: int = 2, pretrained: bool = True) -> nn.Module:
    """Return a torchvision backbone with its classifier head replaced.

    For inference (loading saved weights), pass pretrained=False to skip the
    ImageNet download.
    """
    if name == "efficientnet_b0":
        weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.efficientnet_b0(weights=weights)
        in_features = model.classifier[1].in_features  # 1280
        model.classifier[1] = nn.Linear(in_features, num_classes)
        return model

    if name == "resnet50":
        weights = models.ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
        model = models.resnet50(weights=weights)
        in_features = model.fc.in_features  # 2048
        model.fc = nn.Linear(in_features, num_classes)
        return model

    if name == "vit_b_16":
        weights = models.ViT_B_16_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.vit_b_16(weights=weights)
        in_features = model.heads.head.in_features  # 768
        model.heads = nn.Linear(in_features, num_classes)
        return model

    raise ValueError(
        f"Unknown model name: {name!r}. "
        "Supported: 'efficientnet_b0', 'resnet50', 'vit_b_16'."
    )
