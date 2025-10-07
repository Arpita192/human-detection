import cv2
import base64
import sys
import atexit
import csv
from datetime import datetime
import os
from ultralytics import YOLO
import time
import select # NEW: Import the select module

# --- State Variables ---
start_time = datetime.now()
max_humans_in_frame = 0
log_file_path = 'log_report.csv'

def log_session():
    """
    This function is called automatically when the script exits.
    It calculates the session duration and logs the details to a CSV file.
    """
    global max_humans_in_frame, start_time, log_file_path

    end_time = datetime.now()
    duration = end_time - start_time
    duration_str = str(duration).split('.')[0]

    # Don't log very short sessions with no detections
    if duration.total_seconds() < 2 and max_humans_in_frame == 0:
        return

    log_data = {
        'Date': start_time.strftime('%Y-%m-%d'),
        'Time': start_time.strftime('%H:%M:%S'),
        'Humans Detected': max_humans_in_frame,
        'Duration': duration_str
    }

    file_exists = os.path.isfile(log_file_path)
    try:
        with open(log_file_path, 'a', newline='') as csvfile:
            fieldnames = ['Date', 'Time', 'Humans Detected', 'Duration']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(log_data)
    except IOError as e:
        print(f"Error writing to log file: {e}", file=sys.stderr)

# Register the log_session function to be called on script exit
atexit.register(log_session)

def find_camera_index():
    """
    Automatically find a working camera by testing indices 0 through 4.
    Uses CAP_DSHOW for better Windows compatibility.
    """
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            print(f"Found working camera at index: {i}", file=sys.stderr)
            cap.release()
            return i
    return -1

def main():
    global max_humans_in_frame

    print("Python script started. Finding camera...", file=sys.stderr)
    sys.stderr.flush()

    camera_index = find_camera_index()
    if camera_index == -1:
        sys.stderr.write("Error: No working webcam found.\n")
        sys.stderr.flush()
        return

    try:
        print("Initializing YOLO model...", file=sys.stderr)
        sys.stderr.flush()
        model = YOLO('yolov8n.pt')
        print("YOLO model initialized. Opening camera...", file=sys.stderr)
        sys.stderr.flush()
        
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            sys.stderr.write(f"Error: Could not open camera at index {camera_index}.\n")
            sys.stderr.flush()
            return

        print("Camera opened. Starting detection stream.", file=sys.stderr)
        sys.stderr.flush()

        while True:
            # --- MODIFIED LOGIC ---
            # Check if the main process sent a 'QUIT' command without blocking
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                line = sys.stdin.readline()
                if 'QUIT' in line:
                    print("Received QUIT command. Exiting gracefully.", file=sys.stderr)
                    break # Exit the loop to allow atexit to run

            success, frame = cap.read()
            if not success:
                break

            results = model(frame, classes=0, conf=0.5, verbose=False)
            num_humans = len(results[0].boxes)
            if num_humans > max_humans_in_frame:
                max_humans_in_frame = num_humans

            annotated_frame = results[0].plot()
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            b64_string = base64.b64encode(buffer).decode('utf-8')
            
            # Send the frame data followed by a newline character
            print(b64_string)
            sys.stdout.flush()

            time.sleep(0.04) # 25 FPS cap for smooth video

    except Exception as e:
        sys.stderr.write(f"An error occurred: {e}\n")
        sys.stderr.flush()
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()

if __name__ == '__main__':
    main()

import cv2
import base64
import sys
import atexit
import csv
from datetime import datetime
import os
from ultralytics import YOLO
import time
import threading # NEW: Replaced 'select' with 'threading' for robust input handling

# --- State Variables ---
start_time = datetime.now()
max_humans_in_frame = 0
log_file_path = 'log_report.csv'
exit_signal = threading.Event() # A signal to safely exit the main loop

def log_session():
    """
    This function is called automatically when the script exits.
    It calculates the session duration and logs the details to a CSV file.
    """
    global max_humans_in_frame, start_time, log_file_path

    end_time = datetime.now()
    duration = end_time - start_time
    duration_str = str(duration).split('.')[0]

    if duration.total_seconds() < 2 and max_humans_in_frame == 0:
        return

    log_data = {
        'Date': start_time.strftime('%Y-%m-%d'),
        'Time': start_time.strftime('%H:%M:%S'),
        'Humans Detected': max_humans_in_frame,
        'Duration': duration_str
    }

    file_exists = os.path.isfile(log_file_path)
    try:
        with open(log_file_path, 'a', newline='') as csvfile:
            fieldnames = ['Date', 'Time', 'Humans Detected', 'Duration']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(log_data)
    except IOError as e:
        print(f"Error writing to log file: {e}", file=sys.stderr)

# Register the log_session function to be called on script exit
atexit.register(log_session)

def find_camera_index():
    """
    Automatically find a working camera by testing indices 0 through 4.
    Uses CAP_DSHOW for better Windows compatibility.
    """
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            print(f"Found working camera at index: {i}", file=sys.stderr)
            cap.release()
            return i
    return -1

def watch_for_quit_command():
    """
    Runs in a separate thread and listens for a 'QUIT' command on stdin.
    When received, it sets the global exit_signal event.
    """
    for line in sys.stdin:
        if 'QUIT' in line:
            exit_signal.set()
            break

def main():
    global max_humans_in_frame

    print("Python script started. Finding camera...", file=sys.stderr)
    sys.stderr.flush()

    camera_index = find_camera_index()
    if camera_index == -1:
        sys.stderr.write("Error: No working webcam found.\n")
        sys.stderr.flush()
        return

    try:
        # Start the thread that listens for the quit command from the main process
        quit_thread = threading.Thread(target=watch_for_quit_command)
        quit_thread.daemon = True  # Allows main program to exit even if this thread is running
        quit_thread.start()

        print("Initializing YOLO model...", file=sys.stderr)
        sys.stderr.flush()
        model = YOLO('yolov8n.pt')
        print("YOLO model initialized. Opening camera...", file=sys.stderr)
        sys.stderr.flush()
        
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            sys.stderr.write(f"Error: Could not open camera at index {camera_index}.\n")
            sys.stderr.flush()
            return

        print("Camera opened. Starting detection stream.", file=sys.stderr)
        sys.stderr.flush()

        # The main loop now checks the exit_signal event instead of reading stdin directly.
        while not exit_signal.is_set():
            success, frame = cap.read()
            if not success:
                break

            results = model(frame, classes=0, conf=0.5, verbose=False)
            num_humans = len(results[0].boxes)
            if num_humans > max_humans_in_frame:
                max_humans_in_frame = num_humans

            annotated_frame = results[0].plot()
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            b64_string = base64.b64encode(buffer).decode('utf-8')
            
            print(b64_string)
            sys.stdout.flush()

            time.sleep(0.04) # 25 FPS cap for smooth video

    except Exception as e:
        sys.stderr.write(f"An error occurred: {e}\n")
        sys.stderr.flush()
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        print("Script finished.", file=sys.stderr)


if __name__ == '__main__':
    main()

