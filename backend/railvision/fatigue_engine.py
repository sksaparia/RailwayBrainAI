"""
RailwayBrain AI - RailVision AI Module
------------------------------------------
Driver fatigue detection using classical computer vision (OpenCV Haar
Cascade classifiers). This runs FOR REAL on any uploaded image/video -
it is not a mock. It does not use the hardware-grade YOLOv9 / thermal
fusion stack described in the actual Railway proposal (that requires
the NVIDIA Jetson + dual camera hardware named in the proposal) -
this module is the software-only, laptop-buildable demo of the same
concept, exactly as scoped in the project's Week 1-2 deliverable.

Pipeline:
1. Detect face (Haar frontal-face cascade)
2. Detect eyes within the face ROI (Haar eye cascade)
3. Track eye-closure across frames (video) or estimate from a single
   frame (image) using eye-region openness heuristics
4. Compute a fatigue score and attention score
5. Classify driver status: SAFE / WARNING / DROWSY
6. Generate a plain-language AI recommendation

Per project spec: no TensorFlow, no MediaPipe dependency required -
OpenCV's bundled Haar cascades are used so the module has zero extra
model downloads and works fully offline.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("railwaybrain.railvision")

FACE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
EYE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"

# Thresholds (tuned for demo purposes; documented, not hidden)
EYE_CLOSURE_WARNING_PCT = 35.0   # % of analysed frames with closed/undetected eyes
EYE_CLOSURE_DROWSY_PCT = 60.0
BLINK_RATE_DROWSY = 2            # very low blink count over a short video can indicate a closed-eye stretch


RISK_LEVEL_LABELS = {
    "SAFE": "Low Risk",
    "WARNING": "Moderate Risk",
    "DROWSY": "High Risk",
    "UNKNOWN": "Unable to Assess",
}


@dataclass
class FatigueResult:
    status: str                     # SAFE | WARNING | DROWSY
    fatigue_score: float            # 0-100 (higher = more fatigued)
    attention_score: float          # 0-100 (higher = more attentive)
    blink_count: int
    eye_closure_pct: float
    faces_detected: int
    frames_analysed: int
    recommendation: str
    fatigue_probability: float = 0.0   # 0.0-1.0, derived directly from fatigue_score
    confidence_score: float = 0.0      # 0-100, how reliable this reading is
    risk_level: str = "Unable to Assess"
    detection_time: str = ""
    annotated_frame: Optional[np.ndarray] = field(default=None, repr=False)


class FatigueEngine:
    """Stateless-per-call engine wrapping the Haar cascade pipeline."""

    def __init__(self) -> None:
        self.face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
        self.eye_cascade = cv2.CascadeClassifier(EYE_CASCADE_PATH)
        if self.face_cascade.empty() or self.eye_cascade.empty():
            raise RuntimeError(
                "OpenCV Haar cascade XML files could not be loaded. "
                "Verify the opencv-python installation."
            )

    # ------------------------------------------------------------------ #
    # Core per-frame detection
    # ------------------------------------------------------------------ #
    def analyse_frame(self, frame_bgr: np.ndarray) -> tuple[int, int, int]:
        """
        Returns (faces_found, eyes_found_total, eyes_expected_total)
        eyes_expected_total = 2 * faces_found (used to estimate closure %).
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )

        eyes_found_total = 0
        for (x, y, w, h) in faces:
            face_roi = gray[y:y + int(h * 0.6), x:x + w]  # upper 60% of face = eye region
            eyes = self.eye_cascade.detectMultiScale(
                face_roi, scaleFactor=1.1, minNeighbors=6, minSize=(20, 20)
            )
            eyes_found_total += min(len(eyes), 2)  # cap at 2 per face

            # annotate in-place for visual feedback
            cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), (0, 200, 255), 2)
            for (ex, ey, ew, eh) in eyes[:2]:
                cv2.rectangle(
                    frame_bgr, (x + ex, y + ey), (x + ex + ew, y + ey + eh), (0, 255, 120), 2
                )

        return len(faces), eyes_found_total, len(faces) * 2

    # ------------------------------------------------------------------ #
    # Image analysis (single frame)
    # ------------------------------------------------------------------ #
    def analyse_image(self, frame_bgr: np.ndarray) -> FatigueResult:
        faces, eyes_found, eyes_expected = self.analyse_frame(frame_bgr)

        if faces == 0:
            return self._no_face_result(frame_bgr)

        closure_pct = 100.0 * (1 - (eyes_found / max(eyes_expected, 1)))
        fatigue_score = min(100.0, closure_pct * 1.15)
        attention_score = max(0.0, 100.0 - fatigue_score)

        status, recommendation = self._classify(closure_pct, blink_count=1 if eyes_found else 0,
                                                  frames=1)
        confidence = self._confidence(faces, eyes_found, eyes_expected, frames_analysed=1, max_frames=1)
        return FatigueResult(
            status=status,
            fatigue_score=round(fatigue_score, 1),
            attention_score=round(attention_score, 1),
            blink_count=1 if eyes_found >= eyes_expected else 0,
            eye_closure_pct=round(closure_pct, 1),
            faces_detected=faces,
            frames_analysed=1,
            recommendation=recommendation,
            fatigue_probability=round(fatigue_score / 100.0, 2),
            confidence_score=confidence,
            risk_level=RISK_LEVEL_LABELS.get(status, "Unable to Assess"),
            detection_time=datetime.now().strftime("%d %b %Y, %H:%M:%S"),
            annotated_frame=frame_bgr,
        )

    # ------------------------------------------------------------------ #
    # Video analysis (multi frame, sampled)
    # ------------------------------------------------------------------ #
    def analyse_video(self, video_path: str, sample_every_n_frames: int = 5,
                       max_frames: int = 150) -> FatigueResult:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        frame_idx = 0
        analysed = 0
        total_faces = 0
        total_eyes_found = 0
        total_eyes_expected = 0
        blink_events = 0
        prev_eyes_open = True
        last_annotated = None

        while analysed < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            if frame_idx % sample_every_n_frames != 0:
                continue

            faces, eyes_found, eyes_expected = self.analyse_frame(frame)
            analysed += 1
            total_faces += faces
            total_eyes_found += eyes_found
            total_eyes_expected += eyes_expected
            last_annotated = frame

            eyes_open_now = eyes_found >= max(eyes_expected, 1) * 0.5
            if prev_eyes_open and not eyes_open_now:
                blink_events += 1
            prev_eyes_open = eyes_open_now

        cap.release()

        if analysed == 0 or total_faces == 0:
            return self._no_face_result(last_annotated)

        closure_pct = 100.0 * (1 - (total_eyes_found / max(total_eyes_expected, 1)))
        fatigue_score = min(100.0, closure_pct * 1.1 + (5 if blink_events <= BLINK_RATE_DROWSY else 0))
        attention_score = max(0.0, 100.0 - fatigue_score)

        status, recommendation = self._classify(closure_pct, blink_events, analysed)
        confidence = self._confidence(total_faces, total_eyes_found, total_eyes_expected,
                                       frames_analysed=analysed, max_frames=max_frames)

        return FatigueResult(
            status=status,
            fatigue_score=round(fatigue_score, 1),
            attention_score=round(attention_score, 1),
            blink_count=blink_events,
            eye_closure_pct=round(closure_pct, 1),
            faces_detected=total_faces,
            frames_analysed=analysed,
            recommendation=recommendation,
            fatigue_probability=round(fatigue_score / 100.0, 2),
            confidence_score=confidence,
            risk_level=RISK_LEVEL_LABELS.get(status, "Unable to Assess"),
            detection_time=datetime.now().strftime("%d %b %Y, %H:%M:%S"),
            annotated_frame=last_annotated,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _classify(self, closure_pct: float, blink_count: int, frames: int) -> tuple[str, str]:
        if closure_pct >= EYE_CLOSURE_DROWSY_PCT:
            return "DROWSY", (
                "CRITICAL: Sustained eye closure detected. Trigger cab alarm immediately, "
                "instruct driver to acknowledge, and if no response within threshold escalate "
                "to nearest station for emergency stop protocol (per RailVision AI proposal "
                "IC0000000170: false-negative-zero design, undetected signal defaults to Red)."
            )
        if closure_pct >= EYE_CLOSURE_WARNING_PCT:
            return "WARNING", (
                "Fatigue indicators rising. Issue audible cab alert, recommend driver take a "
                "5-10 minute rest at next crew-change point, and flag for divisional roster review."
            )
        return "SAFE", (
            "Driver alertness within normal range. Continue standard monitoring interval."
        )

    def _confidence(self, faces: int, eyes_found: int, eyes_expected: int,
                     frames_analysed: int, max_frames: int) -> float:
        """
        Honest, derived confidence score (0-100) — reflects how much
        signal the detector actually had, not a black-box AI certainty.
        Rewards: a face being found, both eyes being found consistently,
        and (for video) more sampled frames giving a steadier reading.
        """
        if faces == 0:
            return 0.0
        face_component = 45.0  # a face was found at all
        eye_component = 35.0 * (min(eyes_found, eyes_expected) / max(eyes_expected, 1))
        sample_component = 20.0 * min(frames_analysed / max(max_frames, 1), 1.0) if max_frames > 1 else 20.0
        return round(min(100.0, face_component + eye_component + sample_component), 1)

    def _no_face_result(self, frame: Optional[np.ndarray]) -> FatigueResult:
        return FatigueResult(
            status="UNKNOWN",
            fatigue_score=0.0,
            attention_score=0.0,
            blink_count=0,
            eye_closure_pct=0.0,
            faces_detected=0,
            frames_analysed=0,
            recommendation=(
                "No driver face detected in frame(s). Check camera alignment/lighting - "
                "in production this maps to the RailVision hardware's IR thermal fallback."
            ),
            fatigue_probability=0.0,
            confidence_score=0.0,
            risk_level=RISK_LEVEL_LABELS.get("UNKNOWN", "Unable to Assess"),
            detection_time=datetime.now().strftime("%d %b %Y, %H:%M:%S"),
            annotated_frame=frame,
        )


def save_screenshot(frame_bgr: np.ndarray, out_dir: str) -> str:
    """Save an annotated frame as a timestamped JPEG and return the path."""
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(out_dir, f"fatigue_event_{ts}.jpg")
    cv2.imwrite(path, frame_bgr)
    return path
