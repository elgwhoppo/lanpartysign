from pysnmp.hlapi import *
import subprocess
import re
import time
from multiprocessing import Pipe

SNMP_TARGET = "192.168.1.40"
SNMP_V2_COMMUNITY = "public"
INTERFACE_OID_IN = "1.3.6.1.2.1.31.1.1.1.6.1"
INTERFACE_OID_OUT = "1.3.6.1.2.1.31.1.1.1.10.1"
POLL_INTERVAL = 3  # seconds

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

def format_bps(value):
    if value >= 10**9:  # Gbps
        return f"{value / 10**9:.1f}G"
    elif value >= 10**6:  # Mbps
        return f"{value / 10**6:.3g}"  # using .3g will format to 3 significant figures
    elif value >= 10**3:  # Kbps
        return f"{value / 10**3:.2f}K"
    else:
        return f"{value:.2f}"

def snmp_child(pipe):
    while True:
        prev_in = fetch_snmp_data(INTERFACE_OID_IN)
        prev_out = fetch_snmp_data(INTERFACE_OID_OUT)
        time.sleep(POLL_INTERVAL)

        while True:
            try: 
                current_in = fetch_snmp_data(INTERFACE_OID_IN)
                current_out = fetch_snmp_data(INTERFACE_OID_OUT)

                in_rate = (current_in - prev_in) * 8 / POLL_INTERVAL  # convert bytes to bits
                out_rate = (current_out - prev_out) * 8 / POLL_INTERVAL

                total_bps = in_rate + out_rate
                formatted_total = format_bps(total_bps)

                print(f"SNMP Data: {formatted_total}")

                pipe.send(formatted_total)

            except subprocess.CalledProcessError:
                pipe.send("O_0")  # Send three dots if the ping fails
            except Exception as e:
                pipe.send("O_0")


            prev_in, prev_out = current_in, current_out
            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    #parent_conn, child_conn = Pipe()
    #snmp_child(child_conn)  # Call snmp_child directly when running the script standalone

        # This section is for testing the script directly
    while True:
        print(snmp_child())
        time.sleep(1)