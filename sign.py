from multiprocessing import Process, Pipe
import snmp  # Import the snmp module
import ping  # Import the ping module
import time
import RPi.GPIO as GPIO
from datetime import datetime
import urllib.request, urllib.error
import threading
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
pwms = []  # This list will hold all PWM instances.


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
    'S':(1,1,0,0,5,1,1,0), #number 2, the second one, is top left segment
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
    'S.':(1,1,0,0,5,1,1,1), #number 2, the second one, is top left segment
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
    # initialization stuff
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(segments, GPIO.OUT)
    GPIO.setup(digits, GPIO.OUT)

def cleanup():
    GPIO.cleanup()

def get_ip_address():
    """Retrieve the primary IP address of the Raspberry Pi."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to an external server (doesn't actually establish a connection, but chooses an interface to use)
        s.connect(("8.8.8.8", 80))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP

def wake_up_display():
    """Wake up function to test all segments by quickly moving 8 through all the segments."""
    for _ in range(500):  # Display "HAIOHH" 50 times to increase visibility
        display_string("HA1 OH")

    for _ in range(5):  # Repeat 5 times
        for pos in range(6):  # Assuming you have a 6-character display
            data = ' ' * pos + '8' + ' ' * (5 - pos)
            
            for _ in range(5):  # Display each pattern 10 times to increase visibility
                display_string(data)

            time.sleep(0.005)  # Wait for 0.5 seconds between patterns
    
    """Wake up function to test all segments and display the IP address."""
    ip_address = get_ip_address()
    segments = ip_address.split('.')
    formatted_ip_1 = segments[1] + segments[0]  # "168192" for IP "192.168.1.49"
    formatted_ip_2 = segments[3].rjust(3, '0') + segments[2].rjust(3, '0')  # "049001" for IP "192.168.1.49"
    
    patterns = ["ADD 1P", formatted_ip_1, formatted_ip_2]
    
    for _ in range(5):  # Repeat the whole sequence 5 times
        for pattern in patterns:
            for _ in range(100):  # Display each pattern 100 times for visibility
                display_string(pattern)

    display_string("      ")  # Clear the display

def display_string(data):
    """Display the combined SNMP and ping data on the seven-segment displays."""

    # Formatting data
    formatted_data = str(data).ljust(12)[:12]  # assuming the display can show 6 characters at a time.
    #print("Formatted data:", formatted_data)

    # Add leading zeros if necessary
    if '.' in formatted_data:
        integer_part, decimal_part = formatted_data.split('.')
        integer_part = integer_part.rjust(4, '0')
        formatted_data = f"{integer_part}.{decimal_part}"

    #print("Formatted data with leading zeros:", formatted_data)

    # Break down the string into individual characters, considering '.' as part of the preceding character.
    expanded_string = []
    for i in range(len(formatted_data)):
        if formatted_data[i] == '.' and i > 0:
            expanded_string[-1] += '.'
        else:
            expanded_string.append(formatted_data[i])

    #print("Expanded string:", expanded_string)

    # Display the formatted data for a brief moment (no infinite loop)
    for digit, char in zip(digits, expanded_string):
        pattern = number_patterns.get(char, number_patterns[' '])  # Get the pattern or default to blank
        GPIO.output(digit, GPIO.HIGH)  # Enable this digit
        #print(f"Displaying character '{char}' with pattern {pattern}")

        for segment, value in zip(segments, pattern):
            GPIO.output(segment, value)

        time.sleep(0.003)  # Adjust this sleep for the correct display time per digit
        GPIO.output(digit, GPIO.LOW)  # Disable this digit

def display(data):
    # Simulated display function
    print(data)

if __name__ == '__main__':
    # Initialization for the display
    setup()

    # Wake up the display
    wake_up_display()    

    startup_time = time.time()
    
    # Create pipes for SNMP and ping
    parent_conn_snmp, child_conn_snmp = Pipe()
    parent_conn_ping, child_conn_ping = Pipe()

    # Create child processes
    p_snmp = Process(target=snmp.snmp_child, args=(child_conn_snmp,))
    p_ping = Process(target=ping.ping_child, args=(child_conn_ping,))

    # Start child processes
    p_snmp.start()
    p_ping.start()

    last_snmp_data = '000'
    last_ping_data = None
    try:
        while True:
            # Parent reads from its end of pipes and updates display
            if parent_conn_snmp.poll():  # Check if there's data to read
                data_received = parent_conn_snmp.recv()
                last_snmp_data = data_received['data']
                print(data_received['debug'])  # Print out the debug info or handle it as required

            if parent_conn_ping.poll():  # Check if there's data to read
                last_ping_data = parent_conn_ping.recv()

            # Check if snmp.py has crashed or terminated
            if not p_snmp.is_alive():
                print("SNMP process has terminated! Exiting sign.py...")
                os._exit(1)

            if time.time() - startup_time < 30:
                last_snmp_data = "SNP"
                continue


            combined_data = f"{last_ping_data}{last_snmp_data}"  # Combining the data.
            display_string(combined_data)  # Use the RPi.GPIO to display the combined data

    except KeyboardInterrupt:
        # On keyboard interrupt, terminate child processes and exit
        p_snmp.terminate()
        p_ping.terminate()
        p_snmp.join()
        p_ping.join()
        cleanup()  # Proper cleanup on exit
