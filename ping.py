import re
import socket
import subprocess
import time
from multiprocessing import Pipe

# Constants
POLL_INTERVAL = 0.15  # seconds
#IP_TO_PING = "203.50.2.71"  # Australia DNS
IP_TO_PING = "8.8.8.8"  # Google DNS
ERROR_RESPONSE = "O_0"

def ping_target(address=IP_TO_PING):
    """Ping the specified address and return the response time in ms as a whole number."""
    try:
        response = subprocess.check_output(['ping', '-c', '1', address])
        response_time = float(re.search("time=(\d+\.?\d*)", response.decode('utf-8')).group(1))
        # Convert to whole number and ensure it's between 1 and 999
        return min(max(1, int(response_time)), 999)
    except Exception:
        return 999  # If there's an error (e.g., request timed out), return 999

def ping_child(pipe=None):
    """Ping the specified address in a loop and send the response time to a parent process via a pipe."""
    counter = 0
    while True:
        try:
            response = subprocess.check_output(
                ['ping', '-c', '1', IP_TO_PING],
                stderr=subprocess.STDOUT,  # get all output
                universal_newlines=True  # return string not bytes
            )
            ping_time = float(re.search(r"time=(\d+.\d+)", response).group(1))
            formatted_ping = "{:3.0f}".format(ping_time)  # Format to have 3 digits

        except (socket.error, subprocess.CalledProcessError, Exception):
            formatted_ping = ERROR_RESPONSE

        # Send data to parent or print based on availability of pipe
        if pipe:
            pipe.send(formatted_ping)
        else:
            print(formatted_ping)

        counter += 1
        if counter % 100 == 0:
            print(f"[MAIN THREAD] 100 iterations of ping.py have passed. Current output of ping.py to sign.py: {formatted_ping}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    # This section is for testing the script directly
    while True:
        print(ping_target())
        time.sleep(1)
