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

def can_ping(host):
    """Return True if host responds to a ping request, otherwise False."""
    try:
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
                   UdpTransportTarget((target, 161), timeout=1, retries=0),
                   ContextData(),
                   ObjectType(ObjectIdentity('1.3.6.1.2.1.1.1.0')))
        )
        if errorIndication or errorStatus:
            return False
        return True
    except Exception:
        return False

def snmp_fetch(pipe):
    prev_time = time.time()
    prev_in = fetch_snmp_data(INTERFACE_OID_IN)
    prev_out = fetch_snmp_data(INTERFACE_OID_OUT)

    while True:
        # Check connectivity to SNMP target
        while not can_ping(SNMP_TARGET):
            handle_error(pipe, "UHH")
            time.sleep(POLL_INTERVAL)

        # Check SNMP availability on the target
        while not can_snmp(SNMP_TARGET, SNMP_V2_COMMUNITY):
            handle_error(pipe, "UHH")
            time.sleep(POLL_INTERVAL)

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

        time.sleep(POLL_INTERVAL)

def snmp_fetch_thread(prev_values):
    while True:
        # Check connectivity to SNMP target
        while not can_ping(SNMP_TARGET):
            time.sleep(POLL_INTERVAL)

        # Check SNMP availability on the target
        while not can_snmp(SNMP_TARGET, SNMP_V2_COMMUNITY):
            time.sleep(POLL_INTERVAL)

        prev_values["current_time"] = time.time()

        prev_values["current_in"] = fetch_snmp_data(INTERFACE_OID_IN)
        prev_values["current_out"] = fetch_snmp_data(INTERFACE_OID_OUT)

        time.sleep(POLL_INTERVAL)

def fetch_snmp_data(oid):
    print(f"Fetching SNMP data for OID: {oid}")  # Debugging
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
               CommunityData(SNMP_V2_COMMUNITY),
               UdpTransportTarget((SNMP_TARGET, 161)),
               ContextData(),
               ObjectType(ObjectIdentity(oid)))
    )
    if errorIndication:
        print(f"Error indication: {errorIndication}")  # Debugging
    elif errorStatus:
        print(f"Error status: {errorStatus.prettyPrint()} at {varBinds[int(errorIndex)-1] if errorIndex else '?'}")  # Debugging
    else:
        for varBind in varBinds:
            print(f"Fetched data: {varBind[1]}")  # Debugging
            return int(varBind[1])

def get_fuzzed_value(true_value):
    """Generate a value that's within 5% of the true_value."""
    fuzz_factor = random.uniform(0.95, 1.05)
    return true_value * fuzz_factor

def format_bps(value):
    if value >= 10**9:  # Gbps
        val = value / 10**9
        if val >= 10:  # If value is 10Gbps or more, restrict to 9.9G
            return "9.9G"
        else:
            return f"{val:.1f}G"
    elif value >= 10**6:  # Mbps
        val = value / 10**6
        if val >= 100:
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

def snmp_fetch(pipe):
    while True:
        while not can_ping(SNMP_TARGET):
            handle_error(pipe, "UHH")
            time.sleep(POLL_INTERVAL)

        while not can_snmp(SNMP_TARGET, SNMP_V2_COMMUNITY):
            handle_error(pipe, "UHH")
            time.sleep(POLL_INTERVAL)

        # ... rest of your logic for the thread ...

def snmp_child(pipe=None):
    # Initialize prev_* variables outside the loop
    prev_time = time.time()
    prev_in = fetch_snmp_data(INTERFACE_OID_IN)
    prev_out = fetch_snmp_data(INTERFACE_OID_OUT)
    in_rate = (prev_in - 0) * 8  # Initializing in_rate
    out_rate = (prev_out - 0) * 8  # Initializing out_rate
    total_bps = in_rate + out_rate  # Initialize total_bps
    data_ready = False

    # If it's the first data fetch, we'll send "SNP" for the display
    first_fetch = True

    last_non_zero_fuzzed_bps = 0

    # Shared dictionary to store values
    prev_values = {
        "current_time": prev_time,
        "current_in": prev_in,
        "current_out": prev_out,
    }

    # Start the SNMP fetch thread
    snmp_thread = threading.Thread(target=snmp_fetch_thread, args=(prev_values,))
    snmp_thread.start()

    while True:
        # Check if the snmp_fetch_thread has updated the values
        if prev_values["current_time"] != prev_time:
            actual_interval = prev_values["current_time"] - prev_time

            if actual_interval > 0:
                new_in_rate = (prev_values["current_in"] - prev_in) * 8 / actual_interval
                new_out_rate = (prev_values["current_out"] - prev_out) * 8 / actual_interval
                new_total_bps = new_in_rate + new_out_rate
            else:
                # Here you can decide how to handle the case when actual_interval is 0.
                # For example, you could use the previous values:
                new_in_rate = (prev_values["current_in"] - prev_in) * 8
                new_out_rate = (prev_values["current_out"] - prev_out) * 8
                new_total_bps = new_in_rate + new_out_rate

            # Check if either in_rate or out_rate are zero, or if they're both None.
            # If any of these conditions are met, we'll keep the previous total_bps.
            if new_in_rate == 0 or new_out_rate == 0 or (new_in_rate is None and new_out_rate is None):
                total_bps = total_bps  # essentially does nothing, but makes it clear in the code
            else:
                in_rate = new_in_rate
                out_rate = new_out_rate
                total_bps = new_total_bps
            if first_fetch:
                formatted_total = "SNP"
                first_fetch = False
            else:
                formatted_total = format_bps(total_bps)

            data_to_send = {
                'data': formatted_total,
                'debug': f"Raw in: {prev_values['current_in']}, Raw out: {prev_values['current_out']}, Interval: {actual_interval:.2f}s, "
                         f"In rate: {in_rate:.2f}, Out rate: {out_rate:.2f}, Total rate: {formatted_total}",
            }

            if pipe:
                pipe.send(data_to_send)
            else:
                print(data_to_send['debug'])

            # Update previous values for the next iteration
            prev_in = prev_values["current_in"]
            prev_out = prev_values["current_out"]
            prev_time = prev_values["current_time"]

        # Send fuzzed values ONLY if first_fetch is False
        if not first_fetch:
            for _ in range(int(POLL_INTERVAL * 10)):  # 10 fuzzed values every second for the entire POLL_INTERVAL
                time.sleep(0.1)  # Update every 100ms
                fuzzed_bps = get_fuzzed_value(total_bps)
                # Check if fuzzed_bps is zero, make it the last non-zero value
                if fuzzed_bps == "0":
                    fuzzed_bps = last_non_zero_fuzzed_bps
                else:
                    last_non_zero_fuzzed_bps = fuzzed_bps

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
    snmp_child()