import RPi.GPIO as GPIO
import time

# Definitions
segments = (25, 5, 6, 12, 13, 19, 16, 24)   # GPIOs for segments a-g
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
    for pin in segments + digits + (decimal_point, ):
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

def cleanup():
    """Cleanup GPIO settings."""
    GPIO.cleanup()

def main():
    setup()

    # Turn on all digits
    for digit in digits:
        GPIO.output(digit, GPIO.HIGH)

            
    # Initialize PWM for all segment pins.
    pwms = [GPIO.PWM(pin, FREQUENCY) for pin in segments]
    for pwm in pwms:
        pwm.start(100)

    try:
        # Display numbers 0-9 with varying brightness levels
        for number in range(0, 10):
            pattern = number_patterns[str(number)]
            brightness = 100 if number == 0 else number * 10
            for i, pwm in enumerate(pwms):
                if pattern[i]:
                    pwm.ChangeDutyCycle(brightness)  # Modify brightness as per the number
                else:
                    pwm.ChangeDutyCycle(0)  # Turn off segment
            print(f"Displaying number {number} at {brightness}% brightness")
            time.sleep(1)

    except KeyboardInterrupt:
        pass

    finally:
        for pwm in pwms:
            pwm.stop()
        cleanup()

if __name__ == "__main__":
    main()