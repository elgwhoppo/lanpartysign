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


# where do i find the throughput value?
# hint: throughput value should be in bps
bwurl = "/tmp/bwnow.txt"

# what remote IP should I ping to test for latency?
iptoping = "8.8.8.8"

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
global snmptargetofflinecounter
global snmpdelaycounter
global bps,octetsOLDout,timeOLDout,octetsOLDin,timeOLDin,snmphealth
subcycle = pulsewidth*6
pulsewidthon = pulsewidth-2
pulsewidthoff = 4
fuzzrate = fetchrate + 5
oldbw = [0,0,0]
counter = 0
urlbrokecounter = 0
y = "45.678"
t = "123456789"
k = 0
g = 0
urlbroke = 0
#Variable Declaration SetupifOutOctets - Modify to fit your environment
interfaceOIDout = "1.3.6.1.2.1.31.1.1.1.10.2"
interfaceOIDin = "1.3.6.1.2.1.31.1.1.1.6.2"
snmptarget = "10.11.12.1"
snmpv2community = "public"

#Initial Variable Assignment - don't touch
octetsOLDout = 0
timeOLDout = 0
octetsOLDin = 0
timeOLDin = 0
bps = 0
snmpdelaycounter = 0


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
    'O':(0,0,0,1,1,1,1),
    'N':(0,0,0,1,1,0,1),
    'G':(1,1,0,1,1,1,0),
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
	
def SetDecimal(k):
    #print "I'm in SetDecimal...about to check K:"
    #print k
    if k >= 999999:
        print "              Decmial Formatting: 1.3G"
        PWM.add_channel_pulse(dmach,24,1,pulsewidthon)
    elif k >= 99999 and  k < 999999:
        PWM.add_channel_pulse(dmach,24,pulsewidth,pulsewidthoff)
        PWM.add_channel_pulse(dmach,24,1,pulsewidthoff)
        print "              Decmial Formatting: 999"
    else:
        PWM.add_channel_pulse(dmach,24,pulsewidth,pulsewidthon)
        print "              Decmial Formatting: 0.1"

def dothething():        
    counter = 0
    for i in range(86400):
        print "Fetching bandwidth from " + str(snmptarget) + "..."
		#call the SNMP bandwidth function
		
        bps = getsnmpbw()
        t = int(bps)
        print "        bps has been measured at: " + str(t)
        print ""
        print "pinging out..."
        pingresponse = os.popen("timeout "+str(fetchrate*.001)+" ping -c 1 "+str(iptoping)+" | grep rtt | cut -c 24-28").readlines()
        # a timed out ping will record a "999"
        pingresponse.append("999")
        y = pingresponse[0]
        print "   Latency to " + iptoping + " is pinging: " + str(y)
        #print y
        #print "here be throughput in Kbps, raw from pfsense"
        #print t
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
        k = int(t)/1000
        g = int(t)/1000000
        p = int(math.ceil(float(y)))
        # set 999 in case something blows up
        l = '999'
        v = '999'
        # crunch values
        # so throughput displays as 1.3_,999, 99.9, 9.9, or 0.9 in megabits
        # and latency is 999, 99, or 9 in milliseconds
        #k = 1699999 #Bogus testing number for 1.6G format
        if k >= 999999 and k < 9999999:
            v = str(k)[0:2]+str("G")
        if k >= 10000 and k < 999999:
            v = str(k)[0:3]
        if k >= 1000 and k < 9999:
            v = ' '+str(k)[0:2]
        if k >= 100 and  k < 999:
            v = ' 0'+str(k)[0:1]
        if k > 0 and k < 99:
            v = ' 01'
        #if snmphealth == "Network Error":
        #    v = "N00"
        if p >= 100 and p < 999:
            l = str(p)[0:3]
        if p >= 10 and p < 99:
            l = ' '+str(p)[0:2]
        if p < 9:
            l = '  '+str(p)[0:1]
        print "Raw value for bandwidth printing: " +str(v)
        print "              Raw value for ping: " +str(l)
        print ""
        s = v.rjust(3)+l.rjust(3)
        print ""
        print "   THE FOLLOWING WILL BE PRINTED: " + str(s)
        SetSix7Seg(s)
        #print "Determine Decimal on this number: " + str(k)
        SetDecimal(k)
        print ""
        print "                   End of Loop"   
        print "******************************************************"
        time.sleep(fuzzrate*.001)
		
