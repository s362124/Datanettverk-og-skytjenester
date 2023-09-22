import socket  # Import the socket module to create and manage sockets
import time  # Import the time module to measure time intervals
import threading # Import the threading module to create and manage threads
import argparse # Import the argparse module to parse command line arguments
import re # Import the regular expressions module for string pattern matching

# Constants
DATA_SIZE = 4096 # Size of the data to be sent/received at a time
BREAK_TIME = 5  # Time to wait before breaking the loop

# Server function
def server(ip, port):
    # Function to handle connections from clients
    def manage_connection(connection1, adresse):
        initial_time = time.time() # Record the start time
        captured_data = 0  # Initialize the amount of data captured
        received_data = True  # Set the flag for data reception

        # Loop until there's no more data to receive
        while received_data:
            try:
                data = connection1.recv(DATA_SIZE) # Receive data from the client

                if not data: # If no data is received
                    received_data = False # Set the flag to false
                else:
                    if data == b'BYE': # If the data received is 'BYE'
                        connection1.sendall(b'ACK: BYE') # Send an acknowledgement
                        received_data = False  # Set the flag to false
                    else:
                        captured_data += len(data) # Add the length of the received data to the total captured data
            except socket.error as e: # If there's an error in receiving data
                print(f"Error receiving data from client {adresse[0]}:{adresse[1]} - {e}")
                received_data = False  # Set the flag to false


        finish_time = time.time() # Record the finish time
        time_spent = finish_time - initial_time # Calculate the time spent
        data_transfer_rate = (captured_data * 8 / (1000 * 1000)) # Calculate the data transfer rate
        rate = data_transfer_rate / time_spent # Calculate the rate

        # Print the result 
        print('ID                           Interval          RECEIVED             Rate')
        result_str = f'{adresse[0]}:{adresse[1]}      0.0 - {time_spent:.1f}       {data_transfer_rate:.2f} MB         {rate:.2f} Mbps'
        print(result_str)

        connection1.sendall(result_str.encode('utf-8')) # Send the result to the client
        connection1.close() # Close the connection

# Create a server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((ip, int(port))) # Bind the server socket to the specified IP and port
    server_socket.listen(5) # Set the server socket to listen for incoming connections

    # Print server information
    print("--------------------------------------------------")
    print(f"A simpleperf server is listening on port {port}")
    print("--------------------------------------------------")

    # Main server loop
    while True:
        connection1, adresse = server_socket.accept() # Accept a new connection
        print(f"New client connection from {adresse[0]}:{adresse[1]}")
        threading.Thread(target=manage_connection, args=(connection1, adresse)).start() # Start a new thread to handle the connection


# Client function
def client (server_ip, server_port, time_span, interval, parallel, byte_count):
    # Function to run a client connection
    def run_connection(i, server_ip, server_port, time_span, interval, byte_count):
        try:
            local_ip = socket.gethostbyname(socket.gethostname()) # Get the local IP address
            local_port = server_port + i # Calculate the local port number
            client_addr = f"{local_ip}:{local_port}" # Create the client address string

            # Create and connect a socket to the server
            with socket.create_connection((server_ip, server_port)) as user_socket:
                print(f"Client connected with {server_ip} port {server_port}")

                begin_time = time.time() # Record the start time
                transmitted_data = 0 # Initialize the amount of data transmitted
                last_output_time = begin_time # Initialize the last output time

                 # Print the header for the output
                print('ID              Interval     Transfer        Bandwidth')

                # Loop until the specified conditions are met
                while time.time() - begin_time < time_span and (byte_count == 0 or transmitted_data < byte_count):
                    # Calculate the amount of data to send
                    data_to_send = min(DATA_SIZE, byte_count - transmitted_data) if byte_count > 0 else DATA_SIZE
                    user_socket.sendall(b'0' * data_to_send) # Send the data
                    transmitted_data += data_to_send # Update the total transmitted data

                    time.sleep(0.001) # Sleep for a short duration

                    # Check if it's time to print the output
                    if time.time() - last_output_time >= interval:
                        time_spent = time.time() - begin_time # Calculate the time spent
                        transfer = (transmitted_data / (1024 * 1024)) # Calculate the transfer in MB
                        bandwidth = (transmitted_data * 8) / (time_spent * 1000 * 1000) # Calculate the bandwidth in Mbps
                        # Print the output
                        print(f'{client_addr} {time_spent - interval:.1f} - {time_spent:.1f}s {transfer:.2f}MB {bandwidth:.2f}Mbps')
                        last_output_time = time.time() # Print the output

                # Print the last interval
                time_spent = time.time() - begin_time # Calculate the time spent
                transfer = (transmitted_data / (1024 * 1024)) # Calculate the transfer in MB
                bandwidth = (transmitted_data * 8) / (time_spent * 1000 * 1000) # Calculate the bandwidth in Mbps
                # Print the output
                print(f'{client_addr} {time_spent - interval:.1f} - {time_spent:.1f}s {transfer:.2f}MB {bandwidth:.2f}Mbps')

                user_socket.sendall(b'BYE') # Send 'BYE' to the server
                data_timeout = 10  # Set a timeout for receiving data from the server
                user_socket.settimeout(data_timeout)

                # Loop to receive data from the server
                while True:
                    try:
                        data = user_socket.recv(DATA_SIZE) # Receive data from the server
                        if data == b'ACK: BYE': # If the received data is 'ACK: BYE'
                            break # Break the loop
                    except socket.break_time: # If the socket times out
                        break # Break the loop
                
                 # Calculate and print the final results
                time_spent = time.time() - begin_time
                transfer = (transmitted_data / (1024 * 1024))
                bandwidth = (transmitted_data * 8) / (time_spent * 1000 * 1000)
                print(f'\n{client_addr} 0.0 - {time_spent:.1f}s {transfer:.2f}MB {bandwidth:.2f}Mbps')
                print(f'\nSent {transmitted_data} KB in {time_spent:.2f} seconds. Total Transfer:{transfer:.2f}MB Bandwidth:{bandwidth:.2f}Mbps')
                print()

        except Exception as e: # Catch any exceptions that occur during client connection
            print(f"Client error: {e}") # Print the error message


    # Function to start multiple client connections in parallel
    def start_client_connections(server_ip, server_port, time_span, interval, parallel, byte_count):
        time.sleep(1) # Sleep for a short duration

        # Print client connection details
        print("--------------------------------------------------")
        print(f"A simpleperf client connecting to server {server_ip}, port {server_port}")
        print("--------------------------------------------------")

        threads = [] # List to store the thread objects
        for i in range(parallel): # Loop for creating multiple connections
            # Create and start a new thread for each connection
            t = threading.Thread(target=run_connection, args=(i, server_ip, server_port, time_span, interval, byte_count), name=f"client_connection-{i}")
            threads.append(t)
            t.start()

        for t in threads: # Loop for joining the threads
            t.join()

    start_client_connections(server_ip, server_port, time_span, interval, parallel, byte_count) # Start the client connections


