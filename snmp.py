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
POLL_INTERVAL = 5  # seconds

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
    
def handle_error(pipe, message):
    if pipe:
        pipe.send("UHH")
    else:
        print(message)
    time.sleep(POLL_INTERVAL)

def snmp_child(pipe=None):
    while True:
        # Check connectivity to SNMP target
        while not can_ping(SNMP_TARGET):
            handle_error(pipe, "UHH")
            time.sleep(POLL_INTERVAL)

        # Check SNMP availability on the target
        while not can_snmp(SNMP_TARGET, SNMP_V2_COMMUNITY):
            handle_error(pipe, "UHH")
            time.sleep(POLL_INTERVAL)

        # Let's fetch the time and SNMP data once before entering the loop.
        prev_time = time.time()
        prev_in = fetch_snmp_data(INTERFACE_OID_IN)
        prev_out = fetch_snmp_data(INTERFACE_OID_OUT)

        try:
            # Once both checks pass, enter this inner loop to continuously fetch SNMP data
            while True:
                start_time = time.time()  # record start time of this iteration

                current_time = time.time()
                actual_interval = current_time - prev_time

                current_in = fetch_snmp_data(INTERFACE_OID_IN)
                current_out = fetch_snmp_data(INTERFACE_OID_OUT)

                in_rate = (current_in - prev_in) * 8 / actual_interval
                out_rate = (current_out - prev_out) * 8 / actual_interval

                total_bps = in_rate + out_rate
                formatted_total = format_bps(total_bps)

                data_to_send = {
                    'data': formatted_total,
                    'debug': f"Raw in: {current_in}, Raw out: {current_out}, Interval: {actual_interval:.2f}s, "
                             f"In rate: {in_rate:.2f}, Out rate: {out_rate:.2f}, Total rate: {formatted_total}",
                }

                if pipe:
                    pipe.send(data_to_send)
                else:
                    print(data_to_send['debug'])

                # Save the current values as the previous values for the next iteration.
                prev_in, prev_out, prev_time = current_in, current_out, current_time

                end_time = time.time()  # record end time of this iteration
                elapsed_time = end_time - start_time  # find out how long it took
                sleep_time = POLL_INTERVAL - elapsed_time  # adjust sleep time

                if sleep_time > 0:  # Only sleep if there's time remaining in the desired interval
                    time.sleep(sleep_time)

        except (socket.error, pysnmp.error.PySnmpError, pysnmp.carrier.error.CarrierError):
            handle_error(pipe, "UHH")
            continue
        
        except Exception as e:
            handle_error(pipe, "UHH")
            continue


if __name__ == '__main__':
#    parent_conn, child_conn = Pipe()
#    snmp_child()  # Call snmp_child directly when running the script standalone
    while True:
        print(snmp_child())
        time.sleep(1)