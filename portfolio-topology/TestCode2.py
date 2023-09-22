# Import required modules
import argparse
import socket
import time
import threading
import re

# Set buffer size and timeout
BUFFER_SIZE = 1000
TIMEOUT = 5

# Function to parse size string and return size in bytes
def parse_size(size_str):
    # Use regex to match size string format
    size_match = re.match(r'^(\d+)([BKM]B?)$', size_str, re.IGNORECASE)
    # Raise ValueError if format is invalid
    if not size_match:
        raise ValueError(f"Invalid size format: {size_str}")
    # Extract size and unit from matched groups
    size = int(size_match.group(1))
    unit = size_match.group(2).upper()
    # Convert size to bytes based on the unit
    if unit == 'KB' or unit == 'K':
        size *= 1024
    elif unit == 'MB' or unit == 'M':
        size *= 1024 * 1024
    # No need for else, as 'B' doesn't require any conversion
    return size

# Function to handle connection
def handle_connection(conn, addr, ip, port):
    # Print connection info
    print(f"A simpleperf client with {addr} is connected with {ip}:{port}")
    # Record start time
    start_time = time.time()
    # Initialize received_data
    received_data = 0
    # Loop to receive data
    while True:
        # Receive data
        data = conn.recv(BUFFER_SIZE)
        # Break loop if no data is received
        if not data:
            break
        # Add received data length to received_data
        received_data += len(data)
        # Check for BYE message
        if data == b'BYE':
            # Send acknowledgment
            conn.sendall(b'ACK: BYE')
            # Break loop
            break
    # Close connection
    conn.close()
    # Record end time
    end_time = time.time()

    # Calculate elapsed time and rate
    elapsed_time = end_time - start_time
    rate = (received_data / 1000) / elapsed_time
    # Print result
    print(f"Received {received_data} bytes in {elapsed_time:.2f} seconds. Bandwidth: {rate:.2f} MB/s")

# Function to parse file size and return size in bytes
def parse_file_size(file_size):
    # Use regex to match file size string format
    size_match = re.match(r'^(\d+)([KMGT]B)$', file_size, re.IGNORECASE)
    # Return None if format is invalid
    if not size_match:
        return None
    # Extract size and unit from matched groups
    size = int(size_match.group(1))
    unit = size_match.group(2).upper()
    # Convert size to bytes based on the unit
    if unit == 'B':
        pass
    elif unit == 'KB':
        size *= 1024
    elif unit == 'MB':
        size *= 1024 * 1024
    elif unit == 'GB':
        size *= 1024 * 1024 * 1024
    elif unit == 'TB':
        size *= 1024 * 1024 * 1024 * 1024
    # Return size in bytes
    return size

# Function to run server mode
def server_mode(ip, port, file_size):
    # Parse file size
    size = parse_file_size(file_size)
    # Print error message if file size is invalid
    if not size:
        print(f"Invalid file size: {file_size}")
        return

    # Function to handle client connections
    def handle_client(conn, addr):
        handle_connection(conn, addr, ip, port)

    # Create server socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Bind server socket to IP and port
        server_socket.bind((ip, int(port)))
        # Set server socket to listen for connections
        server_socket.listen(5)
        # Set server socket timeout
        server_socket.settimeout(30)
        # Print server listening message
        print(f"A simpleperf server is listening on port {port}")

        # Loop to accept connections
        while True:
            try:
                # Accept connection
                conn, addr = server_socket.accept()
                # Create a new thread to handle the connection
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_thread.start()

            # Handle server timeout exception
            except socket.timeout:
                print("Server timeout: No new connections")
                break
            # Handle other server exceptions
            except Exception as e:
                print(f"Server error: {e}")
                break

# Function to print stats header
def print_stats_header():
    print("{:<15} {:<15} {:<15} {:<15}".format("ID", "Interval", "Transfer", "Bandwidth"))

# Function to print stats
def print_stats(client_addr, start_time, end_time, transfer, bandwidth):
    print("{:<15} {:<7.1f}-{:<7.1f} {:<8.1f} MB {:<12.2f} Mbps".format(f"{client_addr}", start_time, end_time, transfer, bandwidth))

# Function to check if duration is exceeded
def check_duration_exceeded(start_time, time_duration):
    return time.time() - start_time >= time_duration

