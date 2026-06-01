import cv2
import numpy as np
import requests
import time
import threading
ZONE_POINTS = np.float32([[121, 57], [397, 64], [420, 450], [46, 446]])
ZONE_W_CM = 13.0
ZONE_H_CM = 18.0
OUT_W     = 390
OUT_H     = 540

ESP_IP    = "http://192.168.0.7"
FLASK_URL = "http://127.0.0.1:5000"
last_sent = 0
COOLDOWN  = 14


# ── هاد الـ flag يمنع أي إرسال وقت الذراع شغالة ──
arm_busy  = False

color_ranges = {
    "RED":   [(np.array([0,  120, 70]), np.array([10,  255, 255])),
              (np.array([170,120, 70]), np.array([180, 255, 255]))],
    "BLUE":  [(np.array([100,120, 70]), np.array([130, 255, 255]))],
    "GREEN": [(np.array([40,  70, 70]), np.array([80,  255, 255]))]
}
# ── تحويل من بكسل إلى سنتيمتر داخل المنطقة ──
def pixel_to_cm(px, py):
    x_cm = ZONE_W_CM - (px / OUT_W) * ZONE_W_CM
    y_cm = ZONE_H_CM - (py / OUT_H) * ZONE_H_CM
    return round(x_cm, 1), round(y_cm, 1)

def detect(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    best_color, best_area, best_cx, best_cy = None, 0, 0, 0

    for color, ranges in color_ranges.items():
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lo, hi in ranges:
            mask |= cv2.inRange(hsv, lo, hi)
        mask = cv2.dilate(cv2.erode(mask, None, iterations=2), None, iterations=2)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            c    = max(cnts, key=cv2.contourArea)
            area = cv2.contourArea(c)
            if area > 1500 and area > best_area:
                best_area  = area
                best_color = color
                M          = cv2.moments(c)
                best_cx    = int(M["m10"] / M["m00"])
                best_cy    = int(M["m01"] / M["m00"])
                bgr = {"RED":(0,0,255),"BLUE":(255,0,0),"GREEN":(0,255,0)}[color]
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(frame, (x,y), (x+w,y+h), bgr, 2)
                cv2.circle(frame, (best_cx, best_cy), 6, bgr, -1)

    return best_color, best_cx, best_cy

# ههيدا بيبعت الداتا للفلاسك
def send_detection(color, x_cm, y_cm):
    global arm_busy

    arm_busy = True  # ← منع أي إرسال ثاني

    # أرسل للـ ESP
    try:
        requests.post(f"{ESP_IP}/position",
            json={"color": color, "x": x_cm, "y": y_cm},
            timeout=1)
        print(f"→ ESP: {color} x={x_cm} y={y_cm}")
    except Exception as e:
        print(f"ESP Error: {e}")

    # أرسل للـ Flask
    try:
        requests.post(f"{FLASK_URL}/detect",
            json={"color": color, "x": x_cm, "y": y_cm},
            timeout=1)
    except:
        pass

    # انتظر وقت الذراع تخلص
    time.sleep(COOLDOWN)
    arm_busy = False  # ← هلق تمام نكشف مرة ثانية
    print("Arm finished — ready to detect next block")

def main():
    global last_sent, arm_busy

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Camera not found!")
        return

    M = cv2.getPerspectiveTransform(ZONE_POINTS,
        np.float32([[0,0],[OUT_W,0],[OUT_W,OUT_H],[0,OUT_H]]))

    print("Camera running — press Q to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        warped = cv2.warpPerspective(frame, M, (OUT_W, OUT_H))
        color, cx, cy = detect(warped) 
 
        if color:
            x_cm, y_cm = pixel_to_cm(cx, cy)
            bgr = {"RED":(0,0,255),"BLUE":(255,0,0),"GREEN":(0,255,0)}[color]
            cv2.putText(warped, f"{color} x={x_cm} y={y_cm}",
                (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, bgr, 2)

            # ← ما يرسل إذا الذراع شغالة
            if not arm_busy:
                now = time.time()
                if now - last_sent > COOLDOWN:
                    last_sent = now
                    t = threading.Thread(
                        target=send_detection,
                        args=(color, x_cm, y_cm)
                    )
                    t.daemon = True
                    t.start()
            else:
                cv2.putText(warped, "ARM BUSY — waiting...",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0,165,255), 2)

        cv2.circle(warped, (OUT_W, OUT_H), 8, (255,255,0), -1)
        cv2.imshow("Zone", warped)
        cv2.imshow("Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

