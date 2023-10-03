# 1.5 Python update, GPIO framework update
# 1.4 Bugfix and snmp updates 
# 1.3 Update via @elgwhoppo
#  - Moved all bandwidth checking to SNMP
#  - Cleaned up formatting 
# 1.2 Update via @elgwhoppo
#  - Increased default fetch time to 750ms
#  - Added "no URL" as error message when bwnow.txt can't be reached
# 1.1 Update via @elgwhoppo
#  - added iptoping in initial settings section
#  - fixed for Mbps greater than two digits not dropping decimal
# 1.0 Initial Version via @krhainos 

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

# what remote IP should I ping to test for latency?
iptoping = "8.8.8.8" #Google DNS IP-Anycast
#iptoping = "139.130.4.5" #Australia DNS

# define how often to fetch data and ping in milliseconds (e.g. 1000 = 1 second)
fetchrate = 750

# please dont touch any of these
global counter
global urlbrokecounter
global snmpunchangedcounter
global snmpunchangedvalue
global snmpdelaycounter
global bps,octetsOLDout,timeOLDout,octetsOLDin,timeOLDin,snmphealth
global snmptargetpingstatus,iptopingstatus
global stringToPrint

display_value_lock = threading.Lock()

stringToPrint = "O_0TBD"
last_displayed_string = ""
fuzzrate = fetchrate + 5
oldbw = [0,0,0]
counter = 0
urlbrokecounter = 0
snmpunchangedcounter = 0
snmpunchangedvalue = 0
y = "45.678"
t = "123456789"
k = 0
g = 0

#Initial Variable Assignment - don't touch
octetsOLDout = 0
timeOLDout = 0
octetsOLDin = 0
timeOLDin = 0
bps = 0
snmpdelaycounter = 0
snmpunchangedvalue = 0

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

# Global variable to hold the current value to be displayed
stringToPrint = "            "

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

def display_number_on_digit(value, digit_idx):
    # Special handling for the decimal point
    if value == '.':
        GPIO.output(decimal_point, 1)
    else:
        # Check if the character is in the truth table
        if value in num:
            segment_vals = num[value]
            for i, seg_pin in enumerate(segments):
                GPIO.output(seg_pin, segment_vals[i])
            GPIO.output(digits[digit_idx], 1)
        else:
            # Handle characters not in the truth table by turning off all segments
            for seg_pin in segments:
                GPIO.output(seg_pin, 0)
            GPIO.output(digits[digit_idx], 0)
    
    time.sleep(0.002)  # Adjust this delay to reduce flickering

    # Turn off the current digit and decimal point to prepare for the next character
    GPIO.output(digits[digit_idx], 0)
    GPIO.output(decimal_point, 0)

def threaded_display():
    print("[threaded_display] Started!")

    while True:
        try:
            # Simulate getting a value from the queue for testing
            new_string = "1.2.3.4.5.6."
            print("[threaded_display] Got the following from the queue:", new_string)
        except queue.Empty:
            pass

        # Initialize a list to store segment values for each digit
        digit_segments = [[], [], [], [], [], []]

        # Iterate through each character in the new string
        for char in new_string:
            if char == '.':
                # Handle decimal point
                for i in range(6):
                    digit_segments[i].append(1)
                print("[threaded_display] Handling decimal point:", digit_segments)
            elif char in num:
                # Handle valid characters using the truth table
                segments = num[char]
                for i in range(6):
                    digit_segments[i].append(segments[i])
                print("[threaded_display] Handling character", char, ":", digit_segments)
            else:
                # Handle characters not in the truth table (e.g., space)
                for i in range(6):
                    digit_segments[i].append(0)
                print("[threaded_display] Handling unknown character", char, ":", digit_segments)

        # Update the segments for each digit
        for idx in range(6):
            GPIO.output(segments[idx], digit_segments[idx])

        # Sleep for a short duration to control the display update rate
        time.sleep(0.002)

        # Turn off all digits and decimal point
        for i in range(6):
            GPIO.output(digits[i], 0)
        GPIO.output(decimal_point, 0)



