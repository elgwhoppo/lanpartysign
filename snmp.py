# 1.0 J. Clarke Initial release, dumps snmp data to a text files

from pysnmp.hlapi import *
from datetime import datetime
import urllib2
import time
import math
import os

# what IP should I check for SNMP counters? 
#snmptarget = "192.168.1.157" #Unifi 16 port switch
#snmptarget = "192.168.1.1" #UDM-PRO Wad
snmptarget = "10.10.0.1" #UDM-PRO Litchfield
#snmptarget = "10.11.12.2" #Dlink-DGS-1510-28X

iptoping = "8.8.8.8" #Google DNS IP-Anycast

# pick a dma channel that won't crash your raspberry pi
dmach = 14

# define pulswidth in microseconds
# do not exceed 330 with 6 digits.  "night mode" can be 115
pulsewidth = 330

# define how often to fetch data and ping in milliseconds (e.g. 1000 = 1 second)
fetchrate = 750

#Variable Declaration IfOutOctets and IfInOctets- Modify to fit your environment

#UDM-PRO SE WAN Interface ifInOctets.5, AKA Ethernet WAN interface
#interfaceOIDout = "1.3.6.1.2.1.2.2.1.16.5"
#interfaceOIDin = "1.3.6.1.2.1.2.2.1.10.5"

#Trying ifInOctets.15
interfaceOIDin = "1.3.6.1.2.1.2.2.1.10.15"
interfaceOIDout = "1.3.6.1.2.1.2.2.1.16.15"


#UDM-PRO WAN Interface
#interfaceOIDout = "1.3.6.1.2.1.2.2.1.16.4" #ifIndex.4
#interfaceOIDin = "1.3.6.1.2.1.2.2.1.10.4" #ifIndex.4

#USG-PRO-4
#interfaceOIDout = "1.3.6.1.2.1.2.2.1.16.4" #USG-PRO-4 WAN1 config
#interfaceOIDin = "1.3.6.1.2.1.2.2.1.10.4"  #USG-PRO-4 WAN1 config

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
snmpv2community = "forgetown"

#Initial Variable Assignment - don't touch
octetsOLDout = 0
timeOLDout = 0
octetsOLDin = 0
timeOLDin = 0
bps = 0
snmpdelaycounter = 0
int1out = None

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
            time.sleep(2)
            return(errorIndication)
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
    try: 
       int1out = int1out.split(' = ')[1]
    except Exception as e:
        print("An error occurred:", str(e))
	
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
    # TESTING ONLY: Make it more
    #ifbitspersecond = ifbitspersecond * 100
    # Calculate breakdown 
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

    # Return the variable from the function	
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

def check_snmp_connectivity():
    # SNMP parameters
    snmp_target = '10.10.0.1'
    community_string = 'forgetown'
    snmp_oid = '1.3.6.1.2.1.1.1.0'  # Example OID for system description
    
    # Create an SNMP engine
    snmp_engine = SnmpEngine()
    
    try:
        # Create an SNMP GET request
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(
                snmp_engine,
                CommunityData(community_string),
                UdpTransportTarget((snmp_target, 161)),
                ContextData(),
                ObjectType(ObjectIdentity(snmp_oid))
            )
        )
        
        # Check for errors
        if errorIndication:
            print("SNMP Error:", errorIndication)
            return 0
        elif errorStatus:
            print("SNMP Error:", errorStatus.prettyPrint())
            return 0 
        else:
            print("SNMP Data:", varBinds[0].prettyPrint())
            return 1
    
    except Exception as e:
        print("An error occurred:", str(e))
        return 0

# Call the function to check SNMP connectivity
#check_snmp_connectivity()


# Get SNMP and main function 
def getsnmp():
    bps = getsnmpbw()
    print bps
    bpsfile = open("bps.txt", "w")
    bpsstr = str(bps)
    bpsfile.write(bpsstr)
    bpsfile.close()
# Loop forever 
while True:
    try:
        snmpworkingrn = check_snmp_connectivity()
        if snmpworkingrn == 1: 
            getsnmp()
        else: 
            print ("SNMP isn't working right now. Sleeping for 10 seconds and repeating...")
            time.sleep(10)
    except KeyboardInterrupt:
        sys.exit()

