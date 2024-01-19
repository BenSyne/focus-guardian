import cv2
import time

def capture_camera_image(filename):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise IOError("Cannot open webcam")

    time.sleep(2)  # Warm-up period for the camera to adjust to lighting conditions

    ret, frame = cap.read()
    if not ret:
        raise IOError("Failed to capture image from camera")

    cv2.imwrite(filename, frame)
    cap.release()