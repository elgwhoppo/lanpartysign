# 1.0 J. Clarke Initial release, dumps snmp data to a text files

from pysnmp.hlapi import *
from datetime import datetime
import urllib2
import time
import math
import os

# what IP should I check for SNMP counters? 
#snmptarget = "192.168.1.157" #Unifi 16 port switch
snmptarget = "192.168.1.1" #UDM-PRO Wad
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

def getsnmpbw():
    global octetsOLDout,timeOLDout,octetsOLDin,timeOLDin,snmpdelaycounter,snmphealth,int1in,int1out
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
    print "Raw int1out SNMP string: ",int1out
    # Take only to the right of the space equals space in the MIB finding
    int1out = int1out.split(' = ')[1]
	
    print "Cleaned up intlout 1: ",int1out
    #convert to integer
    int1out = int(int1out)
    print "Cleaned up intlout 2: ",int1out
    changedbitsout = (int1out - octetsOLDout)
    timedeltaout = (currenttimeout - timeOLDout)
    changedbitsout = abs(changedbitsout)
	
	# IN METRICS
	# Turn var into a string
    int1in = str(int1in)
    print "Raw int1out SNMP string: ",int1in

    # Take only to the right of the space equals space in the MIB finding	
    int1in = int1in.split(' = ')[1]
	
    print "Cleaned up intlin 1: ",int1in
	#exmple:   SNMPv2-SMI::mib-2.31.1.1.1.6.2 = 18417094860
	#example from UDM-PRO has 31 characters: SNMPv2-SMI::mib-2.2.2.1.16.4 = 3542493243
    #convert to integer
    int1in = int(int1in)
    print "Cleaned up intlin 2: ",int1in
    changedbitsin = (int1in - octetsOLDin)
    timedeltain = (currenttimein - timeOLDin)
    changedbitsin = abs(changedbitsin)


	#calculate bits per second
    ifoutbytespersecond = changedbitsout/timedeltaout
    #print("ifoutbytespersecond = ",ifoutbytespersecond)
    ifinbytespersecond = changedbitsin/timedeltain
    #print("ifinbytespersecond = ",ifinbytespersecond)
    ifbytespersecond = ifoutbytespersecond+ifinbytespersecond
    #print("ifbytespersecond = ",ifbytespersecond)
    ifoutbitspersecond = ifoutbytespersecond*8
    #print("ifoutbitspersecond = ",ifoutbitspersecond)
    ifinbitspersecond = ifinbytespersecond*8
    #print("ifinbitspersecond = ",ifinbitspersecond)
    ifbitspersecond = ifinbitspersecond+ifoutbitspersecond
    ifbitspersecond = int(round(ifbitspersecond))
    ifKbitspersecond = ifbitspersecond/1000
    ifMbitspersecond = ifKbitspersecond/1000
    ifGbitspersecond = ifMbitspersecond/1000
    ifGbitspersecond = round(ifGbitspersecond,1)
    print "---------------------------------------------------"
    print "ifinbitspersecond -----> " + str(ifinbitspersecond)
    print "ifoutbitspersecond ----> " + str(ifoutbitspersecond)
    print "ifbitspersecond -------> " + str(ifbitspersecond)
    print "---------------------------------------------------"
    print "ifKbitspersecond ---> " + str(ifKbitspersecond)
    print "ifMbitspersecond ---> " + str(ifMbitspersecond)
    print "ifGbitspersecond ---> " + str(ifGbitspersecond)
    print "---------------------------------------------------"
	
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


def getsnmp():
# trying to get better error handling for no internet/snmp
#    snmptargetonline()
#    iptopingonline()
#    print iptopingstatus
#    print snmptargetpingstatus
#    pwmsetup()
#    dothething()
    bps = getsnmpbw()
    print bps
    bpsfile = open("bps.txt", "w")
    bpsstr = str(bps)
    bpsfile.write(bpsstr)
    bpsfile.close()

while True:
    try:
       getsnmp()
    except KeyboardInterrupt:
	   sys.exit()

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
