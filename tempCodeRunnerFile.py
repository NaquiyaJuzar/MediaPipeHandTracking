import cv2
import time, math, numpy as np
import HandTrackingModule as htm
import pyautogui
import threading
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Initialize variables for accuracy testing
expected_gestures = ['Scroll', 'Zoom', 'Move'] * 5  # Repeat each gesture type 5 times (or adjust as needed)
predicted_gestures = []
gesture_index = 0  # To track which gesture we're testing
correct_predictions = 0
test_count = len(expected_gestures)

prevZoom = None

def smooth_zoom():
    global mode, prevZoom
    while mode == 'Zoom':
        if len(lmList) != 0 and fingers == [1, 1, 0, 0, 0]:  # When in zoom mode (only thumb and index up)
            x1, y1 = lmList[4][1], lmList[4][2]   # Thumb tip
            x2, y2 = lmList[8][1], lmList[8][2]   # Index tip
            current_length = math.hypot(x2 - x1, y2 - y1)  # Distance between thumb and index

            if prevZoom is not None:
                # Determine zoom direction based on the distance change
                zoomChange = current_length - prevZoom
                if abs(zoomChange) > 10:  # Set a threshold for smooth zoom
                    if zoomChange > 0:
                        pyautogui.hotkey('ctrl', '+')  # Zoom in
                    elif zoomChange < 0:
                        pyautogui.hotkey('ctrl', '-')  # Zoom out

            prevZoom = current_length  # Update the previous length for next calculation

        else:
            prevZoom = None  # Reset when the fingers are not detected correctly

def smooth_move():
    global mode, start_pos
    while mode == 'Move':
        # Assuming a fist is detected
        if len(lmList) != 0 and fingers == [0, 1, 1, 0, 0]:
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
        

wCam, hCam = 640,480
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)
pTime = 0

detector = htm.handDetector(maxHands=1, detectionCon=0.85, trackCon=0.8)
start_pos = None
color = (0,215,255)
tipIds = [4, 8, 12, 16, 20]
mode = ''
active = 0
prevY = None

pyautogui.FAILSAFE = False
while True:
    success, img = cap.read()
    if not success:
        print("Failed to capture image from camera")
        break

    img = detector.findHands(img)
    lmList = detector.findPosition(img, draw=False)
    fingers = []

    if len(lmList) != 0:

        # Thumb
        if lmList[tipIds[0]][1] > lmList[tipIds[0 -1]][1]:
            if lmList[tipIds[0]][1] >= lmList[tipIds[0] - 1][1]:
                fingers.append(1)
            else:
                fingers.append(0)
        elif lmList[tipIds[0]][1] < lmList[tipIds[0 -1]][1]:
            if lmList[tipIds[0]][1] <= lmList[tipIds[0] - 1][1]:
                fingers.append(1)
            else:
                fingers.append(0)

        for id in range(1,5):
            if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)

        # Determine the current mode (gesture)
        if (fingers == [1, 1, 1, 1, 1]) & (active == 0):
            mode = 'Scroll'
            active = 1
        
        elif (fingers == [1, 1, 0, 0, 0]) & (active == 0):
            mode = 'Zoom'
            active = 1
        elif (fingers == [0, 1, 1, 0, 0]) & (active == 0):
            mode = 'Move'
            active = 1
        else:
            mode = 'N'
            active = 0

############# Scroll ##############
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

################# Zoom ####################
    if mode == 'Zoom':
        active = 1
        if not threading.active_count() > 1:
            zoom_thread = threading.Thread(target=smooth_zoom)
            zoom_thread.start()

#######################################################################
    if mode == 'Move' and fingers == [0, 1, 1, 0, 0]:
        active = 1
        if not threading.active_count() > 1:
            move_thread = threading.Thread(target=smooth_move)
            move_thread.start()

    if fingers != [0,1,1,0,0]:
        active = 0

    # Log the predicted gesture for accuracy evaluation
    if active == 1 and gesture_index < test_count:
        predicted_gestures.append(mode)
        print(f"Expected Gesture: {expected_gestures[gesture_index]}, Predicted Gesture: {mode}")
        gesture_index += 1

    # After all test cases, calculate accuracy
    if gesture_index == test_count:
        correct_predictions = sum([pred == actual for pred, actual in zip(predicted_gestures, expected_gestures)])
        accuracy = (correct_predictions / test_count) * 100
        print(f"Accuracy: {accuracy:.2f}%")
        break  # Exit after the test is complete

    # Calculate FPS
    cTime = time.time()
    if (cTime - pTime) >= 0.1:
        fps = 1 / (cTime - pTime)
        pTime = cTime
        cv2.putText(img, f'FPS:{int(fps)}', (480, 50), cv2.FONT_ITALIC, 1, (255, 0, 0), 2)

    cv2.imshow('Hand LiveFeed', img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
