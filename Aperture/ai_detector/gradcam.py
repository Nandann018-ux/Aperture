"""Grad-CAM (CNNs) and attention rollout (ViT) interpretability.

Public entry point: ``compute_gradcam(model, image_tensor, target_class=1)``.
The function dispatches based on the model's architecture:

  - EfficientNet / MobileNet variants (have ``model.features``) -> Grad-CAM
    on the last conv block.
  - ResNet variants (have ``model.layer4``) -> Grad-CAM on ``layer4[-1]``.
  - Vision Transformer (have ``model.encoder.layers``) -> attention rollout.

Returns a 2D ``np.ndarray`` of shape (H, W) (matching the input spatial size),
normalized to [0, 1].
"""
from __future__ import annotations

import cv2
import numpy as np
import torch
import torch.nn as nn


def _normalize(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float32)
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-12:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def _gradcam_cnn(
    model: nn.Module,
    image_tensor: torch.Tensor,
    target_layer: nn.Module,
    target_class: int,
) -> np.ndarray:
    from pytorch_grad_cam import GradCAM
    from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

    cam = GradCAM(model=model, target_layers=[target_layer])
    grayscale = cam(
        input_tensor=image_tensor,
        targets=[ClassifierOutputTarget(int(target_class))],
    )
    return _normalize(grayscale[0])


def _attention_rollout(
    model: nn.Module,
    image_tensor: torch.Tensor,
    discard_ratio: float = 0.0,
) -> np.ndarray:
    """Abnar & Zuidema attention rollout for torchvision ViT.

    Captures attention weights from each ``nn.MultiheadAttention`` in the
    encoder by re-invoking it with ``need_weights=True`` inside a forward
    hook, then composes them with residual identity to get the CLS-token
    importance map, reshaped to a 14x14 grid and upsampled to the input
    size.
    """
    attentions: list[torch.Tensor] = []
    hooks = []

    def make_hook():
        def hook(module, inputs, output):
            q = inputs[0]
            with torch.no_grad():
                _, attn = module(q, q, q, need_weights=True, average_attn_weights=True)
            attentions.append(attn.detach().cpu())
        return hook

    for block in model.encoder.layers:  # type: ignore[union-attr]
        hooks.append(block.self_attention.register_forward_hook(make_hook()))

    try:
        with torch.no_grad():
            _ = model(image_tensor)
    finally:
        for h in hooks:
            h.remove()

    if not attentions:
        raise RuntimeError("No attention layers captured for rollout.")

    n_tokens = attentions[0].size(-1)
    result = torch.eye(n_tokens)
    for attn in attentions:
        a = attn[0]  # (N, N)
        if discard_ratio > 0:
            flat = a.view(-1).clone()
            k = int(flat.numel() * discard_ratio)
            if k > 0:
                idx = flat.topk(k, largest=False).indices
                flat[idx] = 0
                a = flat.view_as(a)
        a = a + torch.eye(a.size(0))
        a = a / a.sum(dim=-1, keepdim=True)
        result = a @ result

    mask = result[0, 1:]  # CLS row, drop CLS->CLS
    grid = int(round(mask.numel() ** 0.5))
    if grid * grid != mask.numel():
        raise RuntimeError(
            f"Token count {mask.numel()} is not a perfect square; "
            "this rollout assumes a square patch grid."
        )
    heatmap = mask.view(grid, grid).numpy()
    h, w = image_tensor.shape[-2:]
    heatmap = cv2.resize(heatmap, (w, h), interpolation=cv2.INTER_CUBIC)
    return _normalize(heatmap)


def compute_gradcam(
    model: nn.Module,
    image_tensor: torch.Tensor,
    target_class: int = 1,
) -> np.ndarray:
    """Return a [0, 1]-normalized heatmap aligned to the input image.

    ``image_tensor`` may be (C, H, W) or (1, C, H, W); we batch as needed.
    """
    if image_tensor.dim() == 3:
        image_tensor = image_tensor.unsqueeze(0)
    elif image_tensor.dim() != 4 or image_tensor.size(0) != 1:
        raise ValueError(
            f"Expected single-image tensor (C,H,W) or (1,C,H,W); got {tuple(image_tensor.shape)}"
        )

    # ViT: torchvision packages encoder blocks under model.encoder.layers
    if hasattr(model, "encoder") and hasattr(model.encoder, "layers"):
        return _attention_rollout(model, image_tensor)

    if hasattr(model, "features"):
        # EfficientNet / MobileNet style — last conv block
        return _gradcam_cnn(model, image_tensor, model.features[-1], target_class)  # type: ignore[index,arg-type]

    if hasattr(model, "layer4"):
        # ResNet style — final residual block
        return _gradcam_cnn(model, image_tensor, model.layer4[-1], target_class)  # type: ignore[index,arg-type]

    raise ValueError(
        "Unsupported model architecture for compute_gradcam: "
        f"{type(model).__name__}"
    )
