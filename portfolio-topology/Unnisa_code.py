# Import required modules
import argparse
import socket
import time
import threading
import re

#Set buffer size and timeout
TIMEOUT = 5
BUFFER_SIZE = 4096

'''The server_mode function is designed to create a simple server that receives data from clients and 
calculates performance metrics like data transfer speed. It implements a basic TCP server that listens for 
incoming connections on a given IP address and port, and handles each client connection in 
a separate thread. When a client is connected, the server receives data from the client and 
calculates the amount of data received and the speed of the data transfer'''

# Define a server_mode function that takes an IP address, port, and file size as input
def server_mode(ip, port, file_size):

    def print_performance_metrics(ip, port, start_time, end_time, received_data):
        # Calculate the elapsed time
        elapsed_time = end_time - start_time
        # Convert received data to megabits
        received_data_mbits = (received_data * 8 / (1000 * 1000))
        # Calculate the data rate (in Mbps)
        rate = received_data_mbits / elapsed_time

        # Print the connection details and performance metrics
        print('ID                  Interval     Received     Rate')
        print(f'{ip}:{port}   0.0 - {elapsed_time:.1f}    {received_data_mbits:.2f} MB    {rate:.2f} Mbps')
    
    # Define a nested function to handle client connections
    def handle_connection(conn, addr):
        # Record the start time
        start_time = time.time()
        # Initialize received data counter
        received_data = 0

        # Loop to receive data from the client
        while True:
            # Receive data from the client
            data = conn.recv(BUFFER_SIZE)

            # Check if the data received is a termination signal, 'BYE'
            if data == b'BYE':
                # Send an acknowledgment to the client
                conn.sendall(b'ACK: BYE')
                # Break the loop and stop receiving data
                break
            # Add the length of the received data to the counter
            received_data += len(data)

        # Record the end time
        end_time = time.time()
        # Calculate the elapsed time
        elapsed_time = end_time - start_time
        # Convert received data to megabits
        received_data_mbits = (received_data * 8 / (1000 * 1000))
        # Calculate the data rate (in Mbps)
        rate = received_data_mbits / elapsed_time

        # Print the connection details and performance metrics
        print('ID                  Interval     Received     Rate')
        print(f'{ip}:{port}   0.0 - {elapsed_time:.1f}    {received_data_mbits:.2f} MB    {rate:.2f} Mbps')

        # Close the client connection
        conn.close()

    # Create a server socket using IPv4 and TCP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Bind the server socket to the IP address and port
    server_socket.bind((ip, int(port)))
    
    # Set the server to listen for incoming connections with a backlog of 5
    server_socket.listen(5)
    
    # Set a timeout of 30 seconds for the server
    server_socket.settimeout(60)
    
    # Print a message indicating the server is listening
    print("------------------------------------------------")
    print(f"A simpleperf server is listening on port {port}")
    print("------------------------------------------------")

    # Loop to accept new client connections
    while True:
        try:
            # Accept a new client connection
            conn, addr = server_socket.accept()
            
            # Print a message for the new connection
            print(f"New connection from: {addr[0]}:{addr[1]}")
            print(f"A simpleperf client with {addr[0]}:{addr[1]} is connected with {ip}:{port}")
            
            # Create a new thread to handle the client connection
            client_thread = threading.Thread(target=handle_connection, args=(conn, addr))
            
            # Start the new thread
            client_thread.start()

        # Catch a timeout exception
        except socket.timeout:
            # Print a message indicating the server timed out waiting for new connections
            print("Server timeout: No new connections")
            # Break the loop and stop accepting new connections
            break
        # Catch any other exceptions
        except Exception as e:
            # Print an error message with the exception details
            print(f"Server error: {e}")
            # Break the loop and stop accepting new connections
            break

    # Close the server socket
    server_socket.close()

