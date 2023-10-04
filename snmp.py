from pysnmp.hlapi import *
import time
import subprocess
import os
import pysnmp.error
import pysnmp.carrier.error
import re
import socket 
from multiprocessing import Pipe

SNMP_TARGET = "192.168.1.40"
SNMP_V2_COMMUNITY = "public"
INTERFACE_OID_IN = "1.3.6.1.2.1.31.1.1.1.6.1"
INTERFACE_OID_OUT = "1.3.6.1.2.1.31.1.1.1.10.1"
SNMP_UPTIME_OID = "1.3.6.1.2.1.31.1.1.1.10.1"
POLL_INTERVAL = 2  # seconds

def fetch_snmp_data(oid):
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
               CommunityData(SNMP_V2_COMMUNITY),
               UdpTransportTarget((SNMP_TARGET, 161)),
               ContextData(),
               ObjectType(ObjectIdentity(oid)))
    )
    if errorIndication:
        print(errorIndication)
    elif errorStatus:
        print('%s at %s' % (errorStatus.prettyPrint(), varBinds[int(errorIndex)-1] if errorIndex else '?'))
    else:
        for varBind in varBinds:
            return int(varBind[1])

def can_ping(host):
    """Return True if host responds to a ping request, otherwise False."""
    try:
        # The '-c 1' means only send one packet. Adjust as needed.
        # The '-W 1' means to wait 1 second for a response.
        subprocess.check_output(["ping", "-c", "1", "-W", "1", host])
        return True
    except subprocess.CalledProcessError:
        return False
    
def can_snmp(target, community):
    """Return True if SNMP response can be retrieved from target, otherwise False."""
    try:
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(SnmpEngine(),
                   CommunityData(community),
                   UdpTransportTarget((target, 161), timeout=1, retries=0),  # adding short timeout and no retries for quick check
                   ContextData(),
                   ObjectType(ObjectIdentity('1.3.6.1.2.1.1.1.0')))  # sysDescr OID
        )
        if errorIndication or errorStatus:
            return False
        return True
    except Exception:
        return False

def format_bps(value):
    if value >= 10**9:  # Gbps
        val = value / 10**9
        if val >= 10:  # If value is 10Gbps or more, restrict to 9.9G
            return "9.9G"
        else:
            return f"{val:.1f}G"
    elif value >= 10**6:  # Mbps
        val = value / 10**6
        if val >= 100:  # If in hundreds, show whole number
            return f"{int(val)}"
        else:
            return f"{val:.2f}"
    elif value >= 10**3:  # Kbps
        val = value / 10**3
        return f"{int(val)}" if val.is_integer() else f"{val:.2f}"
    else:
        return f"{int(value)}" if value.is_integer() else f"{value:.2f}"

def snmp_child(pipe=None):
    while True:
        if not can_ping(SNMP_TARGET):
            if pipe:
                pipe.send("UHH")
            else:
                print("UHH")
            time.sleep(POLL_INTERVAL)  # Let's not spam the ping requests.
            continue
        elif not can_snmp(SNMP_TARGET, SNMP_V2_COMMUNITY):
            if pipe:
                pipe.send("UHH")
            else:
                print("UHH")
            time.sleep(POLL_INTERVAL)  # Let's not spam the SNMP requests.
            continue
        try:
            prev_in = fetch_snmp_data(INTERFACE_OID_IN)
            prev_out = fetch_snmp_data(INTERFACE_OID_OUT)
            time.sleep(POLL_INTERVAL)

            current_in = fetch_snmp_data(INTERFACE_OID_IN)
            current_out = fetch_snmp_data(INTERFACE_OID_OUT)

            in_rate = (current_in - prev_in) * 8 / POLL_INTERVAL  # convert bytes to bits
            out_rate = (current_out - prev_out) * 8 / POLL_INTERVAL

            total_bps = in_rate + out_rate
            formatted_total = format_bps(total_bps)

            print(f"SNMP Data: {formatted_total}")
            if pipe:
                pipe.send(formatted_total)
            else:
                print(formatted_total)  # print directly if running standalone

            prev_in, prev_out = current_in, current_out
            time.sleep(POLL_INTERVAL)

        except (socket.error, pysnmp.error.PySnmpError, pysnmp.carrier.error.CarrierError, Exception):
            if pipe:
                pipe.send("UHH")  # or some other placeholder/error value
                os._exit(1)
            else:
                print("UHH")
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            if pipe:
                pipe.send("UHH")
                os._exit(1)
            else:
                print("UHH")
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
#    parent_conn, child_conn = Pipe()
#    snmp_child()  # Call snmp_child directly when running the script standalone
    while True:
        print(snmp_child())
        time.sleep(1)