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
segments = (25, 5, 6, 12, 13, 19, 16, 24)  # GPIOs for segments a-g, decimal on 24
digits = (23, 22, 27, 18, 17, 4)       # GPIOs for each of the 6 digits
FREQUENCY = 1000  # PWM frequency in Hz.
GLOBAL_BRIGHTNESS = 100  # 100% brightness
pwms = []  # This list will hold all PWM instances.

display_value_lock = threading.Lock()

# Global variable to hold the current value to be displayed
stringToPrint = "123456"

# Use a queue to communicate between threads
display_queue = queue.Queue() #This is the entire string to be printed >> goes into threaded_display
ping_queue = queue.Queue() #just the ping >> goes into display_queue
bps_queue = queue.Queue() #just the bps >> goes into display_queue

# Segment patterns for numbers 0-9, some letters also decimals
number_patterns = {' ':(0,0,0,0,0,0,0,0),
    'L':(0,1,0,1,0,1,0,0),
    'U':(0,1,1,1,1,1,0,0),
    'R':(0,0,0,1,0,0,1,0),
    'E':(1,1,0,1,0,1,1,0),
    'O':(0,0,0,1,1,1,1,0),
    'N':(0,0,0,1,1,0,1,0),
    'G':(1,1,0,1,1,1,0,0),
    'A':(1,1,1,1,1,0,1,0),
    'H':(0,1,0,1,1,0,1,0),
    'T':(0,1,0,1,1,1,1,0), #number 8, the last one is the middle segment
    'P':(1,1,1,1,0,0,1,0), #number 5, the last one is the bottom right
    'B':(0,1,0,1,1,1,1,0), #number 1, the first one is the top segment
    'D':(0,0,1,1,1,1,1,0), #number 2, the second one, is top left segment
    '0':(1,1,1,1,1,1,0,0),
    '1':(0,0,1,0,1,0,0,0),
    '2':(1,0,1,1,0,1,1,0),
    '3':(1,0,1,0,1,1,1,0),
    '4':(0,1,1,0,1,0,1,0),
    '5':(1,1,0,0,1,1,1,0),
    '6':(1,1,0,1,1,1,1,0),
    '7':(1,0,1,0,1,0,0,0),
    '8':(1,1,1,1,1,1,1,0),
    '9':(1,1,1,0,1,1,1,0),
    '_':(0,0,0,0,0,1,0,0),
    ' ':(0,0,0,0,0,0,0,0),
    '.':(0,0,0,0,0,0,0,1),
    'L.':(0,1,0,1,0,1,0,1),
    'U.':(0,1,1,1,1,1,0,1),
    'R.':(0,0,0,1,0,0,1,1),
    'E.':(1,1,0,1,0,1,1,1),
    'O.':(0,0,0,1,1,1,1,1),
    'N.':(0,0,0,1,1,0,1,1),
    'G.':(1,1,0,1,1,1,0,1),
    'A.':(1,1,1,1,1,0,1,1),
    'H.':(0,1,0,1,1,0,1,1),
    'T.':(0,1,0,1,1,1,1,1), #number 8, the last one is the middle segment
    'P.':(1,1,1,1,0,0,1,1), #number 5, the last one is the bottom right
    'B.':(0,1,0,1,1,1,1,1), #number 1, the first one is the top segment
    'D.':(0,0,1,1,1,1,1,1), #number 2, the second one, is top left segment
    '0.':(1,1,1,1,1,1,0,1),
    '1.':(0,0,1,0,1,0,0,1),
    '2.':(1,0,1,1,0,1,1,1),
    '3.':(1,0,1,0,1,1,1,1),
    '4.':(0,1,1,0,1,0,1,1),
    '5.':(1,1,0,0,1,1,1,1),
    '6.':(1,1,0,1,1,1,1,1),
    '7.':(1,0,1,0,1,0,0,1),
    '8.':(1,1,1,1,1,1,1,1),
    '9.':(1,1,1,0,1,1,1,1),
    '_.':(0,0,0,0,0,1,0,1)}

#def initialize_pwm():
#    """Initialize PWM for all segments and digits with global brightness."""
#    global pwms
#    for pin in segments:
#        pwm = GPIO.PWM(pin, FREQUENCY)
#        pwm.start(GLOBAL_BRIGHTNESS)
#        pwms.append(pwm)

def setup():
    # initialization stuff
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(segments, GPIO.OUT)
    GPIO.setup(digits, GPIO.OUT)
#    initialize_pwm()

def cleanup():
#    """Cleanup GPIO settings."""
#    for pwm in pwms:
#        pwm.stop()
    GPIO.cleanup()


def threaded_display():
    current_string = "      "  # Initialize with a blank string
    while True:
        try:
            # Check if a new string is available, non-blocking
            new_string = display_queue.get_nowait()
            current_string = new_string if new_string else current_string
        except queue.Empty:
            pass

        # The key is to run the display method continuously
        display_string(current_string)


def display_string(s):
    """Display a string on the seven-segment displays."""
    expanded_string = s.ljust(6, ' ')  # Pad the string to ensure it's 6 characters long

    for digit, char in zip(digits, expanded_string):
        pattern = number_patterns.get(char, number_patterns[' '])  # Default to blank if char not recognized
        GPIO.output(digit, GPIO.HIGH)  # Enable this digit

        for segment, value in zip(segments, pattern):
            GPIO.output(segment, value)

        time.sleep(0.001)  # To make the display visible
        GPIO.output(digit, GPIO.LOW)  # Disable this digit

def test_single_digit():
    """Display the number 8 on the first digit."""
    pattern = number_patterns['8']
    GPIO.output(digits[0], GPIO.HIGH)  # Enable the first digit

    for segment, value in zip(segments, pattern):
        GPIO.output(segment, value)

def test_all_digits():
    """Display the number 8 on all digits one by one."""
    for index, digit in enumerate(digits):
        pattern = number_patterns['8']
        GPIO.output(digit, GPIO.HIGH)  # Enable the current digit

        for segment, value in zip(segments, pattern):
            GPIO.output(segment, value)

        print(f"Displaying on digit {index + 1}")
        time.sleep(2)  # Display for 2 seconds

        # Turn off the segments for the current digit
        for segment in segments:
            GPIO.output(segment, GPIO.LOW)
        
        GPIO.output(digit, GPIO.LOW)  # Disable the current digit
        time.sleep(1)  # Wait for a second before moving to the next digit

def main():
    try:
        setup()  # Initialize
        #test_single_digit()  # Test single digit without any cycling
        #test_all_digits() # Test single digit with cycling

        # Start the display thread first
        display_thread = threading.Thread(target=threaded_display)
        display_thread.daemon = True  # Set to daemon so it'll automatically exit with the main thread
        display_thread.start()

        while True:
            for text in ["1.P._.1.P._.", "123456", "6.5.4.3.2.1."]:
                print(f"[Main] Displaying text {text}")
                display_queue.put(text)
                time.sleep(2)  # Give each string 2 seconds on the display

    except KeyboardInterrupt:
        # Clean up GPIOs upon exit
        cleanup()

if __name__ == "__main__":
    main()