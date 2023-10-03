# 1.0 refactor

import RPi.GPIO as GPIO
from datetime import datetime
import urllib.request, urllib.error
import threading
import time
import math
import re
import os
import queue 
import random
import socket
import http.client


# Definitions
segments = (25, 5, 6, 12, 13, 19, 16)  # GPIOs for segments a-g
digits = (23, 22, 27, 18, 17, 4)       # GPIOs for each of the 6 digits
decimal_point = 24
FREQUENCY = 1000  # PWM frequency in Hz.
GLOBAL_BRIGHTNESS = 100  # 100% brightness
pwms = []  # This list will hold all PWM instances.

display_value_lock = threading.Lock()

# Global variable to hold the current value to be displayed
stringToPrint = "123456"

# Use a queue to communicate between threads
display_queue = queue.Queue() #This is the entire string to be printed
ping_queue = queue.Queue() #just the ping
bps_queue = queue.Queue() #just the bps

# truth table for segments and where they are.
# decimal point is on GPIO 24
num = {' ':(0,0,0,0,0,0,0),
    'L':(0,1,0,1,0,1,0),
    'U':(0,1,1,1,1,1,0),
    'R':(0,0,0,1,0,0,1),
    'E':(1,1,0,1,0,1,1),
    'O':(0,0,0,1,1,1,1),
    'N':(0,0,0,1,1,0,1),
    'G':(1,1,0,1,1,1,0),
    'A':(1,1,1,1,1,0,1),
    'H':(0,1,0,1,1,0,1),
    'T':(0,1,0,1,1,1,1), #number 8, the last one is the middle segment
    'P':(1,1,1,1,0,0,1), #number 5, the last one is the bottom right
    'B':(0,1,0,1,1,1,1), #number 1, the first one is the top segment
    'D':(0,0,1,1,1,1,1), #number 2, the second one, is top left segment
    '0':(1,1,1,1,1,1,0),
    '1':(0,0,1,0,1,0,0),
    '2':(1,0,1,1,0,1,1),
    '3':(1,0,1,0,1,1,1),
    '4':(0,1,1,0,1,0,1),
    '5':(1,1,0,0,1,1,1),
    '6':(1,1,0,1,1,1,1),
    '7':(1,0,1,0,1,0,0),
    '8':(1,1,1,1,1,1,1),
    '9':(1,1,1,0,1,1,1),
    '_':(0,0,0,0,0,1,0)}

def initialize_pwm():
    """Initialize PWM for all segments and digits with global brightness."""
    global pwms
    for pin in segments:
        pwm = GPIO.PWM(pin, FREQUENCY)
        pwm.start(GLOBAL_BRIGHTNESS)
        pwms.append(pwm)

def setup():
    # initialization stuff
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(segments, GPIO.OUT)
    GPIO.setup(digits, GPIO.OUT)
    GPIO.setup(decimal_point, GPIO.OUT)
    initialize_pwm()

def cleanup():
    """Cleanup GPIO settings."""
    for pwm in pwms:
        pwm.stop()
    GPIO.cleanup()


def threaded_display():
    current_string = " " * 6  # Default value; adjust to your needs
    print("[threaded_display] Started!")

    while True:
        # Try to get a new value from the queue (non-blocking)
        try:
            new_string = display_queue.get_nowait()
            print("[threaded_display] Got the following from the queue:", new_string)
            current_string = new_string
        except queue.Empty:
            # No new value in the queue, continue displaying the previous value
            pass

        # Limit the string to 6 characters and pad with spaces if needed
        current_string = current_string[:6].ljust(6, ' ')

        for i in range(6):
            segment_to_display = current_string[i]
            GPIO.output(segments, num.get(segment_to_display, num[' ']))  # Use ' ' for unsupported characters

            GPIO.output(digits[i], 1)  # Light up the current digit
            time.sleep(0.002)          # Adjust this delay to reduce flickering
            GPIO.output(digits[i], 0)  # Turn off the current digit to prepare for next



def main():
    try:
        setup()  # Initialize

        # Start the display thread first
        display_thread = threading.Thread(target=threaded_display)
        display_thread.daemon = True  # Set to daemon so it'll automatically exit with the main thread
        display_thread.start()

        #diagnostic_test()  # Show diagnostics
        #display_ip()  # Show IP address

        # Start other threads
        #ping_thread = threading.Thread(target=threaded_get_ping)
        #ping_thread.daemon = True
        #ping_thread.start()

        # TODO: Start other threads if necessary...

        while True:
            print("[Main] sleeping 10 seconds...", stringToPrint)
            display_queue.put(stringToPrint)
            time.sleep(10)

    except KeyboardInterrupt:
        # Clean up GPIOs upon exit
        cleanup()

if __name__ == "__main__":
    main()