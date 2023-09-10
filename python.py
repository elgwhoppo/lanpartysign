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

from RPIO import PWM
from pysnmp.hlapi import *
from datetime import datetime
import urllib2
import time
import math
import os
import random

# what IP should I check for SNMP counters? 
#snmptarget = "192.168.1.157" #Unifi 16 port switch
#snmptarget = "192.168.1.1" #UDM-PRO Wad
#snmptarget = "10.11.12.1" #UDM-PRO Litchfield
#snmptarget = "10.11.12.2" #Dlink-DGS-1510-28X

# what remote IP should I ping to test for latency?
iptoping = "8.8.8.8" #Google DNS IP-Anycast
#iptoping = "139.130.4.5" #Australia DNS

# pick a dma channel that won't crash your raspberry pi
dmach = 14

# define pulswidth in microseconds
# do not exceed 330 with 6 digits.  "night mode" can be 115
pulsewidth = 330

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

subcycle = pulsewidth*6
pulsewidthon = pulsewidth-2
pulsewidthoff = 4
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
urlbroke = 0

#Variable Declaration IfOutOctets and IfInOctets- Modify to fit your environment

#UDM-PRO WAN Interface
#interfaceOIDout = "1.3.6.1.2.1.2.2.1.16.4" #ifIndex.4
#interfaceOIDin = "1.3.6.1.2.1.2.2.1.10.4" #ifIndex.4

#USG-PRO-4
interfaceOIDout = "1.3.6.1.2.1.2.2.1.16.4" #USG-PRO-4 WAN1 config
interfaceOIDin = "1.3.6.1.2.1.2.2.1.10.4"  #USG-PRO-4 WAN1 config

#LAN14 pfSense
#interfaceOIDout = "1.3.6.1.2.1.31.1.1.1.10.20" #LAN14 SNMP config
#interfaceOIDin = "1.3.6.1.2.1.31.1.1.1.6.20" #LAN14 SNMP config

#Dlink DGS-1510-28X
#interfaceOIDout = "1.3.6.1.2.1.2.2.1.16.25" #Dlink DGS-1510-28X Port 25 IfOutOctets, port 25, 26, etc. 
#interfaceOIDin = "1.3.6.1.2.1.2.2.1.10.25" #Dlink DGS-1510-28X Port 25 IfInOctets, port 25, 26, etc.

#Unifi 16 Port POE Switch port 1
#interfaceOIDout = "1.3.6.1.2.1.2.2.1.16.1" #Unifi 16 port POE Switch port 1
#interfaceOIDin = "1.3.6.1.2.1.2.2.1.10.1" #Unifi 16 port POE switch port 1

#ensure snmpv2 is ussed, set your read only community to whatever
snmpv2community = "public"

#Initial Variable Assignment - don't touch
octetsOLDout = 0
timeOLDout = 0
octetsOLDin = 0
timeOLDin = 0
bps = 0
snmpdelaycounter = 0
snmpunchangedvalue = 0


# initialization stuff
PWM.setup()
PWM.set_loglevel(PWM.LOG_LEVEL_ERRORS)
PWM.init_channel(dmach)

# truth table for segments and where they are.  i wired them funny as you can see.
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

segments = (25,5,6,12,13,19,16)

# Pulse off and on (minimum of 4 for off state = 40 uS)
pulse = {
    0:pulsewidthoff,
    1:pulsewidthon}

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
	
def SetDecimal(t):
    if t >= 1000000000: 
        # 1.2G
        print "Decmial is like: 1.3G. We're in Gbps now."
        PWM.add_channel_pulse(dmach,24,1,pulsewidthon)
        PWM.add_channel_pulse(dmach,24,pulsewidth,pulsewidthoff)		
    elif t >= 100000000 and t < 1000000000:
        # 999
        PWM.add_channel_pulse(dmach,24,pulsewidth,pulsewidthoff)
        PWM.add_channel_pulse(dmach,24,1,pulsewidthoff)
        print "Decmial is like: 999. We're in 100's of Mbps now."
    elif t >= 10000000 and t < 100000000:
        # 99.9
        PWM.add_channel_pulse(dmach,24,pulsewidth,pulsewidthon)
        PWM.add_channel_pulse(dmach,24,1,pulsewidthoff)
        print "Decimal is like: 10.6. We're in 10's of Mbps now"
    elif t == 66:
        PWM.add_channel_pulse(dmach,24,pulsewidth,pulsewidthoff)
        PWM.add_channel_pulse(dmach,24,1,pulsewidthoff)
        print "              Decmial Formatting: ERR"
    else:
        # 0.23
        PWM.add_channel_pulse(dmach,24,1,pulsewidthon)
        PWM.add_channel_pulse(dmach,24,pulsewidth,pulsewidthoff)
        print "Assuming decmial is like 0.16. We're in single digit or lower Mbps now."

