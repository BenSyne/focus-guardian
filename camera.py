import cv2
import time
import logging
import threading

def capture_camera_image(filename, timeout=3.0):
    """Capture an image from the camera with a timeout."""
    logging.info(f"Initializing camera capture for {filename}")
    
    # Use a flag to track if camera capture succeeded
    capture_success = False
    capture_error = None
    
    def _capture_with_timeout():
        nonlocal capture_success, capture_error
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                capture_error = "Cannot open webcam"
                logging.error(capture_error)
                return
                
            logging.info("Camera opened, warming up...")
            # Reduce warm-up time to 0.5 seconds (from 2)
            time.sleep(0.5)  
            
            logging.info("Reading frame from camera...")
            ret, frame = cap.read()
            if not ret:
                capture_error = "Failed to capture image from camera"
                logging.error(capture_error)
                cap.release()
                return
                
            logging.info(f"Saving camera image to {filename}")
            cv2.imwrite(filename, frame)
            logging.info("Camera image saved, releasing camera")
            cap.release()
            capture_success = True
            logging.info("Camera released")
        except Exception as e:
            capture_error = str(e)
            logging.error(f"Error in camera capture: {capture_error}")
            
    # Start capture in a separate thread
    capture_thread = threading.Thread(target=_capture_with_timeout)
    capture_thread.daemon = True  # Don't let this thread block program exit
    capture_thread.start()
    
    # Wait for the thread to finish or timeout
    capture_thread.join(timeout)
    
    if capture_thread.is_alive():
        # Thread is still running after timeout
        logging.error(f"Camera capture timed out after {timeout} seconds")
        return False
        
    if not capture_success:
        logging.error(f"Camera capture failed: {capture_error or 'Unknown error'}")
        return False
        
    return capture_success