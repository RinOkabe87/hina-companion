import cv2

print("Testing camera...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ No camera found")
else:
    print("✅ Camera found!")
    ret, frame = cap.read()
    if ret:
        cv2.imwrite("test_frame.jpg", frame)
        print("✅ Photo saved as test_frame.jpg")
    cap.release()