def diagnostic_test():
    """Runs a diagnostic test to display numbers from 1 to 9 on each digit with the decimal lit up."""
    try:
        print("[diagnostic_test] Displaying numbers 1 to 9 on each digit with decimal lit up.")
        
        for digit in digits:  # for each digit position
            for num_char in "123456789":  # cycle through the numbers 1-9
                to_display = num_char + '.'  # append a decimal for visualization
                print(f"[diagnostic_test] Sending to queue: {to_display}")
                display_queue.put(to_display)  # Push the value to the queue for the threaded_display to handle
                time.sleep(1)  # display each number for 1 second

    except Exception as e:
        print("An error occurred during the diagnostic test:", e)


def display_ip():
    """Push the formatted IP address strings to the display queue for about 1 minute."""

    def get_ip_address():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't need to be reachable
            s.connect(('10.254.254.254', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    ip = get_ip_address()
    octets = ip.split('.')
    start_time = time.time()

    formatted_strings = [
        "ADD 1P",
        f"{int(octets[1]):03}.{int(octets[0]):03}",
        f"{int(octets[3]):03}.{int(octets[2]):03}"
    ]

    while time.time() - start_time < 60:  # run for about 1 minute
        for to_display in formatted_strings:
            print(f"[display_ip] Pushing '{to_display}' to display_queue")
            display_queue.put(to_display)  # Push the formatted string to the queue
            time.sleep(1)  # Display each formatted string for 1 second


def threaded_get_ping():
    print("[threaded_get_ping] Started!")
    ping_loop_counter = 0
    while True:
        try:
            ping_loop_counter += 1
            pingresponse = os.popen("timeout "+str(fetchrate*.001)+" ping -c 1 "+str(iptoping)+" | grep rtt | cut -c 24-28").readlines()
            # a timed out ping will record a "999"
            pingresponse.append("999")
            y = pingresponse[0]
            y = "{:3}".format(min(999, int(float(y))))
            ping_queue.put(y)  # Push the new value to the queue



            print("[threaded_get_ping]:Pushed ",str(y)," to ",ping_queue)
            if ping_loop_counter % 10 == 0:
                print("[threaded_display] Ping thread is running. One of the last 10 pings is:", y)
                ping_loop_counter = 0
            time.sleep(fetchrate*.001)

        except Exception as e:
            print("An error occurred: " + str(e))
            return None


def getsnmpbw():
    global octetsOLDout, timeOLDout, octetsOLDin, timeOLDin, snmpdelaycounter, snmphealth

    try:
        with open("/home/pi/lanpartysign/bps.txt", "r") as f:
            ifbitspersecond = f.read()
            
            if not ifbitspersecond:
                print("SNMP returned an empty string. Is the SNMP script running? Manually setting to 66.")
                return 66
            else:
                ifbitspersecond = int(ifbitspersecond)
                return ifbitspersecond

    except IOError:
        print("File not found: /home/pi/lanpartysign/bps.txt. Is the file path correct?")
        return None

    except ValueError:
        print("Invalid data in the file. Is the SNMP script returning valid data? Manually setting to 66.")
        return 66

    except Exception as e:
        print("An error occurred: " + str(e))
        return None
   	
def threaded_calculate_string_to_print():        
    counter = 0
    global snmpbrokecounter,snmpunchangedvalue,snmpbrokenow,stringToPrint
    snmpbrokecounter = 0
    snmpunchangedvalue = 0
    snmpbrokenow = 0

    #call the SNMP bandwidth function
    bps = getsnmpbw()
    
    print("Raw bps value pulled from bps.txt:", bps)
    
    t = int(bps)
    ogbps = t
    
    if ogbps != snmpunchangedvalue:
        snmpbrokenow = 0
        snmpbrokecounter = 0
    else:
        snmpbrokecounter = snmpbrokecounter+1
        print("BPS has been the same for this many times:     ", snmpbrokecounter)
        print("")
    
    if snmpbrokecounter > 100:
        print("SNMP definitely broken. Mark as error: ", snmpbrokecounter)
        snmpbrokenow = 1
    snmpunchangedvalue = ogbps

    #Add some fuzz to the bandwidth
    bpsmultipler = random.uniform(0.95, 1.05) 
    realvaluembps = t/1000000
    t = t*bpsmultipler
    t = int(t)
    fuzzedvaluembps = t/1000000

    #
    pingresponse = os.popen("timeout "+str(fetchrate*.001)+" ping -c 1 "+str(iptoping)+" | grep rtt | cut -c 24-28").readlines()
    # a timed out ping will record a "999"
    pingresponse.append("999")
    y = pingresponse[0]
    print("   Latency to " + iptoping + " is pinging: " + str(y))

    counter = counter +1
    #print(counter)
    #print("HISTORICAL VAUES")
    #print(oldbw[0])
    #print(oldbw[1])
    if counter == 2:
        counter = 0
    if counter == 1:
        oldbw[1] = oldbw[0]
        #print("FUZZED VALUES")
        t = (int(t)+int(oldbw[1]))/2
    if counter == 0:
        oldbw[0] = t
        #print("REAL VALUES")
    #
    # DEACTIVATE FUZZ
    #
    #maths
    var_bps = int(t)
    var_kbps = int(t)/1000
    var_mbps = int(t)/1000000
    var_gbps = int(t)/1000000000
    #print("                Current Bandwidth")
    #print("                             bps:", var_bps)
    #print("                            Kbps:", var_kbps)
    #print("                            Mbps:", var_mbps)
    #print("                            Gbps:", var_gbps)        
    #print("") 
    k = int(t)/1000
    g = int(t)/1000000
    p = int(math.ceil(float(y)))
    # set 999 in case something blows up
    l = '999'
    v = '999'

    # 1.5G
    if t >= 1000000000:
        v = str(var_gbps)[0:1]+str(".")+str(var_mbps)[0:1]+str("G")
    # 689
    if t >= 100000000 and t < 1000000000:
        v = str(var_mbps)[0:3]
    # 56.3
    if t >= 10000000 and t < 100000000:
        v = str(var_mbps)[0:2]+(".")+str(var_kbps)[0:1]
    # 0.04
    if t < 10000000:
        v = str(var_mbps)[0:1]+(".")+str(var_kbps)[0:2]

    if ogbps == 66:
        #Set the value to 66 for error handling; will remove the decmial in the SetDecimal function
        t = 66
        #Set the verbiage to ERR for error, or blank in the case of this script now
        #v = "ERR"
        v = "TBD"
    if snmpbrokenow == 1:
        t = 66
        #Set to blank, err not by design
        #v = "TBD"
        v = "O_0"
    if p >= 999:
        l = 'UHH'
    if p >= 100 and p < 999:
        l = str(p)[0:3]
    if p >= 10 and p < 99:
        l = ' '+str(p)[0:2]
    if p < 9:
        l = '  '+str(p)[0:1]
    print("Raw value for bandwidth printing: " +str(v))
    print("              Raw value for ping: " +str(l))
    stringToPrint = str(l)+str(v)
    print("")
    print("   The following will be printed by the threaded process: " + stringToPrint)
    print("[Main] Pushing the following to the display queue:", stringToPrint)
    display_queue.put(stringToPrint)  # Push the new value to the queue
    print("")
    print("                   End of Loop")   
    print("******************************************************")


def main():
    global stringToPrint

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
            time.sleep(10)

    except KeyboardInterrupt:
        # Clean up GPIOs upon exit
        cleanup()

if __name__ == "__main__":
    main()