# Define a client_mode function that takes server IP, server port, time duration, interval, parallel, and number of bytes as input
class SimplePerfClient:
    def _init_(self, server_ip, server_port, time_duration, interval, parallel, num_bytes):
        self.server_ip = server_ip
        self.server_port = server_port
        self.time_duration = time_duration
        self.interval = interval
        self.parallel = parallel
        self.num_bytes = num_bytes

    def check_duration_exceeded(self, start_time):
        return time.time() - start_time >= self.time_duration

    def print_interval_statistics(self, client_addr, start_time, last_print_time, sent_data, last_interval_printed):
        current_time = time.time()
        if current_time - last_print_time >= self.interval:
            elapsed_time = current_time - start_time
            transfer = (sent_data / (1024 * 1024))
            bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)
            print(f'{client_addr}   {elapsed_time - self.interval:.1f} - {elapsed_time:.1f}s   {transfer:.2f}MB   {bandwidth:.2f}Mbps')

            last_print_time = current_time
            last_interval_printed = True
        else:
            last_interval_printed = False

        return last_print_time, last_interval_printed

    def client_connection(self, client_addr):
        try:
            with socket.create_connection((self.server_ip, self.server_port)) as client_socket:
                print(f"Client connected with {self.server_ip} port {self.server_port}")

                start_time = time.time()
                sent_data = 0
                last_print_time = start_time
                header_printed = True

                if header_printed:
                    print(f'ID              Interval     Transfer        Bandwidth')
                    header_printed = False

                last_interval_printed = False

                while not self.check_duration_exceeded(start_time) and (self.num_bytes == 0 or sent_data < self.num_bytes):
                    to_send = min(BUFFER_SIZE, self.num_bytes - sent_data) if self.num_bytes > 0 else BUFFER_SIZE
                    client_socket.sendall(b'0' * to_send)
                    sent_data += to_send
                    time.sleep(0.001)

                    last_print_time, last_interval_printed = self.print_interval_statistics(client_addr, start_time, last_print_time, sent_data, last_interval_printed)

                if not last_interval_printed:
                    _, _ = self.print_interval_statistics(client_addr, start_time, start_time + self.time_duration - self.interval, sent_data, last_interval_printed)

                client_socket.sendall(b'BYE')

                while True:
                    data = client_socket.recv(BUFFER_SIZE)
                    if data == b'ACK: BYE':
                        break

                end_time = time.time()
                elapsed_time = end_time - start_time
                transfer = (sent_data / (1024 * 1024))
                bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)

                print(f"\nSent {sent_data} KB in {elapsed_time:.2f} seconds. Total Transfer:{transfer:.2f}MB Bandwidth:{bandwidth:.2f}Mbps\n")

        except Exception as e:
            print(f"Client error: {e}")


    def initiate_client_connections(self):
        time.sleep(1)
        print("-------------------------------------------------------------------------")
        print(f"A simpleperf client connecting to server {self.server_ip}, port {self.server_port}")
        print("-------------------------------------------------------------------------")

        threads = []
        for i in range(self.parallel):
            local_ip = socket.gethostbyname(socket.gethostname())
            client_addr = f"{local_ip}:{self.server_port + i + 1}"
            t = threading.Thread(target=self.client_connection, name=f"client_connection-{i}", args=(client_addr,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    #initiate_client_connections(server_ip, server_port, time_duration, interval, parallel, num_bytes)

#client.initiate_client_connections()
#client = SimplePerfClient(server_ip, server_port, time_duration, interval, parallel, num_bytes)
    

# Main function
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
    parser.add_argument("-I", "--server_ip", help="Server IP address (client mode)")
    parser.add_argument("-t", "--time", type=int, default=10, help="Time duration in seconds (client mode)")
    parser.add_argument("-f", "--file_size", default="10MB", help="File size for data transfer (e.g. 10MB, 1GB)")
    parser.add_argument("-i", "--interval", type=int, default=None, help="Print statistics per z seconds (client mode)")
    parser.add_argument("-P", "--parallel", type=int, default=1, choices=range(1, 6), help="Create parallel connections to connect to the server and send data (min: 1, max: 5)")
    parser.add_argument("-n", "--num", type=str, default="0B", help="Transfer number of bytes specified by -n flag, it should be either in B, KB or MB.")
    
    # Parse arguments
    args = parser.parse_args()

    # Check if the provided size format is valid
    size_match = re.match(r'^(\d+)([BKM]B?)$', args.num, re.IGNORECASE)
    if not size_match:
        raise ValueError(f"Invalid size format: {args.num}")

    # Convert the size to bytes
    size = int(size_match.group(1))
    unit = size_match.group(2).upper()
    if unit == 'KB' or unit == 'K':
        size *= 1024
    elif unit == 'MB' or unit == 'M':
        size *= 1024 * 1024
    num_bytes = size

    # Set the interval for printing stats if not provided
    if args.interval is None:
        args.interval = args.time

    if args.server:
        server_mode(args.bind, args.port, args.file_size)
    elif args.client:
        if not args.server_ip:
            parser.error("The following argument is required: -I/--server_ip")
    client = SimplePerfClient(args.server_ip, args.port, args.time, args.interval, args.parallel, num_bytes)
    client.initiate_client_connections()

# Run the main function
if __name__ == "_main_":
    main()