import subprocess
import re
import time
import socket
from multiprocessing import Pipe

POLL_INTERVAL = 0.15  # seconds
#IP_TO_PING = "203.50.2.71" # Australia DNS
IP_TO_PING = "8.8.8.8" # Google DNS

def ping_target(address=IP_TO_PING):
    """Ping the specified address and return the response time in ms as a whole number."""
    try:
        response = subprocess.check_output(['ping', '-c', '1', address])
        response_time = float(re.search("time=(\d+\.?\d*)", response.decode('utf-8')).group(1))
        # Convert to whole number and ensure it's between 1 and 999
        response_time = min(max(1, int(response_time)), 999)
    except:
        response_time = 999  # If there's an error (e.g., request timed out), return 999
    return response_time

def ping_child(pipe=None):
    while True:
        try:
            response = subprocess.check_output(
                ['ping', '-c', '1', IP_TO_PING],
                stderr=subprocess.STDOUT,  # get all output
                universal_newlines=True  # return string not bytes
            )

            # Extract the ping time using regex
            ping_time = float(re.search(r"time=(\d+.\d+)", response).group(1))
            formatted_ping = "{:3.0f}".format(ping_time)  # Format to have 3 digits

            pipe.send(formatted_ping)  # Send the ping time to the parent process
            time.sleep(POLL_INTERVAL)
        except (socket.error, subprocess.CalledProcessError):
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


if __name__ == "__main__":
    # This section is for testing the script directly
    while True:
        print(ping_target())
        time.sleep(1)