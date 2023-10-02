import RPi.GPIO as GPIO
import time
import subprocess
import re
import threading
import os
from multiprocessing import Process, Value

# Definitions
segments = (25, 5, 6, 12, 13, 19, 16)  # GPIOs for segments a-g
digits = (23, 22, 27, 18, 17, 4)       # GPIOs for each of the 6 digits
decimal_point = 24

#Script definitions
ip_to_ping = "172.193.67.34"
#ip_to_ping = "8.8.8.8"
fetchrate = 1000  # in milliseconds (1 second)

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

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(segments, GPIO.OUT)
GPIO.setup(digits, GPIO.OUT)
GPIO.setup(decimal_point, GPIO.OUT)

def display_string_with_decimal(input_str):
    str_to_display = input_str.replace(".", "")
    decimals = [i-1 for i, char in enumerate(input_str) if char == "."]  # Adjusted to get the correct segments
    
    for idx, char in enumerate(str_to_display):
        GPIO.output(segments, num[char])   # Set segments for the character

        if idx in decimals:
            GPIO.output(decimal_point, 1)
        else:
            GPIO.output(decimal_point, 0)

        GPIO.output(digits[idx], 1)        # Light up the current digit
        time.sleep(0.002)                  # Adjust this delay to reduce flickering
        GPIO.output(digits[idx], 0)        # Turn off the current digit to prepare for next


def main():
    try:
        for i in range(1, 1000000):
            stringToPrint = f" {i:.6f}".replace(".", "").replace("00000", " ").replace("0000", "  ").replace("000", "   ").replace("00", "    ").replace("0", "     ")
            display_string_with_decimal(stringToPrint)
            print ("stringToPrint:",stringToPrint)
            time.sleep(1)

    except KeyboardInterrupt:
        # Clean up GPIOs upon exit
        GPIO.cleanup()

if __name__ == "__main__":
    main()