def getsnmpbw():
    global octetsOLDout,timeOLDout,octetsOLDin,timeOLDin,snmpdelaycounter,snmphealth
    snmpdelaycounter = snmpdelaycounter + 1
    time.sleep(1)
    # *** get selected interface interface out rate stuff it in a variable
	# set time
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
		   CommunityData(snmpv2community),
		   UdpTransportTarget((snmptarget, 161)),
		   ContextData(),
		   ObjectType(ObjectIdentity(interfaceOIDout)))
    )
    if errorIndication:
	    print(errorIndication)
    elif errorStatus:
	    print('%s at %s' % (errorStatus.prettyPrint(),
	    					errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
	    for varBind in varBinds:
		    #print(' = '.join([x.prettyPrint() for x in varBind]))
		    int1out = varBind
            currenttimeout = time.time()
			
    # *** get selected interface interface IN rate stuff it in a variable
	# set time
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
		   CommunityData(snmpv2community),
		   UdpTransportTarget((snmptarget, 161)),
		   ContextData(),
		   ObjectType(ObjectIdentity(interfaceOIDin)))
    )
    if errorIndication:
	    print(errorIndication)
    elif errorStatus:
	    print('%s at %s' % (errorStatus.prettyPrint(),
	    					errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
	    for varBind in varBinds:
		    #print(' = '.join([x.prettyPrint() for x in varBind]))
		    int1in = varBind
            currenttimein = time.time()

    # OUT METRICS
	
    # Turn var into a string
    int1out = str(int1out)
    # Chop off character 34 and left
    int1out = int1out[34:]
    #convert to integer
    int1out = int(int1out)
	
    changedbitsout = (int1out - octetsOLDout)
    timedeltaout = (currenttimeout - timeOLDout)
    changedbitsout = abs(changedbitsout)
	
	# IN METRICS
	# Turn var into a string
    int1in = str(int1in)
    # Chop off character 34 and left
    int1in = int1in[33:]
	#exmple:   SNMPv2-SMI::mib-2.31.1.1.1.6.2 = 18417094860
    #convert to integer
    int1in = int(int1in)
    changedbitsin = (int1in - octetsOLDin)
    timedeltain = (currenttimein - timeOLDin)
    changedbitsin = abs(changedbitsin)


	#calculate bits per second
    ifoutbytespersecond = changedbitsout/timedeltaout
    ifinbytespersecond = changedbitsin/timedeltain
    ifbytespersecond = ifoutbytespersecond+ifinbytespersecond
    ifoutbitspersecond = ifoutbytespersecond*8
    ifinbitspersecond = ifinbytespersecond*8
    ifbitspersecond = ifinbitspersecond+ifoutbitspersecond
    ifbitspersecond = int(round(ifbitspersecond))
    ifKbitspersecond = ifbitspersecond/1000
    ifMbitspersecond = ifKbitspersecond/1000
    ifGbitspersecond = ifMbitspersecond/1000
    ifGbitspersecond = round(ifGbitspersecond,1)
    #print "---------------------------------------------------"
    #print "ifinbitspersecond -----> " + str(ifinbitspersecond)
    #print "ifoutbitspersecond ----> " + str(ifoutbitspersecond)
    #print "ifbitspersecond -------> " + str(ifbitspersecond)
    #print "---------------------------------------------------"
    #print "ifKbitspersecond ---> " + str(ifKbitspersecond)
    #print "ifMbitspersecond ---> " + str(ifMbitspersecond)
    #print "ifGbitspersecond ---> " + str(ifGbitspersecond)
	
    #byteschar = str(bytes)
	#f= open("/tmp/bwnow.txt","w+")
    #for i in range(1):
    #     f.write(byteschar)
    #f.close()

    #print "bps: -->"
    #print bytes
    #print "Kbps:-->"
    #print(bytes/1000)
    #print "Mbps:-->"
    #print(bytes/1000000)

    #set variables to old for next round of math
    octetsOLDout = int1out
    timeOLDout = currenttimeout
    octetsOLDin = int1in
    timeOLDin = currenttimein
	
	#health check the SNMP node - meh maybe some day. 
    #snmphealth = check_ping()
    #if snmphealth == "Network Error":
    #    print "SNMP host is offline"
    #else:
    #    print "SNMP host is online and functioning."
	
	

	
    return ifbitspersecond

def check_ping():
    hostname = snmptarget
    response = os.system("ping -c 1 " + hostname)
    # and then check the response...
    if response == 0:
        pingstatus = "Network Active"
    else:
        pingstatus = "Network Error"

    return pingstatus
	

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
       PWM.clear_channel(0)
       PWM.cleanup()
	   

# Interface OID looks like Test 2:em1 (1.3.6.1.2.1.31.1.1.1.6.2,1.3.6.1.2.1.31.1.1.1.10.2): in=107117891  out=945560614
# Use paessler SNMPTEST to obtain when doing interface or snmpwalk
#Pfsense SNMP Helper  - see https://www.reddit.com/r/PFSENSE/comments/3szzbh/snmp_64bit_counters/ for additional help
#
# the following is a pfsense box with 1 LAN 1 WAN intefaces. 
#snmpwalk -v 2c -c public 10.11.12.1 iso.3.6.1.2.1.31.1.1.1
#iso.3.6.1.2.1.31.1.1.1.1.1 = STRING: "em0" <-- interface definition note for below, these increment with additional interfaces
#iso.3.6.1.2.1.31.1.1.1.1.2 = STRING: "em1"
#iso.3.6.1.2.1.31.1.1.1.1.3 = STRING: "enc0"
#iso.3.6.1.2.1.31.1.1.1.1.4 = STRING: "lo0"
#iso.3.6.1.2.1.31.1.1.1.1.5 = STRING: "pflog0"
#iso.3.6.1.2.1.31.1.1.1.1.6 = STRING: "pfsync0"#
#iso.3.6.1.2.1.31.1.1.1.2.1 = Counter32: 21374  <-- Begin ifInMulticastPkts
#iso.3.6.1.2.1.31.1.1.1.2.2 = Counter32: 29570
#iso.3.6.1.2.1.31.1.1.1.2.3 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.2.4 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.2.5 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.2.6 = Counter32: 0 <-- End ifInMulticastPkts
#iso.3.6.1.2.1.31.1.1.1.3.1 = Counter32: 0 <-- Begin ifInBroadcastPkts
#iso.3.6.1.2.1.31.1.1.1.3.2 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.3.3 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.3.4 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.3.5 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.3.6 = Counter32: 0 <-- End ifInBroadcastPkts
#iso.3.6.1.2.1.31.1.1.1.4.1 = Counter32: 6 <-- Begin ifOutMulticastPkts
#iso.3.6.1.2.1.31.1.1.1.4.2 = Counter32: 5
#iso.3.6.1.2.1.31.1.1.1.4.3 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.4.4 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.4.5 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.4.6 = Counter32: 0 <-- End ifOutMulticastPkts
#iso.3.6.1.2.1.31.1.1.1.5.1 = Counter32: 0 <-- Begin ifOutBroadcastPkts
#iso.3.6.1.2.1.31.1.1.1.5.2 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.5.3 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.5.4 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.5.5 = Counter32: 0
#iso.3.6.1.2.1.31.1.1.1.5.6 = Counter32: 0 <-- End ifOutBroadcastPkts
#iso.3.6.1.2.1.31.1.1.1.6.1 = Counter64: 26006348139 <--- em0 in-octets
#iso.3.6.1.2.1.31.1.1.1.6.2 = Counter64: 9205906507  <--- em1 in-octets      !!! Used in this script by way of example
#iso.3.6.1.2.1.31.1.1.1.7.1 = Counter64: 20027195
#iso.3.6.1.2.1.31.1.1.1.7.2 = Counter64: 11609973
#iso.3.6.1.2.1.31.1.1.1.8.1 = Counter64: 21374
#iso.3.6.1.2.1.31.1.1.1.8.2 = Counter64: 29570 <--- End 
#iso.3.6.1.2.1.31.1.1.1.9.1 = Counter64: 0
#iso.3.6.1.2.1.31.1.1.1.9.2 = Counter64: 0
#iso.3.6.1.2.1.31.1.1.1.10.1 = Counter64: 9134872256  <--- em0 out-octets   
#iso.3.6.1.2.1.31.1.1.1.10.2 = Counter64: 26020039451 <--- em1 out-octets    !!! Used in this script by way of example
#iso.3.6.1.2.1.31.1.1.1.11.1 = Counter64: 11443662
#iso.3.6.1.2.1.31.1.1.1.11.2 = Counter64: 20180393
#iso.3.6.1.2.1.31.1.1.1.12.1 = Counter64: 6
#iso.3.6.1.2.1.31.1.1.1.12.2 = Counter64: 5
#iso.3.6.1.2.1.31.1.1.1.13.1 = Counter64: 0
#iso.3.6.1.2.1.31.1.1.1.13.2 = Counter64: 0
#iso.3.6.1.2.1.31.1.1.1.14.1 = INTEGER: 1
#iso.3.6.1.2.1.31.1.1.1.14.2 = INTEGER: 1
#iso.3.6.1.2.1.31.1.1.1.14.3 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.14.4 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.14.5 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.14.6 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.15.1 = Gauge32: 1000 <--- em0 interface speed (1000 = 1Gbps)
#iso.3.6.1.2.1.31.1.1.1.15.2 = Gauge32: 1000 <--- em1 interface speed (1000 = 1Gbps)
#iso.3.6.1.2.1.31.1.1.1.15.3 = Gauge32: 0
#iso.3.6.1.2.1.31.1.1.1.15.4 = Gauge32: 0
#iso.3.6.1.2.1.31.1.1.1.15.5 = Gauge32: 0
#iso.3.6.1.2.1.31.1.1.1.15.6 = Gauge32: 0
#iso.3.6.1.2.1.31.1.1.1.16.1 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.16.2 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.16.3 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.16.4 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.16.5 = INTEGER: 1
#iso.3.6.1.2.1.31.1.1.1.16.6 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.17.1 = INTEGER: 1
#iso.3.6.1.2.1.31.1.1.1.17.2 = INTEGER: 1
#iso.3.6.1.2.1.31.1.1.1.17.3 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.17.4 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.17.5 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.17.6 = INTEGER: 2
#iso.3.6.1.2.1.31.1.1.1.18.1 = ""
#iso.3.6.1.2.1.31.1.1.1.18.2 = ""
#iso.3.6.1.2.1.31.1.1.1.18.3 = ""
#iso.3.6.1.2.1.31.1.1.1.18.4 = ""
#iso.3.6.1.2.1.31.1.1.1.18.5 = ""
#iso.3.6.1.2.1.31.1.1.1.18.6 = ""
#iso.3.6.1.2.1.31.1.1.1.19.1 = Timeticks: (0) 0:00:00.00
#iso.3.6.1.2.1.31.1.1.1.19.2 = Timeticks: (0) 0:00:00.00
#iso.3.6.1.2.1.31.1.1.1.19.3 = Timeticks: (0) 0:00:00.00
#iso.3.6.1.2.1.31.1.1.1.19.4 = Timeticks: (0) 0:00:00.00
#iso.3.6.1.2.1.31.1.1.1.19.5 = Timeticks: (0) 0:00:00.00
#iso.3.6.1.2.1.31.1.1.1.19.6 = Timeticks: (0) 0:00:00.00
