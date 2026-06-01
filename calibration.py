# step1_calibrate.py
import cv2
import numpy as np

points = []

def click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        print(f"Point {len(points)}: ({x}, {y})")
        if len(points) == 4:
            print("\n✅ Copy this to step2:")
            print(f"ZONE_POINTS = np.float32({points})")

cap = cv2.VideoCapture(1)  # غير لـ 0 أو 2 إذا ما اشتغل
cv2.namedWindow("Calibrate")
cv2.setMouseCallback("Calibrate", click)

print("Click 4 corners: top-left → top-right → bottom-right → bottom-left")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera not found!")
        break

    for i, p in enumerate(points):
        cv2.circle(frame, tuple(p), 8, (0,255,0), -1)
        cv2.putText(frame, str(i+1), (p[0]+10, p[1]),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

    cv2.putText(frame, f"Points: {len(points)}/4 — Press Q when done",
        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)

    cv2.imshow("Calibrate", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()