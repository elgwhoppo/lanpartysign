import time
from pysnmp.hlapi import *

# had to downgrade pysnmp to 4.4.6

SNMP_TARGET = "192.168.1.40"
SNMP_V2_COMMUNITY = "public"
INTERFACE_OID_IN = "1.3.6.1.2.1.31.1.1.1.6.1"
INTERFACE_OID_OUT = "1.3.6.1.2.1.31.1.1.1.10.1"
BPS_FILE_PATH = "/home/pi/lanpartysign/bps.txt"

# Initialize previous values
prev_in_value = 0
prev_out_value = 0
prev_time = time.time()

def fetch_oid_value(oid):
    errorIndication, errorStatus, _, varBinds = next(
        getCmd(SnmpEngine(),
               CommunityData(SNMP_V2_COMMUNITY),
               UdpTransportTarget((SNMP_TARGET, 161)),
               ContextData(),
               ObjectType(ObjectIdentity(oid)))
    )
    if errorIndication or errorStatus:
        print("Error fetching OID:", errorIndication or errorStatus)
        return None
    return int(varBinds[0][1])

while True:
    current_time = time.time()
    time_interval = current_time - prev_time

    in_value = fetch_oid_value(INTERFACE_OID_IN)
    out_value = fetch_oid_value(INTERFACE_OID_OUT)

    print("Fetched values: IN =", in_value, "OUT =", out_value)

    if in_value is None or out_value is None:
        print("One of the values is None. Sleeping for a second...")
        time.sleep(1)
        continue

    in_diff = in_value - prev_in_value
    out_diff = out_value - prev_out_value

    bps_in = in_diff / time_interval
    bps_out = out_diff / time_interval

    total_bps = bps_in + bps_out

    print("Calculated bps: IN =", bps_in, "bps, OUT =", bps_out, "bps. TOTAL =", total_bps, "bps")

    with open(BPS_FILE_PATH, 'w') as f:
        f.write(str(int(total_bps)))
        print("Written total bps to file:", BPS_FILE_PATH)

    # Store current values for next iteration
    prev_in_value = in_value
    prev_out_value = out_value
    prev_time = current_time

    print("Sleeping for 1 second...")
    time.sleep(1)