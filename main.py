import cv2
from ImageProcess import FaceProcess
import requests
import threading as th
import time

# Users can change the following parameters
url_stranger = 'https://maker.ifttt.com/trigger/"new_stranger_detected"/json/with/key/bR_A_e1ooj1Ai2ZISWcjM4yWlrp2phmnDpjM-0geZ0p'
url_package = 'https://maker.ifttt.com/trigger/PackageCall/with/key/bR_A_e1ooj1Ai2ZISWcjM4yWlrp2phmnDpjM-0geZ0p'
filename = 'known_face.csv'
key_image_name = 'Key_lock.jpg'

# Users shouldn't change the following parameters
stranger = 0
package = 1
check_flag = True
flags = [True, True]

# Send Message with IFTTT APIs
def send_message(url):
    response = requests.post(url)
    print(response.content)


# Check the status of elements
def check_status():
    global flags
    while check_flag:
        if False in flags:
            index = flags.index(False)
            flags[index] = True
        time.sleep(30)


if __name__ == "__main__":
    # Configure the face recognition process
    face_rgn = FaceProcess(resize_frame=0.2, recognize_threshold=0.8, recognize_mode=0,
                           detect_interval=3, person_store_number=10, filename=filename)
    face_rgn.load_database()

    # Configure the camera
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280.0)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720.0)
    frame = None

    # Configure the window
    cv2.namedWindow('Detection', cv2.WINDOW_NORMAL)
    cv2.setWindowProperty('Detection', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Check the flags
    th.Thread(target=check_status).start()

    # Read image
    key_image = cv2.imread(key_image_name)
    key_image = cv2.resize(key_image, (0, 0), fx=0.2, fy=0.2)

    while True:
        # Grab a single frame from the camera
        ret, frame = camera.read()
        # Recognize people and show result
        face_rgn.detect_people(frame=frame)
        face_rgn.add_content_to_frame(frame=frame)

        # Send message according to the detection results
        if flags[stranger] is True and "Unknown" in face_rgn.face_names:
            flags[stranger] = False
            th.Thread(target=send_message, args=[url_stranger]).start()

        # Call themselves if package is detected
        if ["Unknown"] * len(face_rgn.face_names) != face_rgn.face_names:
            frame[0: key_image.shape[0], 0: key_image.shape[1], :] = key_image

        # Display the resulting image
        cv2.imshow('Detection', frame)

        # This allows you to stop the script from looping by pressing 'q'
        key = cv2.waitKey(5)
        if key == 27:   # ESC to quit
            break
        elif key == ord('s'):   # S to save
            th.Thread(target=face_rgn.save_database, args=[camera]).start()
        elif key == ord('r'):   # R to remove
            th.Thread(target=face_rgn.delete_data).start()

    # When everything is done, release the capture
    camera.release()
    cv2.destroyAllWindows()
    face_rgn.stop_recognize_thread()
    check_flag = False
