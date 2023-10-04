from pysnmp.hlapi import *
import time
import subprocess
import re
from multiprocessing import Pipe

SNMP_TARGET = "192.168.1.40"
SNMP_V2_COMMUNITY = "public"
INTERFACE_OID_IN = "1.3.6.1.2.1.31.1.1.1.6.1"
INTERFACE_OID_OUT = "1.3.6.1.2.1.31.1.1.1.10.1"
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

def format_bps(value):
    if value >= 10**9:  # Gbps
        return f"{value / 10**9:.1f}G"
    elif value >= 10**6:  # Mbps
        return f"{value / 10**6:.3g}"  # using .3g will format to 3 significant figures
    elif value >= 10**3:  # Kbps
        return f"{value / 10**3:.2f}K"
    else:
        return f"{value:.2f}"

def snmp_child(pipe=None):
    while True:
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

        except (socket.error, http.client.HTTPException, urllib.error.URLError):
            if pipe:
                pipe.send("O_0")  # or some other placeholder/error value
            else:
                print("O_0")
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            if pipe:
                pipe.send("O_0")
            else:
                print("O_0")
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
#    parent_conn, child_conn = Pipe()
#    snmp_child()  # Call snmp_child directly when running the script standalone
    while True:
        print(snmp_child())
        time.sleep(1)