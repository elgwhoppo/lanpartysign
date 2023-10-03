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

# initialization stuff
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(segments, GPIO.OUT)
GPIO.setup(digits, GPIO.OUT)
GPIO.setup(decimal_point, GPIO.OUT)

# Start PWM at 100% brightness for all segments and the decimal point
pwms = [GPIO.PWM(pin, FREQUENCY) for pin in segments + (decimal_point, )]
for pwm in pwms:
    pwm.start(100)

# Global variable to hold the current value to be displayed
stringToPrint = "      "

# Use a queue to communicate between threads
display_queue = queue.Queue() #This is the entire string to be printed
ping_queue = queue.Queue() #just the ping
bps_queue = queue.Queue() #just the bps

# truth table for segments and where they are.  i wired them funny as you can see.
# decimal point is on GPIO 24
num = {' ':(0,0,0,0,0,0,0),
    '*':(1,1,1,1,1,1,1,1),
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

def diagnostic_test():
    """Runs a diagnostic test to turn on all segments and decimal points."""
    try:
        for _ in range(5):  # run 5 times
            # Turn on all segments
            GPIO.output(segments, [1]*7)

            # Turn on all digit positions with decimals
            for digit in digits:
                GPIO.output(digit, 1)
                GPIO.output(decimal_point, 1)
                time.sleep(0.1)  # Reduced sleep duration
                GPIO.output(digit, 0)
                GPIO.output(decimal_point, 0)
    except Exception as e:
        print("An error occurred during the diagnostic test:", e)

def display_ip():
    """Display each octet of the IP address in the desired format for about 1 minute."""
    GPIO.setmode(GPIO.BCM)
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
        f"{int(octets[1]):03}{int(octets[0]):03}",
        f"{int(octets[3]):03}{int(octets[2]):03}"
    ]

    while time.time() - start_time < 60:  # run for about 1 minute
        for to_display in formatted_strings:
            end_time = time.time() + 1  # set end time to 1 second from now
            while time.time() < end_time:
                for idx, char in enumerate(to_display):
                    GPIO.output(segments, num[char])  # Set segments for the character
                    GPIO.output(digits[idx], 1)   # Light up the current digit
                    time.sleep(0.002)             # Adjust this delay to reduce flickering
                    GPIO.output(digits[idx], 0)   # Turn off the current digit to prepare for next

def threaded_display():
    current_string = " " * 6  # default value; adjust to your needs
    print("[threaded_display] Started!")

    while True:
        # Try to get a new value from the queue (non-blocking)
        try:
            #new_string = display_queue.get_nowait()
            new_string = ping_queue.get_nowait()
            print("[threaded_display] Got the following from the queue:", new_string)
            current_string = new_string
        except queue.Empty:
            # No new value in the queue
            pass

        str_to_display = current_string.replace(".", "")
        decimals = [i-1 for i, char in enumerate(current_string) if char == "."]

        for idx, char in enumerate(str_to_display):
            GPIO.output(segments, num[char])   # Set segments for the character

            if idx in decimals:
                GPIO.output(decimal_point, 1)
            else:
                GPIO.output(decimal_point, 0)

            GPIO.output(digits[idx], 1)        # Light up the current digit
            time.sleep(0.002)                  # Adjust this delay to reduce flickering
            GPIO.output(digits[idx], 0)        # Turn off the current digit to prepare for next


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


# Create and start the thread, passing the current value of stringToPrint
def main():
    global stringToPrint
    try:
        diagnostic_test()
        display_ip()
        
        #threaded run display
        display_thread = threading.Thread(target=threaded_display)
        display_thread.daemon = True  # Set to daemon so it'll automatically exit with the main t>
        display_thread.start()

        #threaded ping
        display_thread = threading.Thread(target=threaded_get_ping)
        display_thread.daemon = True  # Set to daemon so it'll automatically exit with the main t>
        display_thread.start()    

        #threaded SNMP
        #todo

        #threaded calculate string to print
        #display_thread = threading.Thread(target=threaded_calculate_string_to_print)
        #display_thread.daemon = True  # Set to daemon so it'll automatically exit with the main t>
        #display_thread.start()

        while True: 
            print("[Main] sleeping 10 seconds...", stringToPrint)
            time.sleep(10)

    except KeyboardInterrupt:
        # Clean up GPIOs upon exit
        GPIO.cleanup()

if __name__ == "__main__":
    main()