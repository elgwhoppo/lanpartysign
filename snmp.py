from pysnmp.hlapi import *
import time
import subprocess
import os
import pysnmp.error
import pysnmp.carrier.error
import re
import random
import socket 
from multiprocessing import Pipe
import threading

SNMP_TARGET = "192.168.1.40"
SNMP_V2_COMMUNITY = "public"
INTERFACE_OID_IN = "1.3.6.1.2.1.31.1.1.1.6.1"
INTERFACE_OID_OUT = "1.3.6.1.2.1.31.1.1.1.10.1"
SNMP_UPTIME_OID = "1.3.6.1.2.1.31.1.1.1.10.1"
POLL_INTERVAL = 15  # seconds

# Shared data structure for the raw SNMP data
raw_data_lock = threading.Lock()
raw_data = {
    "in_rate": 0,
    "out_rate": 0,
    "current_in": 0,
    "current_out": 0,
    "actual_interval": 0
}

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

# ... [rest of your functions] ...

def snmp_fetch():
    global raw_data
    
    while True:
        # Your existing SNMP fetching logic here
        
        # Check connectivity to SNMP target
        while not can_ping(SNMP_TARGET):
            handle_error(None, "UHH")
            time.sleep(POLL_INTERVAL)

        # Check SNMP availability on the target
        while not can_snmp(SNMP_TARGET, SNMP_V2_COMMUNITY):
            handle_error(None, "UHH")
            time.sleep(POLL_INTERVAL)

        prev_time = time.time()
        prev_in = fetch_snmp_data(INTERFACE_OID_IN)
        prev_out = fetch_snmp_data(INTERFACE_OID_OUT)

        current_time = time.time()
        actual_interval = current_time - prev_time

        current_in = fetch_snmp_data(INTERFACE_OID_IN)
        current_out = fetch_snmp_data(INTERFACE_OID_OUT)

        in_rate = (current_in - prev_in) * 8 / actual_interval
        out_rate = (current_out - prev_out) * 8 / actual_interval

        # Update shared raw_data
        with raw_data_lock:
            raw_data["in_rate"] = in_rate
            raw_data["out_rate"] = out_rate
            raw_data["current_in"] = current_in
            raw_data["current_out"] = current_out
            raw_data["actual_interval"] = actual_interval

        time.sleep(POLL_INTERVAL)

def snmp_child(pipe=None):
    snmp_thread = threading.Thread(target=snmp_fetch)
    snmp_thread.start()

    while True:
        # Now, we'll get the raw data from the shared structure
        with raw_data_lock:
            total_bps = raw_data["in_rate"] + raw_data["out_rate"]
            current_in = raw_data["current_in"]
            current_out = raw_data["current_out"]
            actual_interval = raw_data["actual_interval"]

        formatted_total = format_bps(total_bps)
        data_to_send = {
            'data': formatted_total,
            'debug': f"Raw in: {current_in}, Raw out: {current_out}, Interval: {actual_interval:.2f}s, "
                     f"In rate: {raw_data['in_rate']:.2f}, Out rate: {raw_data['out_rate']:.2f}, Total rate: {formatted_total}",
        }

        if pipe:
            pipe.send(data_to_send)
        else:
            print(data_to_send['debug'])

        # Continue with your fuzzing logic
        for _ in range(int(POLL_INTERVAL * 10)):  # 10 fuzzed values every second for the entire POLL_INTERVAL
            time.sleep(0.1)  # Update every 100ms
            fuzzed_bps = get_fuzzed_value(total_bps)
            formatted_fuzzed_total = format_bps(fuzzed_bps)
            
            data_to_send_fuzzed = {
                'data': formatted_fuzzed_total,
                'debug': f"Fuzzed Value: {formatted_fuzzed_total}"
            }

            if pipe:
                pipe.send(data_to_send_fuzzed)
            else:
                print(data_to_send_fuzzed['debug'])

if __name__ == '__main__':
    while True:
        print(snmp_child())
        time.sleep(1)