def main():
    # Initialize argument parser
    parser = argparse.ArgumentParser(description="Simpleperf network throughput measurement tool")
    
    # Add mutually exclusive group for server and client modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", action="store_true", help="Server mode")
    group.add_argument("-c", "--client", action="store_true", help="Client mode")

    # Add arguments for IP address binding and port number
    parser.add_argument("-b", "--bind", default="", help="IP address to bind to (server mode)")
    parser.add_argument("-p", "--port", type=int, default=8088, help="Port number to use")

    # Add arguments for server and client configurations
    parser.add_argument("-I", "--server_ip", default="127.0.0.1", help="Server IP address (client mode)")
    parser.add_argument("-t", "--time", type=int, default=25, help="Total duration in seconds for which data should be generated")
    parser.add_argument("-f", "--format", default="MB", choices=["B", "KB", "MB"], help="The format of the output data")
    parser.add_argument("-i", "--interval", type=int, default=None, help="Print statistics per z seconds (client mode)")
    parser.add_argument("-P", "--parallel", type=int, default=1, choices=range(1, 6), help="Create parallel connections to connect to the server and send data (min: 1, max: 5)")
    parser.add_argument("-n", "--num", type=str, default="0B", help="Transfer number of bytes specified by -n flag, it should be either in B, KB or MB.")
    
    # Parse arguments
    args = parser.parse_args()

    # Check if the provided port number is within the valid range
    if args.port < 1024 or args.port > 65535:
        parser.error("The port number must be within the range [1024, 65535]")

    # Check if the provided size format is valid
    size_match = re.match(r"([0-9]+)([a-z]+)", args.num, re.IGNORECASE)
    if not size_match:
        raise ValueError(f"Invalid size format: {args.num}")

    # Convert the size to bytes
    def convert_size_to_bytes(size_str):
        units_map = {'K': 1024, 'KB': 1024, 'M': 1024 * 1024, 'MB': 1024 * 1024}

        size_match = re.match(r"([0-9]+)([a-z]+)", size_str, re.IGNORECASE)
        if not size_match:
            raise ValueError(f"Invalid size format: {size_str}")

        size_value = int(size_match.group(1))
        size_unit = size_match.group(2).upper()

        return size_value * units_map.get(size_unit, 1)

    byte_count = convert_size_to_bytes(args.num)

    # Set the interval for printing stats if not provided
    if args.interval is None:
        args.interval = args.time

    if args.server:
        server(args.bind, args.port)  
    elif args.client:
        try:
            client(args.server_ip, args.port, args.time, args.interval, args.parallel, byte_count)
        except ConnectionRefusedError:
            print(f"Cannot connect to server {args.server_ip} on port {args.port}. Make sure the server is running.")

# Here we run the main function
if __name__ == "__main__":
    main()