import os
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"

import cv2
import mediapipe as mp

img = cv2.imread("assets/smoke/hand_crop_test.jpg")
if img is None:
    raise RuntimeError("image load failed")

rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

print("image shape:", img.shape)
print("mediapipe version:", mp.__version__)
print("has solutions:", hasattr(mp, "solutions"))

hands = mp.solutions.hands.Hands(
    static_image_mode=True,
    max_num_hands=1,
    min_detection_confidence=0.3,
)

result = hands.process(rgb)

print("landmarks:", result.multi_hand_landmarks)
print("handedness:", result.multi_handedness)

hands.close()
