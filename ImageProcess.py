import numpy as np
import face_recognition
import csv
import cv2
import time
import threading
from tkinter import *


# The class to store, restore and remove faces to database
# It can also detect, recognize multi faces and show labels
class FaceProcess:
    def __init__(self, resize_frame=0.25, recognize_threshold=0.8, recognize_mode=0,
                 detect_interval=3, person_store_number=50, filename='known_face.csv'):
        self._resize = resize_frame         # Used to resize the frame to gain faster speed
        self._compare_threshold = recognize_threshold   # Used to recognized people
        self._mode = recognize_mode         # Choose the mode to detect people
        self._detect_inter = detect_interval    # Set how many frame to detect once
        self._person_store_number = person_store_number     # Set how many faces should be stored
        self._filename = filename           # Set the .csv file's name

        if not self._mode:
            self._start_recognize_thread()
            self._detect_inter = 0

        self._cnt = 0                       # Used to cooperation with _detect_inter
        self._known_face_encodings = []     # Stores known face encodings
        self._known_face_names = []         # Stores known face names
        self._file_data = []                # Stores file data read from .csv file
        self._face_locations = []           # Stores face locations that been detected
        self.face_names = []                # Stores face names that been recognized

        self._rgb_small_frame = []          # Stores the rgb frame image
        self._pre_detect_number = 0         # Stores the previous face numbers
        self._detect_sign = False           # Control the detect thread by event
        self._thread_sign = True            # Control the detect thread mainly

    # Save data to .csv file
    def save_database(self, cap_scan):
        # Let the user to input the name
        name = get_input("Input", "Please input your name:")
        if not name:
            return

        # Open a camera
        cv2.namedWindow('Scan your face')
        cv2.moveWindow('Scan your face', 20, 20)
        cnt = 0

        # Store "person_store_number" numbers encodings of the user to store_face_encodings
        data = []
        while True:
            ret, frame = cap_scan.read()
            small_frame = cv2.resize(frame, (0, 0), fx=self._resize, fy=self._resize)
            self._face_locations = face_recognition.face_locations(small_frame)
            face_encodings = face_recognition.face_encodings(small_frame, self._face_locations)
            if face_encodings:
                data.append(np.insert(np.array(face_encodings).astype(np.str_), 0, name))
                cnt = cnt + 1
            if cnt >= self._person_store_number:
                break
            cv2.imshow('Scan your face', frame)
            if cv2.waitKey(5) & 0xFF == ord('t'):
                break

        # Release the capture
        # cap_scan.release()
        cv2.destroyWindow('Scan your face')

        # Decide which method should be used
        data_store = data
        if name in self._known_face_names:
            # Open the file and rewrite the content
            file = open(self._filename, 'w')
            for i in range(len(self._known_face_names)):
                if self._known_face_names[i] != name:
                    tmp = np.insert(np.array(self._known_face_encodings[i]).astype(np.str_),
                                    0, self._known_face_names[i])
                    data_store.append(tmp)
        else:
            # Open the file to add content
            file = open(self._filename, 'a')

        # Write file
        writer = csv.writer(file, delimiter=',', lineterminator='\n')
        for content in data_store:
            writer.writerow(content)
        file.close()

        # Reload data from file
        self.load_database()

    # Delete existing data with specific name
    def delete_data(self):
        name = get_input("Input", "Please input the name you want to delete:")
        if not name:
            return

        if name not in self._known_face_names:
            return

        # delete data
        data_store = []
        for i in range(len(self._known_face_names)):
            if self._known_face_names[i] != name:
                tmp = np.insert(np.array(self._known_face_encodings[i]).astype(np.str_),
                                0, self._known_face_names[i])
                data_store.append(tmp)

        # Write file
        file = open(self._filename, 'w')
        writer = csv.writer(file, delimiter=',', lineterminator='\n')
        for content in data_store:
            writer.writerow(content)
        file.close()

        # Reload data from file
        self.load_database()

    # Load faces data from .csv file
    def load_database(self):
        file = open(self._filename, 'r')
        self._file_data = np.array(list(csv.reader(file, delimiter=',')))
        file.close()

        if self._file_data.shape[0] != 0:
            self._known_face_names = self._file_data[:, 0]
            self._known_face_encodings = []
            for i in range(self._file_data.shape[0]):
                self._known_face_encodings.append(self._file_data[i, 1:].astype(np.float64))
        else:
            self._known_face_names = []
            self._known_face_encodings = []

        self._detect_sign = True

    # Detect the faces in the frame and store them to _face_locations
    def detect_people(self, frame):
        self._cnt += 1
        if self._cnt > self._detect_inter:
            self._cnt = 0
            # resize the frame and convert the frame
            small_frame = cv2.resize(frame, (0, 0), fx=self._resize, fy=self._resize)
            self._rgb_small_frame = small_frame[:, :, ::-1]

            # Find all the faces and face encodings in the current frame of video
            self._face_locations = face_recognition.face_locations(self._rgb_small_frame)

            # If _mode was set 1, recognize people with detect
            if self._mode:
                self._recognize_people_core()

    # Start the thread to recognize faces
    def _start_recognize_thread(self):
        self._thread_sign = True
        threading.Thread(target=self._recognize_people).start()

    # Stop the thread to recognize faces
    def stop_recognize_thread(self):
        self._thread_sign = False

    # Recognize the faces and store them to _face_name
    def _recognize_people(self):
        while self._thread_sign:
            time.sleep(2)
            # If faces are detected
            if self._pre_detect_number != len(self._face_locations) or self._detect_sign:
                self._pre_detect_number = len(self._face_locations)
                self._detect_sign = False
                self._recognize_people_core()

    def _recognize_people_core(self):
        # Get the encodings of faces detected
        face_encodings = face_recognition.face_encodings(self._rgb_small_frame, self._face_locations)

        # Match with the database and store the names
        self.face_names = []
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            name = "Unknown"
            matches = face_recognition.compare_faces(self._known_face_encodings, face_encoding,
                                                     self._compare_threshold)

            # If a match was found in known_face_encodings, use the most match one
            if True in matches:
                if len(matches) > 1:
                    face_distances = face_recognition.face_distance(self._known_face_encodings,
                                                                    face_encoding)
                    most_match_index = np.where(face_distances == min(face_distances))[0][0]
                    name = self._known_face_names[most_match_index]
                else:
                    first_match_index = matches.index(True)
                    name = self._known_face_names[first_match_index]

            # Add name to face_names
            self.face_names.append(name)

    # Display the result in the frame
    def add_content_to_frame(self, frame):
        # Display the results
        for i in range(len(self._face_locations)):
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top = int(self._face_locations[i][0] * 1 / self._resize)
            right = int(self._face_locations[i][1] * 1 / self._resize)
            bottom = int(self._face_locations[i][2] * 1 / self._resize)
            left = int(self._face_locations[i][3] * 1 / self._resize)

            # Draw a label with a name below the face
            pts = np.array([[left, top],
                            [left, bottom],
                            [right, bottom],
                            [right, top]],
                           np.int32)
            cv2.polylines(frame, [pts], True, (0, 255, 0))

            if self.face_names and i < len(self.face_names):
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, self.face_names[i], (left, top - 6), font, 1.0, (0, 255, 0), 1)


class ObjectProcess:
    pass
    # Need to be finished in the future


'''
This get_input function can generate a message box and let users to input
This script is modified from https://blog.csdn.net/t60339/article/details/82842728
'''
def get_input(title, message):
    def return_callback(event):
        root.quit()

    # Get the tkinter root
    root = Tk(className=title)
    root.wm_attributes('-topmost', 1)

    # Set the size of the root
    screenwidth, screenheight = root.maxsize()
    width = 300
    height = 110
    size = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
    root.geometry(size)
    root.resizable(0, 0)

    # Set the label
    instruction = Label(root, height=2)
    instruction['text'] = message
    instruction.pack()

    # Set the entry
    entry = Entry(root)
    entry.bind('<Return>', return_callback)
    entry.pack()
    entry.focus_set()

    # Set the button
    button = Button(root, text='Confirmed', command=root.quit, relief=RAISED,
                    activebackground='green', activeforeground='white')
    button.pack()
    button.place(relx=0.38, rely=0.7)

    # Set other callback and mainloop
    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()

    # Get the text when the entry finished
    text = entry.get()
    root.destroy()

    return text
