import cv2
import time
import math
import numpy as np
import pyautogui
import threading
from HandTrackingModule import handDetector  # Importing your handDetector class

prevZoom = None

# To store accuracy-related values
true_positive = 0
false_positive = 0

def smooth_zoom(lmList, fingers):
    global prevZoom
    while True:
        if len(lmList) != 0 and fingers == [1, 1, 0, 0, 0]:  # When in zoom mode (only thumb and index up)
            x1, y1 = lmList[4][1], lmList[4][2]   # Thumb tip
            x2, y2 = lmList[8][1], lmList[8][2]   # Index tip
            current_length = math.hypot(x2 - x1, y2 - y1)  # Distance between thumb and index

            if prevZoom is not None:
                zoomChange = current_length - prevZoom
                if abs(zoomChange) > 10:  # Set a threshold for smooth zoom
                    if zoomChange > 0:
                        pyautogui.hotkey('ctrl', '+')  # Zoom in
                    elif zoomChange < 0:
                        pyautogui.hotkey('ctrl', '-')  # Zoom out

            prevZoom = current_length  # Update the previous length for next calculation
        else:
            prevZoom = None  # Reset when the fingers are not detected correctly
        time.sleep(0.05)

def smooth_move(lmList, fingers):
    start_pos = None
    while True:
        if len(lmList) != 0 and fingers == [0, 1, 1, 0, 0]:  # Fist gesture for cursor movement
            if start_pos is None:
                start_pos = lmList[0][1], lmList[0][2]  # Capture initial hand position
                pyautogui.mouseDown()
            else:
                fist_current_pos = lmList[0][1], lmList[0][2]
                dx = fist_current_pos[0] - start_pos[0]  # Calculate movement on X-axis
                dy = fist_current_pos[1] - start_pos[1]  # Calculate movement on Y-axis
                pyautogui.moveRel(dx, dy)  # Smoothly move the cursor
                start_pos = fist_current_pos  # Update position for the next frame
        else:
            pyautogui.mouseUp()  # Release grab if fist isn't detected
            start_pos = None
        time.sleep(0.05)

def calculate_accuracy(detected_gesture, expected_gesture):
    global true_positive, false_positive
    if detected_gesture == expected_gesture:
        true_positive += 1
    else:
        false_positive += 1
    total_predictions = true_positive + false_positive
    accuracy = (true_positive / total_predictions) * 100 if total_predictions > 0 else 0
    return accuracy

def main():
    pTime = 0
    cTime = 0
    wCam, hCam = 640, 480
    cap = cv2.VideoCapture(0)
    cap.set(3, wCam)
    cap.set(4, hCam)

    detector = handDetector(maxHands=1, detectionCon=0.85, trackCon=0.8)
    tipIds = [4, 8, 12, 16, 20]  # Fingertip landmarks
    mode = ''
    active = 0
    prevY = None
    start_pos = None
    expected_gesture = ''  # Use this to set expected gestures (for testing accuracy)
    pyautogui.FAILSAFE = False  # Disable pyautogui's failsafe

    while True:
        success, img = cap.read()
        if not success:
            print("Failed to capture image from camera")
            break

        img = detector.findHands(img)
        lmList = detector.findPosition(img, z_axis=True, draw=False)
        fingers = []

        if len(lmList) != 0:
            # Thumb
            if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]:
                fingers.append(1)
            else:
                fingers.append(0)

            # Fingers 1-4
            for id in range(1, 5):
                if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]:
                    fingers.append(1)
                else:
                    fingers.append(0)

            # Gesture recognition
            detected_gesture = ''
            if fingers == [1, 1, 1, 1, 1]:
                detected_gesture = 'Scroll'
                mode = 'Scroll'
                active = 1
            elif fingers == [1, 1, 0, 0, 0]:
                detected_gesture = 'Zoom'
                mode = 'Zoom'
                active = 1
                if not threading.active_count() > 1:
                    zoom_thread = threading.Thread(target=smooth_zoom, args=(lmList, fingers))
                    zoom_thread.start()
            elif fingers == [0, 1, 1, 0, 0]:
                detected_gesture = 'Move'
                mode = 'Move'
                active = 1
                if not threading.active_count() > 1:
                    move_thread = threading.Thread(target=smooth_move, args=(lmList, fingers))
                    move_thread.start()
            else:
                mode = 'N'
                active = 0

            # Calculate and display accuracy (compare detected gesture to expected gesture)
            accuracy = calculate_accuracy(detected_gesture, expected_gesture)
            cv2.putText(img, f'Accuracy: {accuracy:.2f}%', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

############# Scroll Gesture Handling ##############
        if mode == 'Scroll':
            active = 1
            cv2.rectangle(img, (200, 410), (250, 455), (255, 255, 255), cv2.FILLED)
            if len(lmList) != 0:
                palmY = sum([lmList[id][2] for id in tipIds]) // len(tipIds)

                if prevY is not None:
                    if prevY - palmY > 20:
                        pyautogui.scroll(-300)
                    elif prevY - palmY < -20:
                        pyautogui.scroll(300)
                    prevY = palmY
                else:
                    prevY = palmY
            else:
                prevY = None
                active = 0

        # Calculate FPS
        cTime = time.time()
        fps = 1 / (cTime - pTime)
        pTime = cTime
        cv2.putText(img, f'FPS: {int(fps)}', (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)

        cv2.imshow("Hand Tracking", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
