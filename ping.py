import subprocess
import re
import time
from multiprocessing import Pipe

def ping_target(address="8.8.8.8"):
    """Ping the specified address and return the response time in ms as a whole number."""
    try:
        response = subprocess.check_output(['ping', '-c', '1', address])
        response_time = float(re.search("time=(\d+\.?\d*)", response.decode('utf-8')).group(1))
        # Convert to whole number and ensure it's between 1 and 999
        response_time = min(max(1, int(response_time)), 999)
    except:
        response_time = 999  # If there's an error (e.g., request timed out), return 999
    return response_time

def ping_child(pipe):
    while True:
        # Execute the ping command
        try:
            response = subprocess.check_output(
                ['ping', '-c', '1', '8.8.8.8'],
                stderr=subprocess.STDOUT,  # get all output
                universal_newlines=True  # return string not bytes
            )

            # Extract the ping time using regex
            ping_time = float(re.search(r"time=(\d+.\d+)", response).group(1))
            formatted_ping = "{:3.0f}".format(ping_time)  # Format to have 3 digits
            print(f"Ping time: {formatted_ping}")
            pipe.send(formatted_ping)  # Send the ping time to the parent process

        except subprocess.CalledProcessError:
            pipe.send("...")  # Send three dots if the ping fails
        except Exception as e:
            pipe.send("Err")

        time.sleep(1)  # Sleep for one second before pinging again


if __name__ == "__main__":
    # This section is for testing the script directly
    while True:
        print(ping_target())
        time.sleep(1)