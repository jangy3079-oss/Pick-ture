"""Face detection/blendshapes (mediapipe) + aesthetic score & zero-shot tags (CLIP).

Model weight sources (downloaded once, cached under worktree-agent1-backend/models/
and the default HF/torch caches — CONTRACT.md 6-1 recommends pre-warming these
before entering the room):
- models/blaze_face_short_range.tflite: mediapipe FaceDetector (face_count)
- models/face_landmarker.task: mediapipe FaceLandmarker w/ blendshapes
  (eyes_open / smiling for portrait_bonus)
- shunk031/aesthetics-predictor-v2-sac-logos-ava1-l14-linearMSE (HF hub, via
  simple-aesthetics-predictor + transformers CLIP): aesthetic_score
- open_clip ViT-B-32 (openai pretrained): zero-shot category tags

Assumption: CONTRACT.md doesn't pin exact model variants for the aesthetics
predictor or the CLIP backbone. We use the reference checkpoint from the
simple-aesthetics-predictor README (linear-MSE head on CLIP ViT-L/14) and
open_clip's standard ViT-B-32/openai for zero-shot tags (small, fast, widely
used baseline) — documented here rather than asking, per CONTRACT.md 6-2.
"""
from __future__ import annotations

import threading
from pathlib import Path

import mediapipe as mp
import open_clip
import torch
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision as mp_vision
from PIL import Image
from transformers import CLIPProcessor

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
AESTHETIC_MODEL_ID = "shunk031/aesthetics-predictor-v2-sac-logos-ava1-l14-linearMSE"

ZERO_SHOT_LABELS = ["selfie", "food", "landscape"]
ZERO_SHOT_PROMPTS = [
    "a selfie photo of a person",
    "a photo of food",
    "a landscape or scenery photo",
]

MAX_FACES = 20

_lock = threading.Lock()
_state: dict = {}


def _load_once() -> dict:
    with _lock:
        if _state:
            return _state

        # Assumption: force CPU delegate explicitly. mediapipe's default delegate
        # tries GPU (Metal on macOS) and hard-crashes the process with
        # "Check failed: service_ Service is unavailable." on this machine —
        # CPU delegate is the documented fallback and is fine at this data scale.
        face_detector = mp_vision.FaceDetector.create_from_options(
            mp_vision.FaceDetectorOptions(
                base_options=BaseOptions(
                    model_asset_path=str(MODELS_DIR / "blaze_face_short_range.tflite"),
                    delegate=BaseOptions.Delegate.CPU,
                ),
                min_detection_confidence=0.5,
            )
        )
        face_landmarker = mp_vision.FaceLandmarker.create_from_options(
            mp_vision.FaceLandmarkerOptions(
                base_options=BaseOptions(
                    model_asset_path=str(MODELS_DIR / "face_landmarker.task"),
                    delegate=BaseOptions.Delegate.CPU,
                ),
                num_faces=MAX_FACES,
                output_face_blendshapes=True,
            )
        )

        from aesthetics_predictor import AestheticsPredictorV2Linear

        aesthetic_model = AestheticsPredictorV2Linear.from_pretrained(AESTHETIC_MODEL_ID)
        aesthetic_model.eval()
        aesthetic_processor = CLIPProcessor.from_pretrained(AESTHETIC_MODEL_ID)

        # "-quickgelu" variant matches the activation function the "openai"
        # pretrained weights were actually trained with (avoids a silent
        # quick_gelu config mismatch warning/degradation from open_clip).
        clip_model, _, clip_preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32-quickgelu", pretrained="openai"
        )
        clip_model.eval()
        clip_tokenizer = open_clip.get_tokenizer("ViT-B-32-quickgelu")
        with torch.no_grad():
            text_tokens = clip_tokenizer(ZERO_SHOT_PROMPTS)
            text_features = clip_model.encode_text(text_tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)

        _state.update(
            face_detector=face_detector,
            face_landmarker=face_landmarker,
            aesthetic_model=aesthetic_model,
            aesthetic_processor=aesthetic_processor,
            clip_model=clip_model,
            clip_preprocess=clip_preprocess,
            clip_text_features=text_features,
        )
        return _state


