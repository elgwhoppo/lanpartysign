import RPi.GPIO as GPIO
import time

# Segment and digit pin definitions:
segments = (25,5,6,12,13,19,16)  # Define GPIO pins for each segment a-g
digit = 18                       # Since it's a single digit display

# Segment patterns for numbers 0-9
num = {
    '0': (1,1,1,1,1,1,0),
    '1': (0,0,1,0,1,0,0),
    '2': (1,0,1,1,0,1,1),
    '3': (1,0,1,0,1,1,1),
    '4': (0,1,1,0,1,0,1),
    '5': (1,1,0,0,1,1,1),
    '6': (1,1,0,1,1,1,1),
    '7': (1,0,1,0,1,0,0),
    '8': (1,1,1,1,1,1,1),
    '9': (1,1,1,0,1,1,1),
}

GPIO.setmode(GPIO.BCM)
GPIO.setup(segments, GPIO.OUT)
GPIO.setup(digit, GPIO.OUT)

def display_number(number):
    GPIO.output(segments, num[number])   # Set segments for the number
    GPIO.output(digit, 1)                # Turn on the digit

try:
    while True:
        for i in range(10):             # Count from 0 to 9
            display_number(str(i))
            time.sleep(1)               # Delay for 1 second between numbers
            GPIO.output(digit, 0)       # Turn off the digit to ensure clear transition to next number

except KeyboardInterrupt:
    pass

GPIO.cleanup()
