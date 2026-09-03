import socket
import time
from multiprocessing import Process, Pipe
from pathlib import Path
import RPi.GPIO as GPIO

from env_config import load_env_file
import unifi  # Import the UniFi dashboard WebSocket collector
import ping  # Import the ping module

# CONSTANTS
SEGMENTS = (25, 5, 6, 12, 13, 19, 16, 24)
DIGITS = (23, 22, 27, 18, 17, 4)
FREQUENCY = 1000
PWMS = []
NUMBER_PATTERNS = {' ':(0,0,0,0,0,0,0,0),
    'L':(0,1,0,1,0,1,0,0),
    'U':(0,1,1,1,1,1,0,0),
    'R':(0,0,0,1,0,0,1,0),
    'E':(1,1,0,1,0,1,1,0),
    'O':(0,0,0,1,1,1,1,0),
    'N':(0,0,0,1,1,0,1,0),
    'G':(1,1,0,1,1,1,0,0),
    'A':(1,1,1,1,1,0,1,0),
    'H':(0,1,0,1,1,0,1,0),
    'T':(0,1,0,1,1,1,1,0), #number 8, the last one is the middle segment
    'P':(1,1,1,1,0,0,1,0), #number 5, the last one is the bottom right
    'B':(0,1,0,1,1,1,1,0), #number 1, the first one is the top segment
    'D':(0,0,1,1,1,1,1,0), #number 2, the second one, is top left segment
    'S':(1,1,0,0,5,1,1,0), #number 2, the second one, is top left segment
    '0':(1,1,1,1,1,1,0,0),
    '1':(0,0,1,0,1,0,0,0),
    '2':(1,0,1,1,0,1,1,0),
    '3':(1,0,1,0,1,1,1,0),
    '4':(0,1,1,0,1,0,1,0),
    '5':(1,1,0,0,1,1,1,0),
    '6':(1,1,0,1,1,1,1,0),
    '7':(1,0,1,0,1,0,0,0),
    '8':(1,1,1,1,1,1,1,0),
    '9':(1,1,1,0,1,1,1,0),
    '_':(0,0,0,0,0,1,0,0),
    ' ':(0,0,0,0,0,0,0,0),
    'L.':(0,1,0,1,0,1,0,1),
    'U.':(0,1,1,1,1,1,0,1),
    'R.':(0,0,0,1,0,0,1,1),
    'E.':(1,1,0,1,0,1,1,1),
    'O.':(0,0,0,1,1,1,1,1),
    'N.':(0,0,0,1,1,0,1,1),
    'G.':(1,1,0,1,1,1,0,1),
    'A.':(1,1,1,1,1,0,1,1),
    'H.':(0,1,0,1,1,0,1,1),
    'T.':(0,1,0,1,1,1,1,1), #number 8, the last one is the middle segment
    'P.':(1,1,1,1,0,0,1,1), #number 5, the last one is the bottom right
    'B.':(0,1,0,1,1,1,1,1), #number 1, the first one is the top segment
    'D.':(0,0,1,1,1,1,1,1), #number 2, the second one, is top left segment
    'S.':(1,1,0,0,5,1,1,1), #number 2, the second one, is top left segment
    '0.':(1,1,1,1,1,1,0,1),
    '1.':(0,0,1,0,1,0,0,1),
    '2.':(1,0,1,1,0,1,1,1),
    '3.':(1,0,1,0,1,1,1,1),
    '4.':(0,1,1,0,1,0,1,1),
    '5.':(1,1,0,0,1,1,1,1),
    '6.':(1,1,0,1,1,1,1,1),
    '7.':(1,0,1,0,1,0,0,1),
    '8.':(1,1,1,1,1,1,1,1),
    '9.':(1,1,1,0,1,1,1,1),
    '_.':(0,0,0,0,0,1,0,1)}

def setup():
    """Initialization for the display."""
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SEGMENTS, GPIO.OUT)
    GPIO.setup(DIGITS, GPIO.OUT)

def cleanup():
    """Cleanup the GPIO settings."""
    GPIO.cleanup()