def _blendshape_score(blendshapes: list, name: str) -> float:
    for category in blendshapes:
        if category.category_name == name:
            return category.score
    return 0.0


def analyze_faces(image_path: Path) -> tuple[int, dict | None]:
    """Returns (face_count, portrait_bonus_dict_or_None).

    portrait_bonus is computed from the blendshapes of the most prominent
    (first-detected) face when face_count >= 1, else None.
    """
    state = _load_once()
    mp_image = mp.Image.create_from_file(str(image_path))

    detection_result = state["face_detector"].detect(mp_image)
    face_count = len(detection_result.detections)
    if face_count == 0:
        return 0, None

    landmarker_result = state["face_landmarker"].detect(mp_image)
    if not landmarker_result.face_blendshapes:
        return face_count, {"eyes_open": True, "smiling": False, "adjustment": 0.0}

    blendshapes = landmarker_result.face_blendshapes[0]
    eye_blink_left = _blendshape_score(blendshapes, "eyeBlinkLeft")
    eye_blink_right = _blendshape_score(blendshapes, "eyeBlinkRight")
    smile_left = _blendshape_score(blendshapes, "mouthSmileLeft")
    smile_right = _blendshape_score(blendshapes, "mouthSmileRight")

    eyes_open = (eye_blink_left + eye_blink_right) / 2 < 0.5
    smiling = (smile_left + smile_right) / 2 > 0.5

    adjustment = 0.0
    if eyes_open:
        adjustment += 0.5
    else:
        adjustment -= 1.0
    if smiling:
        adjustment += 0.5

    return face_count, {"eyes_open": eyes_open, "smiling": smiling, "adjustment": adjustment}


def detect_face_crops(image_path: Path) -> list[Image.Image]:
    """Returns cropped PIL images for each detected face (used by P2 face
    clustering — "가장 많이 찍힌 사람"). Reuses the same FaceDetector as
    analyze_faces, just also returns crops instead of only the count."""
    state = _load_once()
    mp_image = mp.Image.create_from_file(str(image_path))
    detection_result = state["face_detector"].detect(mp_image)

    full_image = Image.open(image_path).convert("RGB")
    crops = []
    for detection in detection_result.detections:
        box = detection.bounding_box
        left, top = max(box.origin_x, 0), max(box.origin_y, 0)
        right = min(box.origin_x + box.width, full_image.width)
        bottom = min(box.origin_y + box.height, full_image.height)
        if right > left and bottom > top:
            crops.append(full_image.crop((left, top, right, bottom)))
    return crops


def embed_face_crop(face_crop: Image.Image) -> torch.Tensor:
    """CLIP image embedding of a cropped face, used as a lightweight identity
    proxy for face clustering (no dedicated face-recognition model is in the
    pre-approved package list — CONTRACT.md 6-1 — so we reuse the CLIP model
    already loaded for zero_shot_tags rather than adding a new dependency
    mid-loop)."""
    state = _load_once()
    tensor = state["clip_preprocess"](face_crop).unsqueeze(0)
    with torch.no_grad():
        features = state["clip_model"].encode_image(tensor)
        features /= features.norm(dim=-1, keepdim=True)
    return features.squeeze(0)


def aesthetic_score(image_path: Path) -> float:
    state = _load_once()
    image = Image.open(image_path).convert("RGB")
    inputs = state["aesthetic_processor"](images=image, return_tensors="pt")
    with torch.no_grad():
        output = state["aesthetic_model"](**inputs)
    return float(output.logits.squeeze().item())


def zero_shot_tags(image_path: Path) -> dict[str, float]:
    state = _load_once()
    image = Image.open(image_path).convert("RGB")
    image_tensor = state["clip_preprocess"](image).unsqueeze(0)
    with torch.no_grad():
        image_features = state["clip_model"].encode_image(image_tensor)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        similarity = (100.0 * image_features @ state["clip_text_features"].T).softmax(dim=-1)
    scores = similarity.squeeze(0).tolist()
    return {label: round(score, 4) for label, score in zip(ZERO_SHOT_LABELS, scores)}
