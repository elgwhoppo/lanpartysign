from pysnmp.hlapi import *
import time
import threading
import sys
import random
from multiprocessing.connection import Connection


# Constants
SNMP_TARGET = "192.168.1.40"
SNMP_V2_COMMUNITY = "public"
INTERFACE_OID_IN = "1.3.6.1.2.1.31.1.1.1.6.1"
INTERFACE_OID_OUT = "1.3.6.1.2.1.31.1.1.1.10.1"
SYSTEM_DESCRIPTION_OID = "1.3.6.1.2.1.1.1.0"
POLL_INTERVAL = 15  # seconds
ERROR_RESPONSE = "UHH"

def snmp_threaded_fetch(shared_data, lock, stop_thread_event):
    consecutive_failures = 0
    last_seen_values = {INTERFACE_OID_IN: None, INTERFACE_OID_OUT: None}
    last_timestamp = time.time()
    
    while not stop_thread_event.is_set():
        current_timestamp = time.time()
        elapsed_time = current_timestamp - last_timestamp
        current_values = {}
        total_delta = 0  # To keep track of the total change in counter values
        
        for oid in [INTERFACE_OID_IN, INTERFACE_OID_OUT, SYSTEM_DESCRIPTION_OID]:
            errorIndication, errorStatus, errorIndex, varBinds = next(
                getCmd(SnmpEngine(),
                       CommunityData(SNMP_V2_COMMUNITY),
                       UdpTransportTarget((SNMP_TARGET, 161)),
                       ContextData(),
                       ObjectType(ObjectIdentity(oid)))
            )
            value = None if errorIndication or errorStatus else str(varBinds[0][1])
            #print(f"[DEBUG] Fetched for OID {oid}: {value}")

            if not value or value == "0":
                current_values[oid] = ERROR_RESPONSE if consecutive_failures >= 5 else last_seen_values.get(oid, ERROR_RESPONSE)
                consecutive_failures += 1
                print(f"[WARN] Failed to fetched value for OID {oid}")
            else:
                current_values[oid] = value
                consecutive_failures = 0


            if oid in [INTERFACE_OID_IN, INTERFACE_OID_OUT] and last_seen_values[oid] is not None and current_values[oid] != ERROR_RESPONSE:
                # calculate delta between current and last values
                delta = int(current_values[oid]) - int(last_seen_values[oid])
                total_delta += delta
                print(f"[DEBUG] Delta for OID {oid}: {delta} Total Delta so far: {total_delta}")

        # Now, let's calculate the combined bps using total_delta
        combined_bps = (total_delta * 8) / elapsed_time  # Multiply by 8 to convert bytes to bits
        combined_bps = round(combined_bps)

        print(f"[DEBUG] Combined bps: {combined_bps}")
        current_values["combined_bps"] = combined_bps
        


        for key, value in current_values.items():
            if value != ERROR_RESPONSE:
                last_seen_values[key] = value
        last_timestamp = current_timestamp

        with lock:
            shared_data.update(current_values)
        stop_thread_event.wait(POLL_INTERVAL)

def format_bps(value):
    """Format the value to appropriate units (Bps, Kbps, Mbps, Gbps). Feed it bps, it'll return a string."""
    if value is None or not isinstance(value, (int, float)):
        return ERROR_RESPONSE
    if value >= 10**9:  # Gbps
        val = value / 10**9
        return f"{val:.1f}G" if val < 10 else "9.9G"
    elif value >= 10**6:  # Mbps
        val = value / 10**6
        return f"{val:.2f}" if val < 100 else str(int(val))
    elif value >= 10**3:  # Kbps
        val = value / 10**3
        return f"{val:.2f}" if not val.is_integer() else str(int(val))
    else:
        return str(value) if not float(value).is_integer() else str(int(value))

def get_fuzzed_value(true_value):
    """Generate a random value that's within 5% of the true_value."""
    if true_value is None or not isinstance(true_value, (int, float)):
        return true_value  # Basically just give it back if it's not an int, float, or None
    
    fuzz_factor = random.uniform(0.98, 1.02)
    #print(f"True Value: {true_value}, Fuzz Factor: {fuzz_factor}, Result: {true_value * fuzz_factor}")
    return round(true_value * fuzz_factor)


def snmp_child(pipe_conn=None):
    # Main program
    shared_data = {}
    lock = threading.Lock()

    interface_in = ""
    counter = 0

    # Create stop event
    stop_thread_event = threading.Event()

    # Start the snmp thread
    thread = threading.Thread(target=snmp_threaded_fetch, args=(shared_data, lock, stop_thread_event))
    thread.start()



    # Periodically read the shared_data
    try: 
        while True:  

            with lock:
        # Extract data from shared_data
                interface_in = shared_data.get(INTERFACE_OID_IN)
                interface_out = shared_data.get(INTERFACE_OID_OUT)
                system_description = shared_data.get(SYSTEM_DESCRIPTION_OID)
                current_bps = shared_data.get("combined_bps")
                #print(f"[MAIN THREAD] Interface IN: {interface_in}")
                #print(f"[MAIN THREAD] Interface OUT: {interface_out}")
                #print(f"[MAIN THREAD] System description: {system_description}")
                #print(f"[MAIN THREAD] Current bps: {current_bps}")
                current_bps = get_fuzzed_value(current_bps)
                #print(f"[MAIN THREAD] Fuzzed bps: {current_bps}")
                current_bps = format_bps(current_bps)
                # If the system description is "UHH", then we know that the SNMP thread has encountered an error
                current_bps = ERROR_RESPONSE if system_description == "UHH" else current_bps

                counter += 1
                if counter % 50 == 0:
                    print(f"[MAIN THREAD] 50 iterations of snmp.py have passed. Current output of snmp.py to sign.py: {current_bps}")

                #print(f"[MAIN THREAD] Current output of script to sign.py: {current_bps}")
        
            #sleep here instead
            data_to_send = {
                'data': current_bps
            }
            if pipe_conn:  # Check if pipe_conn is not None
                pipe_conn.send(data_to_send)
            time.sleep(.08)
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Stopping thread...")
        stop_thread_event.set()  # Signal the thread to stop
        thread.join()  # Wait for the thread to actually stop
        print("Thread stopped. Exiting.")

if __name__ == "__main__":
    snmp_child()  # This will run the function without a pipe when the script is executed standalone.
