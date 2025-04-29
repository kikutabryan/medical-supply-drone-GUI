# import the necessary packages/libraries
from imutils.video import VideoStream
from pyzbar import pyzbar
import datetime
import imutils
import cv2
import numpy as np
import time
import keyboard

################################# SETUP ####################################
# initialize the video stream and allow the camera sensor to warm up
vs = VideoStream(src=0).start()
time.sleep(2.0)

# barcodes found thus far
found = set()
barcode_array = [None] * 4

# variables to check last and current barcodes
barcodeCurrent = None
barcodeLast = None

# time variables and frame rate
fps = 0
frame_count = 0
fps_past_time = time.time()

target_fps = 31
fps_limiter_past_time = time.time()

# display update time
display_update_interval = 1
display_update_past_time = time.time()

# screen dimensions of computer
monitor_screen_height = 1080
monitor_screen_width = 1920

# creates black background
display_screen = np.zeros((monitor_screen_height, monitor_screen_width, 3), dtype='uint8')

# full screen setup
cv2.namedWindow("Display", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Display", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# key press variables
quit_character = 'q'

filter_character = 'f'
filter_key_switch = 0
filter_key_pressed = 0
filter_key_pressed_release = True

blur_decrease_character = '1'
blur_decrease_key_pressed = 0
blur_decrease_key_pressed_release = False

blur_increase_character = '2'
blur_increase_key_pressed = 0
blur_increase_key_pressed_release = False

# blur settings
blur_factor = 1

# camera lens distortion matrices
dist_coeff = np.array([-0.32074218,  0.17722836,  0.00131003, -0.00037975, -0.06541414])
cam_matrix = np.array([[1.34294889e+03, 0.00000000e+00, 8.88780228e+02],
                [0.00000000e+00, 1.33493755e+03, 5.29064509e+02],
                [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]])

# barcode setup
# barcodes found thus far
found = set()
barcode_array = [None] * 4

# variables to check last and current barcodes
barcode_current = None
barcode_last = None

# create log file
log_file = open("RUAV_QR_Scan_Log.txt", "w")
############################################################################



################################ FUNCTIONS #################################
def get_fps(frame_count, fps, past_time):
    frame_count += 1
    if frame_count > 10:
        fps = int(float(frame_count) / (time.time() - past_time))
        past_time = time.time()
        frame_count = 0
    return (frame_count, fps, past_time)
    
def display_fps(frame, offset, fps_text):
    cv2.rectangle(frame, (0, 0), (offset, 60), (143, 16, 152), -1)
    cv2.rectangle(frame, (1, 1), (offset - 1, 60), (255, 255, 255), 2)
    cv2.putText(frame, fps_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

def display_filter_mode(frame, offset, filter_key_switch):
    if filter_key_switch:
        cv2.rectangle(frame, (0, 60), (offset, 120), (38, 155, 20), -1)
        cv2.putText(frame, "Filter: ON", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    else:
        cv2.rectangle(frame, (0, 60), (offset, 120), (20, 20, 155), -1)
        cv2.putText(frame, "Filter: OFF", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.rectangle(frame, (1, 60), (offset - 1, 120 - 1), (255, 255, 255), 2)

def display_commands(frame, offset, screen_height, filter_character, quit_character, blur_decrease_character, blur_increase_character, filter_key_switch):
    cv2.rectangle(frame, (0, 640), (offset - 1, screen_height - 1), (255, 255, 255), 2)
    cv2.putText(frame, "COMMANDS", (20, 700), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.line(frame, (20, 710), (190, 710), (255, 255, 255), 2)
    cv2.putText(frame, "Quit", (20, 760), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, " - "+quit_character, (20, 800), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, "Filter + QR", (20, 860), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, " - "+filter_character, (20, 900), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    if filter_key_switch:
        cv2.putText(frame, "Blur Filter", (20, 960), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, " - "+blur_decrease_character, (20, 1000), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, " - "+blur_increase_character, (20, 1040), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    
def key_pressed(character, key_pressed_past):
    if (keyboard.is_pressed(character) == False) and (key_pressed_past == True):
        key_pressed_release = True
    else:
        key_pressed_release = False
    if keyboard.is_pressed(character):
        key_pressed = True
    else:
        key_pressed = False
    return (key_pressed_release, key_pressed)

def key_switch(key_pressed_release, key):
    if key_pressed_release == True:
        if key == 0:
            key = 1
        elif key == 1:
            key = 0
    return (key)

def blur_change(factor, min_factor, max_factor, change, change_adjustment):
    factor += change * change_adjustment
    if factor > max_factor:
        factor = max_factor
    elif factor < min_factor:
        factor = min_factor
    print("Blur Factor:", factor)
    return(factor)    

def fps_limiter(last_time, target):
    while (time.time() - last_time) < (1.0 / target):
        pass
    last_time = time.time()
    return (last_time)
############################################################################



################################## LOOP ####################################
while True:
    # update video frame
    video_frame = vs.read()
    video_height, video_width = video_frame.shape[:2]
    cam_matrix[0,2] = video_width/2
    cam_matrix[1,2] = video_height/2

    # filter on
    if filter_key_switch == True:
        # checks if decrease key was pressed and released
        (blur_decrease_key_pressed_release, blur_decrease_key_pressed) = key_pressed(blur_decrease_character, blur_decrease_key_pressed)
        # checks if increase key was pressed and released
        (blur_increase_key_pressed_release, blur_increase_key_pressed) = key_pressed(blur_increase_character, blur_increase_key_pressed)

        # camera distortion fix
        video_frame = cv2.undistort(video_frame, cam_matrix, dist_coeff)
        
        # decrease blur
        if blur_decrease_key_pressed_release == True:
            blur_factor = blur_change(blur_factor, 1, 101, -1, 2)
        # increase blur
        elif blur_increase_key_pressed_release == True:
            blur_factor = blur_change(blur_factor, 1, 101, 1, 2)
        # add blur
        video_frame = cv2.GaussianBlur(video_frame, (blur_factor, blur_factor), 0)
        
        # barcode scanning
        # find the barcodes in the frame and decode each of the barcodes
        barcodes = pyzbar.decode(video_frame)
        # if no barcode detected, sets value of None type
        if len(barcodes) == 0:
            barcode_current = None

        # loop over the detected barcodes
        for barcode in barcodes:
            # extract the bounding box location of the barcode and draw
            # the bounding box surrounding the barcode on the image
            (x, y, w, h) = barcode.rect
            
            cv2.rectangle(video_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # the barcode data is a bytes object so if we want to draw it
            # on our output image we need to convert it to a string first
            barcode_data = barcode.data.decode("utf-8")
            barcode_type = barcode.type
            # draw the barcode data and barcode type on the image
            text = "{} ({})".format(barcode_data, barcode_type)
            cv2.putText(video_frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

            # checks to see if barcode changed to prevent repetitive printing
            barcode_current = barcode_data
            if barcode_last != barcode_current:
                if barcode_data != barcode_array[0]:
                    for i in range(3, 0, -1):
                        barcode_array[i] = barcode_array[i - 1]
                    barcode_array[0] = barcode_data
                print(datetime.datetime.now(), barcode_data)
                log_file.write("Scan data: "+str(barcode_data)+" Timestamp: "+str(datetime.datetime.now())+"\n")
                
        # sets last barcode value to current
        barcode_last = barcode_current
            
    # create fullscreen video
    fullscreen_video_width = int(video_width * (monitor_screen_height / video_height))
    fullscreen_video = cv2.resize(video_frame, (fullscreen_video_width, monitor_screen_height), interpolation = cv2.INTER_CUBIC)
    offset = int((monitor_screen_width - fullscreen_video_width) / 2)

    # update display commands and filter display
    if filter_key_pressed_release:
        # black background
        display_screen = np.zeros((monitor_screen_height, monitor_screen_width, 3), dtype='uint8')
        # filter on/off display
        display_filter_mode(display_screen, offset, filter_key_switch)
        # display commands
        display_commands(display_screen, offset, monitor_screen_height, filter_character, quit_character, blur_decrease_character, blur_increase_character, filter_key_switch)

    # add video to display screen
    display_screen[0:monitor_screen_height, offset:(monitor_screen_width - offset),:] = fullscreen_video

    # QR code list display
    if filter_key_switch:
        cv2.rectangle(display_screen, (875,450), (1045,630), (255,255,255), 2)
        cv2.rectangle(display_screen, (monitor_screen_width - 600, 860), (monitor_screen_width, monitor_screen_height), (0, 0, 0), -1)
        cv2.rectangle(display_screen, (monitor_screen_width - 599, 861), (monitor_screen_width - 1, monitor_screen_height - 1), (255, 255, 255), 2)
        cv2.putText(display_screen, "QR Scans:", (monitor_screen_width - 570, 900), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(display_screen, "1. "+str(barcode_array[0]), (monitor_screen_width - 570, 940), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(display_screen, "2. "+str(barcode_array[1]), (monitor_screen_width - 570, 980), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(display_screen, "3. "+str(barcode_array[2]), (monitor_screen_width - 570, 1020), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(display_screen, "4. "+str(barcode_array[3]), (monitor_screen_width - 570, 1060), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # check if the filter key was pressed and released and toggle filter key switch
    (filter_key_pressed_release, filter_key_pressed) = key_pressed(filter_character, filter_key_pressed)
    filter_key_switch = key_switch(filter_key_pressed_release, filter_key_switch)
    
    # fps
    (frame_count, fps, fps_past_time) = get_fps(frame_count, fps, fps_past_time)
    display_fps(display_screen, offset, "FPS: "+str(fps))

    # fps limiter
    fps_limiter_past_time = fps_limiter(fps_limiter_past_time, target_fps)

    # display
    cv2.imshow("Display", display_screen)
    key = cv2.waitKey(1) & 0xFF
    if key == ord(quit_character):
            break

# close windows
log_file.close()
cv2.destroyAllWindows()
vs.stop()
############################################################################