def get_ip_address():
    """Retrieve the primary IP address of the Raspberry Pi."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to an external server (doesn't actually establish a connection, but chooses an interface to use)
        s.connect(("8.8.8.8", 80))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP

def wake_up_display():
    """Wake up function to test all segments by quickly moving 8 through all the segments."""
    for _ in range(500):  # Display "HAIOHH" 50 times to increase visibility
        display_string("HA1 OH")

    for _ in range(5):  # Repeat 5 times
        for pos in range(6):  # Assuming you have a 6-character display
            data = ' ' * pos + '8' + ' ' * (5 - pos)
            
            for _ in range(5):  # Display each pattern 10 times to increase visibility
                display_string(data)

            time.sleep(0.005)  # Wait for 0.5 seconds between patterns
    
    """Wake up function to test all segments and display the IP address."""
    ip_address = get_ip_address()
    print(f"Showing RPI IP Address: {ip_address}")
    segments = ip_address.split('.')

    formatted_ip_1 = segments[1].rjust(3, '0') + segments[0].rjust(3, '0')  # "168192" for IP "192.168.1.49"
    formatted_ip_2 = segments[3].rjust(3, '0') + segments[2].rjust(3, '0')  # "049001" for IP "192.168.1.49"
    
    patterns = ["ADD 1P", formatted_ip_1, formatted_ip_2]
    
    for _ in range(3):  # Repeat the whole sequence 3 times, display IP address 3 times
        for pattern in patterns:
            for _ in range(100):  # Display each pattern 100 times for visibility
                display_string(pattern)

    display_string("      ")  # Clear the display

def display_string(data):
    """Display the combined WAN throughput and ping data on the seven-segment displays."""

    # Formatting data
    formatted_data = str(data).ljust(12)[:12]  # assuming the display can show 6 characters at a time.
    #print("Formatted data:", formatted_data)

    # Add leading zeros if necessary
    if '.' in formatted_data:
        integer_part, decimal_part = formatted_data.split('.')
        integer_part = integer_part.rjust(4, '0')
        formatted_data = f"{integer_part}.{decimal_part}"

    #print("Formatted data with leading zeros:", formatted_data)

    # Break down the string into individual characters, considering '.' as part of the preceding character.
    expanded_string = []
    for i in range(len(formatted_data)):
        if formatted_data[i] == '.' and i > 0:
            expanded_string[-1] += '.'
        else:
            expanded_string.append(formatted_data[i])

    #print("Expanded string:", expanded_string)

    # Display the formatted data for a brief moment (no infinite loop)
    for digit, char in zip(DIGITS, expanded_string):
        pattern = NUMBER_PATTERNS.get(char, NUMBER_PATTERNS[' '])  # Get the pattern or default to blank
        GPIO.output(digit, GPIO.HIGH)  # Enable this digit
        #print(f"Displaying character '{char}' with pattern {pattern}")

        for segment, value in zip(SEGMENTS, pattern):
            GPIO.output(segment, value)

        time.sleep(0.003)  # Adjust this sleep for the correct display time per digit
        GPIO.output(digit, GPIO.LOW)  # Disable this digit

def display(data):
    # Simulated display function
    print(data)


def start_child_process(target):
    parent_conn, child_conn = Pipe()
    process = Process(target=target, args=(child_conn,))
    process.start()
    child_conn.close()
    return parent_conn, process


def restart_child_process(name, process, parent_conn, target):
    print(f"[WARNING] {name} process died. Restarting...")
    if process.is_alive():
        process.terminate()
    process.join()
    parent_conn.close()
    return start_child_process(target)


def recv_if_ready(conn, default=None):
    try:
        if conn.poll():
            return conn.recv()
    except (EOFError, OSError):
        return default
    return default


def stop_child_process(process):
    if process.is_alive():
        process.terminate()
    process.join()


def main():
    load_env_file(Path(__file__).resolve().parent / ".env")

    # Initialization for the display
    print("Setting up GPIO...")
    setup()
    print("Waking up the display...")
    wake_up_display()

    startup_time = time.time() 
    parent_conn_wan, p_wan = start_child_process(unifi.unifi_child)
    parent_conn_ping, p_ping = start_child_process(ping.ping_child)

    last_wan_data = '000'
    last_ping_data = "999"

    try:
        while True:
            # Parent reads from its end of pipes and updates display
            data_received = recv_if_ready(parent_conn_wan)
            if data_received:
                last_wan_data = data_received["data"]
                print(data_received["data"])  # Print out the debug info or handle it as required

            ping_received = recv_if_ready(parent_conn_ping)
            if ping_received:
                last_ping_data = ping_received

            # Check if unifi.py has crashed or terminated
            if not p_wan.is_alive():
                parent_conn_wan, p_wan = restart_child_process(
                    "unifi_child",
                    p_wan,
                    parent_conn_wan,
                    unifi.unifi_child,
                )

            if not p_ping.is_alive():
                parent_conn_ping, p_ping = restart_child_process(
                    "ping_child",
                    p_ping,
                    parent_conn_ping,
                    ping.ping_child,
                )

            if time.time() - startup_time < 50:
                last_wan_data = "UNI"

            combined_data = f"{last_ping_data}{last_wan_data}"  # Combining the data.
            display_string(combined_data)  # Use the RPi.GPIO to display the combined data

    except KeyboardInterrupt:
        # On keyboard interrupt, terminate child processes and exit
        stop_child_process(p_wan)
        stop_child_process(p_ping)
        parent_conn_wan.close()
        parent_conn_ping.close()
        cleanup()  # Proper cleanup on exit 

if __name__ == '__main__':
    main()
