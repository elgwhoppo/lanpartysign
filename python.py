from RPIO import PWM
import urllib2
import time
import math
import os

# where do i find the throughput value?
bwurl = "http://10.11.12.1/bwnow.txt"

# pick a dma channel that won't crash your raspberry pi
dmach = 14

# define pulswidth in microseconds
# do not exceed 330 with 6 digits.  "night mode" can be 115
pulsewidth = 330

# define how often to fetch data and ping in milliseconds (e.g. 1000 = 1 second)
fetchrate = 500

# please dont touch any of these
global counter
subcycle = pulsewidth*6
pulsewidthon = pulsewidth-2
pulsewidthoff = 4
fuzzrate = fetchrate + 5
oldbw = [0,0,0]
counter = 0
y = "45.678"
t = "123456789"
k = 0

# initialization stuff
PWM.setup()
PWM.set_loglevel(PWM.LOG_LEVEL_ERRORS)
PWM.init_channel(dmach)

# truth table for segments and where they are.  i wired them funny as you can see.
# decimal point is on GPIO 24
num = {' ':(0,0,0,0,0,0,0),
    'L':(0,1,0,1,0,1,0),
    '0':(1,1,1,1,1,1,0),
    '1':(0,0,1,0,1,0,0),
    '2':(1,0,1,1,0,1,1),
    '3':(1,0,1,0,1,1,1),
    '4':(0,1,1,0,1,0,1),
    '5':(1,1,0,0,1,1,1),
    '6':(1,1,0,1,1,1,1),
    '7':(1,0,1,0,1,0,0),
    '8':(1,1,1,1,1,1,1),
    '9':(1,1,1,0,1,1,1)}

segments = (25,5,6,12,13,19,16)

# Pulse off and on (minimum of 4 for off state = 40 uS)
pulse = {
    0:pulsewidthoff,
    1:pulsewidthon}

print "moo"

def pwmsetup():
    # more ref add_channel_pulse(dma_channel, gpio, start, width)
    # Start alternating 10k uS pulses for the anodes
    # digits = (18,17,4,23,22,27)
    PWM.add_channel_pulse(dmach, 18, 0, pulsewidthon)
    PWM.add_channel_pulse(dmach, 17, pulsewidth, pulsewidthon)
    PWM.add_channel_pulse(dmach, 4, pulsewidth*2, pulsewidthon)
    PWM.add_channel_pulse(dmach, 23, pulsewidth*3, pulsewidthon)
    PWM.add_channel_pulse(dmach, 22, pulsewidth*4, pulsewidthon)
    PWM.add_channel_pulse(dmach, 27, pulsewidth*5, pulsewidthon)

def SetSix7Seg( digits ):
    # Split passed value into separate digit integer list
    # Set pulses for segments A-G (all digits) 
    for i in range(7):
        PWM.add_channel_pulse(dmach,segments[i], 0, pulse[num[digits[0]][i]])
        PWM.add_channel_pulse(dmach,segments[i], pulsewidth, pulse[num[digits[1]][i]])
        PWM.add_channel_pulse(dmach,segments[i], pulsewidth*2, pulse[num[digits[2]][i]])
        PWM.add_channel_pulse(dmach,segments[i], pulsewidth*3, pulse[num[digits[3]][i]])
        PWM.add_channel_pulse(dmach,segments[i], pulsewidth*4, pulse[num[digits[4]][i]])
        PWM.add_channel_pulse(dmach,segments[i], pulsewidth*5, pulse[num[digits[5]][i]]) 
    # since i only needed the decimal point in one place, this is a bit of a hack...
    if k < 99999:
        PWM.add_channel_pulse(dmach,24,pulsewidth,pulsewidthon)
    else:    
        PWM.add_channel_pulse(dmach,24,pulsewidth,pulsewidthoff)

def dothething():        
    counter = 0
    for i in range(86400):
        print "moo"
        print "fetching bandwidth..."
        bwresponse = urllib2.urlopen(bwurl,timeout=.5)
        print "pinging..."
        pingresponse = os.popen("timeout "+str(fetchrate*.001)+" ping -c 1 8.8.8.8 | grep rtt | cut -c 24-28").readlines()
        # a timed out ping will record a "999"
        pingresponse.append("999")
        t = bwresponse.read()
        y = pingresponse[0]
        print "here be ping"
        print y
        print "here be throguhput"
        print t
        # crash prevention in case a bandwidth value isn't fetched
        if t == "\n" or t == "" :
            print "IT'S EMPTY!!!!!!!!!!!!!!"
            if oldbw[0] == "\n":
                print "IT'S STILL EMPTY!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                oldbw[0] = "999999"
            t = oldbw[0]
        #
        # ACTIVATE FUZZ 
        #
        counter = counter +1
        print counter
        print "HISTORICAL VAUES"
        print oldbw[0]
        print oldbw[1]
        if counter == 2:
            counter = 0
        if counter == 1:
            oldbw[1] = oldbw[0]
            print "FUZZED VALUE"
            t = (int(t)+int(oldbw[1]))/2
        if counter == 0:
            oldbw[0] = t
            print "REAL VALUE"
        #
        # DEACTIVATE FUZZ
        #
        #maths
        k = int(t)/1000
        p = int(math.ceil(float(y)))
        # set 999 in case something blows up
        l = '999'
        v = '999'
        # crunch values
        # so throughput displays as 999, 99.9, 9.9, or 0.9 in megabits
        # and latency is 999, 99, or 9 in milliseconds
        if k >= 10000 and k < 999999:
            v = str(k)[0:3]
        if k >= 1000 and k < 9999:
            v = ' '+str(k)[0:2]
        if k >= 100 and  k < 999:
            v = ' 0'+str(k)[0:1]
        if k > 0 and k < 99:
            v = ' 01'
        if p >= 100 and p < 999:
            l = str(p)[0:3]
        if p >= 10 and p < 99:
            l = ' '+str(p)[0:2]
        if p < 9:
            l = '  '+str(p)[0:1]
        s = v.rjust(3)+l.rjust(3)
        print s
        print "looping..."    
        SetSix7Seg(s)
        time.sleep(fuzzrate*.001)

def doit():
    pwmsetup()
    dothething()

while True:
    try:
       doit()
    except urllib2.URLError, e:
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print "it broke. timeout (url)."
        print "contiuing anyway..."
        pass
    except urllib2.httplib.BadStatusLine:
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print " "
        print "something bad happened (badstatusline)"
        print "continuing anyway..."
        pass
    else:
       PWM.clear_channel(0)
       PWM.cleanup()