# S&S's version for a common ANODE 7-segment display driven by Raspberry Pi
# code modified, tweaked and tailored from code by bertwert 
# on RPi forum thread topic 91796
# http://smokespark.blogspot.com/2015/11/70-4-digit-7-segment-led-display.html
import RPi.GPIO as GPIO
import urllib2

bwurl = "http://10.100.0.1:31337/bwnow.txt"

# let's make a ramdisk!  save write cycles and disk latency!
# mkdir /mnt/ramdisk
# mount -t ramfs -o -size=16m ramfs /mnt/ramdisk
# shell command for ping is ping chorus.co.nz -c 1 | grep rtt | cut -c 24-28
# run that a lot and save it somewhere like /mnt/ramdisk/latency
pingloc = "c:\moo.txt"

GPIO.setmode(GPIO.BCM)
 
# GPIO ports for the 7seg pins
segments =  (25,5,6,12,13,19,16,24)
 
for segment in segments:
    GPIO.setup(segment, GPIO.OUT)
    GPIO.output(segment, 1)
 
# GPIO ports for the digit pins
digits = (4,11,12,13,15,16)
 
for digit in digits:
    GPIO.setup(digit, GPIO.OUT)
    GPIO.output(digit, 0)
 
# note these digits are all inverted compared with the common cathode display:
num = {' ':(1,1,1,1,1,1,1), 
    '0':(0,0,0,0,0,0,1),
    '1':(1,1,0,1,0,1,1),
    '2':(0,1,0,1,0,0,0),
    '3':(0,1,0,1,0,0,0),
    '4':(1,0,0,1,0,1,0),
    '5':(0,0,1,1,0,0,0),
    '6':(0,0,1,0,0,0,0),
    '7':(0,1,0,1,0,1,1),
    '8':(0,0,0,0,0,0,0),
    '9':(0,0,0,1,0,0,0)}
 
try:
    while True:
        # get latency from /mnt/ramdisk/latency and store as y
        with open(pingloc) as pingvar:
            y = pingvar.read()
        # too big
        p = int(float(y))
        if p >= 1000:
            l = '999'
        # 100 to 999 (mmm.m)
        if p >= 100 and p < 999:
            l = str(p)[0:3]
        # 10 to 99 (mm.mm)
        if p >= 10 and p < 99:
            l = str(p)[0:2]
        # 1 to 9 (m.mmm)
        if p >= 10 and p < 99:
            l = str(p)[0:1]
        # 1 (0.mmm)
        if p > 0 and p < 9:
            l = '  1'
        # 1 (0.000)
        if p == 0:
            l = '  0'        
        response = urllib2.urlopen(bwurl)
        t = response.read()
        k = int(t)/1000
        # 0.00 (0)
        v = '000'
        # too big
        if k >= 1000000:
            v = 999
        # 100 to 999 (MMM999)
        if k >= 100000 and k < 999999:
            v = str(k)[0:3]
        # 10.0 to 99.9 (MM999)
        if k >= 10000 and k < 99999:
            v = str(k)[0:3]
        # 1.00 to 9.99 (M999)
        if k >= 1000 and k < 9999:
            v = str(k)[0:3]
        # 0.10 to 0.99 (999)
        if k >= 100 and  k < 999:
            v = '0'+str(k)[0:2]
        # 0.01 to 0.09 (99)
        if k >= 10 and k < 99:
            v = '00'+str(k)[0:1]
        # 0.01 (9)
        if k > 0 and k < 9:
            v = '001'
#       set s to combo of 3 digits of latency + 3 digits of throughput
        s = l.rjust(3)+v.rjust(3)
        for digit in range(6):
            # 10.0 to 99.9 (MM999)
            if k >= 10000 and k < 99999 and digit == 5:
                GPIO.output(24, 0)
            # 1.00 to 9.99 (M999)
            if k >= 1000 and k < 9999 and digit == 4:
                GPIO.output(24, 0)
            # 0.10 to 0.99 (999)
            if k >= 100 and k < 999 and digit == 4:
                GPIO.output(24, 0)
            # 0.01 to 0.09 (99)
            if k >= 10 and k < 99 and digit == 4:
                GPIO.output(24, 0)
            # 0.01 (9)
            if k > 0 and k < 9 and digit == 4:
                GPIO.output(24, 0)
            # 0.00 (0)
            if k == 0 and digit == 2:
                GPIO.output(24, 0)
            for loop in range(0,7):
                GPIO.output(segments[loop], num[s[digit]][loop])
            GPIO.output(digits[digit], 1)
            GPIO.output(24, 1)
            time.sleep(0.005)
            GPIO.output(digits[digit], 0)
finally:
        GPIO.cleanup()
