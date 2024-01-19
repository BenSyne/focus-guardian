import cv2

def capture_camera_image(filename):
    """
    Function to capture an image from the camera.
    """
    cap = cv2.VideoCapture(0)

    # Check if the webcam is opened correctly
    if not cap.isOpened():
        raise IOError("Cannot open webcam")

    ret, frame = cap.read()
    cv2.imwrite(filename, frame)
    cap.release()