# Function for client connection
def client_connection(client_addr, server_ip, server_port, time_duration, interval, num_bytes):
    # Print client connection message
    print(f"A simpleperf client connecting to server {server_ip}, port {server_port}")

    # Try connecting to server
    try:
        # Create client socket and connect to server
        with socket.create_connection((server_ip, server_port)) as client_socket:
            # Print client connected message
            print(f"Client connected with {server_ip} port {server_port}\n")
            

            # Record start time
            start_time = time.time()
            # Initialize sent_data
            sent_data = 0
            # Initialize last_print_time
            last_print_time = start_time
            # Initialize interval_id
            interval_id = 0

            # Print stats header
            print_stats_header()

            # Initialize last_interval_printed flag
            last_interval_printed = False

            # Loop to send data
            while not check_duration_exceeded(start_time, time_duration) and (num_bytes == 0 or sent_data < num_bytes):
                try:
                    # Calculate the amount of data to send
                    to_send = min(BUFFER_SIZE, num_bytes - sent_data) if num_bytes > 0 else BUFFER_SIZE
                    # Send data to server
                    client_socket.sendall(b'0' * to_send)
                    # Increment sent_data
                    sent_data += to_send
                # Handle BrokenPipeError
                except BrokenPipeError:
                    print("Connection closed by server")
                    client_socket.close()
                    break
                
                # Sleep for a short duration
                time.sleep(0.001)

                # Get the current time
                current_time = time.time()
                # Check if it's time to print stats
                if current_time - last_print_time >= interval:
                    # Calculate elapsed time, transfer, and bandwidth
                    elapsed_time = current_time - start_time
                    transfer = (sent_data / (1024 * 1024))
                    bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)

                    # Print stats
                    print_stats(client_addr, elapsed_time - interval, elapsed_time, transfer, bandwidth)

                    # Update last_print_time
                    last_print_time = current_time
                    # Increment interval_id
                    interval_id += 1
                    # Set last_interval_printed flag to True
                    last_interval_printed = True
                else:
                    # Set last_interval_printed flag to False
                    last_interval_printed = False 

            # Print stats if the last interval was not printed
            if not last_interval_printed:
                elapsed_time = time_duration
                transfer = (sent_data / (1024 * 1024))
                bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)
                print_stats(client_addr, elapsed_time - interval, elapsed_time, transfer, bandwidth)

            # Send 'BYE' message to server
            client_socket.sendall(b'BYE')

            # Wait for 'ACK: BYE' message from server
            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if data == b'ACK: BYE':
                    break

            # Record end time
            end_time = time.time()
            # Calculate elapsed time, transfer, and bandwidth
            elapsed_time = end_time - start_time
            transfer = (sent_data / (1024 * 1024))
            bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)  # Convert to Mbps

            # Print final statistics
            print(f"\nSent {sent_data} KB in {elapsed_time:.2f} seconds. Total Transfer:{transfer:.1f}MB Bandwidth:{bandwidth:.2f}Mbps\n")

    # Handle exceptions in client connection
    except Exception as e:
        print(f"Client error: {e}")

# Function for client mode
def client_mode(server_ip, server_port, time_duration, interval, parallel, num_bytes):
    # Wait for 1 second before starting the client
    time.sleep(1)
    
    # Create threads for parallel connections
    threads = []
    for i in range(parallel):
        local_ip = socket.gethostbyname(socket.gethostname())
        client_addr = f"{local_ip}:{server_port + i + 1}"
        t = threading.Thread(target=client_connection, name=f"client_connection-{i}", args=(client_addr, server_ip, server_port, time_duration, interval, num_bytes))
        threads.append(t)
        t.start()

    # Wait for all threads to finish
    for t in threads:
        t.join()

# Main function
def main():
    # Initialize argument parser
    parser = argparse.ArgumentParser(description="Simpleperf network throughput measurement tool")
    # Add mutually exclusive group for server and client modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", action="store_true", help="Server mode")
    group.add_argument("-c", "--client", action="store_true", help="Client mode")
    
    # Add arguments for server and client configurations
    parser.add_argument("-b", "--bind", default="", help="IP address to bind to (server mode)")
    parser.add_argument("-p", "--port", type=int, default=8170, help="Port number to use")
    parser.add_argument("-I", "--server_ip", help="Server IP address (client mode)")
    parser.add_argument("-t", "--time", type=int, default=10, help="Time duration in seconds (client mode)")
    parser.add_argument("-f", "--file_size", default="10MB", help="File size for data transfer (e.g. 10MB, 1GB)")
    parser.add_argument("-i", "--interval", type=int, default=None, help="Print statistics per z seconds (client mode)")
    parser.add_argument("-P", "--parallel", type=int, default=1, choices=range(1, 6), help="Create parallel connections to connect to the server and send data (min: 1, max: 5)")
    parser.add_argument("-n", "--num", type=str, default="0B", help="Transfer number of bytes specified by -n flag, it should be either in B, KB or MB.")

    # Parse arguments
    args = parser.parse_args()

    # Parse the number of bytes to send
    num_bytes = parse_size(args.num)
    # Set the interval for printing stats if not provided
    if args.interval is None:
        args.interval = args.time

    # Run server or client mode based on the provided argument
    if args.server:
        server_mode(args.bind, args.port, args.file_size)
    elif args.client:
        if not args.server_ip:
            parser.error("The following argument is required: -I/--server_ip")
        client_mode(args.server_ip, args.port, args.time, args.interval, args.parallel, num_bytes)

# Run the main function
if __name__ == "__main__":
    main()