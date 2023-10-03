import RPi.GPIO as GPIO
import time

# Definitions
segments = (25, 5, 6, 12, 13, 19, 16, 24)   # GPIOs for segments a-g, the last for decimal
digits = (23, 22, 27, 18, 17, 4)        # GPIOs for each of the 6 digits
FREQUENCY = 1000  # PWM frequency in Hz.

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

def setup():
    """Initialize GPIO pins."""
    GPIO.setmode(GPIO.BCM)
    for pin in segments + digits:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

def cleanup():
    """Cleanup GPIO settings."""
    GPIO.cleanup()


def display_string(s, duration=1):
    """Display a string on the seven-segment displays."""
    expanded_string = []
    for i in range(len(s)):
        if s[i] == '.' and i > 0:  # if a dot is found and it's not the first character
            expanded_string[-1] += '.'  # append the dot to the last character
        else:
            expanded_string.append(s[i])  # add the character to the new string

    # Pad the expanded string with spaces to ensure it's 6 characters long
    while len(expanded_string) < 6:
        expanded_string.append(' ')

    for _ in range(int(duration * 100)):  # Assuming 100Hz refresh rate
        for digit, char in zip(digits, expanded_string):
            pattern = number_patterns.get(char, number_patterns[' '])  # Default to blank if char not recognized
            GPIO.output(digit, GPIO.HIGH)  # Enable this digit

            for segment, value in zip(segments, pattern):
                GPIO.output(segment, value)

            time.sleep(0.002)  # To make the display visible
            GPIO.output(digit, GPIO.LOW)  # Disable this digit


def main():
    setup()

    try:
        # Display sample strings
        for text in ["1.P._.1.P._.", "123456", "6.5.4.3.2.1."]:
            print(f"Displaying text {text}")
            display_string(text, duration=2)
            time.sleep(1)

    except KeyboardInterrupt:
        pass

    finally:
        cleanup()

if __name__ == "__main__":
    main()