def dothething():        
    counter = 0
    global snmpbrokecounter,snmpunchangedvalue,snmpbrokenow
    snmpbrokecounter = 0
    snmpunchangedvalue = 0
    snmpbrokenow = 0
    for i in range(86400):

		#call the SNMP bandwidth function
        bps = getsnmpbw()
		
        print "Raw bps value pulled from bps.txt:",bps
		
        t = int(bps)
        ogbps = t
		
        if ogbps != snmpunchangedvalue:
            snmpbrokenow = 0
            snmpbrokecounter = 0
        else:
            snmpbrokecounter = snmpbrokecounter+1
            print "BPS has been the same for this many times:     ",snmpbrokecounter
            print ""
		
        if snmpbrokecounter > 100:
            print "SNMP definitely broken. Mark as error: ",snmpbrokecounter		
            snmpbrokenow = 1
        snmpunchangedvalue = ogbps

        #activate fuzz, let's make bandwidth move a little
        #normal random
        bpsmultipler = random.uniform(0.9, 1.1)
        #5x random
        #bpsmultipler = random.uniform(5.85, 6.02)
		
        realvaluembps = t/1000000
        #print "  Real value Mbps: ",realvaluembps
        t = t*bpsmultipler
        t = int(t)
        fuzzedvaluembps = t/1000000
        #print "Fuzzed value Mbps: ",fuzzedvaluembps
        #print ""		
        pingresponse = os.popen("timeout "+str(fetchrate*.001)+" ping -c 1 "+str(iptoping)+" | grep rtt | cut -c 24-28").readlines()
        # a timed out ping will record a "999"
        pingresponse.append("999")
        y = pingresponse[0]
        print "   Latency to " + iptoping + " is pinging: " + str(y)
        
	#!!!!!!!!!!!!!!!!!!!!!!!DELAY!!!!!!!!!!!!!!!!!!!!!!!!!
        time.sleep(.15)

        #print "here be throughput in Kbps, raw from pfsense"
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
        #print counter
        #print "HISTORICAL VAUES"
        #print oldbw[0]
        #print oldbw[1]
        if counter == 2:
            counter = 0
        if counter == 1:
            oldbw[1] = oldbw[0]
            #print "FUZZED VALUES"
            t = (int(t)+int(oldbw[1]))/2
        if counter == 0:
            oldbw[0] = t
            #print "REAL VALUES"
        #
        # DEACTIVATE FUZZ
        #
        #maths
        var_bps = int(t)
        var_kbps = int(t)/1000
        var_mbps = int(t)/1000000
        var_gbps = int(t)/1000000000
        print "                Current Bandwidth"
        print "                             bps:", var_bps
        print "                            Kbps:", var_kbps
        print "                            Mbps:", var_mbps
        print "                            Gbps:", var_gbps        
        print "" 
        k = int(t)/1000
        g = int(t)/1000000
        p = int(math.ceil(float(y)))
        # set 999 in case something blows up
        l = '999'
        v = '999'

        # 1.5G
        if t >= 1000000000:
            v = str(var_gbps)[0:1]+str(var_mbps)[0:1]+str("G")
        # 689
        if t >= 100000000 and t < 1000000000:
            v = str(var_mbps)[0:3]
        # 56.3
        if t >= 10000000 and t < 100000000:
            v = str(var_mbps)[0:2]+str(var_kbps)[0:1]
        # 0.04
        if t < 10000000:
            v = str(var_mbps)[0:1]+str(var_kbps)[0:2]



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
        print "Raw value for bandwidth printing: " +str(v)
        print "              Raw value for ping: " +str(l)
        s = v.rjust(3)+l.rjust(3)
        print ""
        print "   The following will be printed: " + str(s)
        SetSix7Seg(s)
        print "Determine Decimal on this number: " + str(k)
        SetDecimal(t)
        print ""
        print "                   End of Loop"   
        print "******************************************************"
        #os.system('clear')
        #time.sleep(fuzzrate*.001)
		
def getsnmpbworig():
    global octetsOLDout,timeOLDout,octetsOLDin,timeOLDin,snmpdelaycounter,snmphealth
    f = open("/home/pi/speedsign/bps.txt", "r")
    ifbitspersecond = f.read()
    #print ifbitspersecond
    #turn into integer
    if ifbitspersecond is None: 
        print "SNMP returned NONE. Is the snmp script running? Manually setting to 66."
        ifbitspersecond = int(66)
        return ifbitspersecond		
    elif ifbitspersecond == "":
        print "SNMP returned empty. Is the snmp script running? Manually setting to 66."
        ifbitspersecond = int(66)
        return ifbitspersecond
    else:
        ifbitspersecond = int(ifbitspersecond)
        return ifbitspersecond



def getsnmpbw():
    global octetsOLDout, timeOLDout, octetsOLDin, timeOLDin, snmpdelaycounter, snmphealth

    try:
        with open("/home/pi/speedsign/bps.txt", "r") as f:
            ifbitspersecond = f.read()
            
            if not ifbitspersecond:
                print("SNMP returned an empty string. Is the SNMP script running? Manually setting to 66.")
                return 66
            else:
                ifbitspersecond = int(ifbitspersecond)
                return ifbitspersecond

    except IOError:
        print("File not found: /home/pi/speedsign/bps.txt. Is the file path correct?")
        return None

    except ValueError:
        print("Invalid data in the file. Is the SNMP script returning valid data? Manually setting to 66.")
        return 66

    except Exception as e:
        print("An error occurred: " + str(e))
        return None

def snmptargetonline():
    hostname = snmptarget
    response = os.system("ping -c 1 " + hostname)
    # and then check the response...
    if response == 0:
        snmptargetpingstatus = "Online"
    else:
        snmptargetpingstatus = "Offline"
    print snmptarget + "current status: " + snmptargetpingstatus
    return snmptargetpingstatus
	
def iptopingonline():
    hostname = iptoping
    response = os.system("ping -c 1 " + hostname)
    # and then check the response...
    if response == 0:
        iptopingstatus = "Online"
    else:
        iptopingstatus = "Offline"
    print iptoping + "current status: " + iptopingstatus
    return iptopingstatus


def doit():
# trying to get better error handling for no internet/snmp
#    snmptargetonline()
#    iptopingonline()
#    print iptopingstatus
#    print snmptargetpingstatus
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
        urlbrokecounter = urlbrokecounter +1
        print "URL Error; timeout. Has failed this many times: ", urlbrokecounter
        print "Contiuing anyway..."
        if urlbrokecounter > 20:
            SetSix7Seg("NO URL")
            SetDecimal("")
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
        print " "
	   #PWM.clear_channel(0)
       #PWM.cleanup()
