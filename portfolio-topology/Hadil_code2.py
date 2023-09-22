# Import required modules
import argparse
import socket
import time
import threading
import re

#Set buffer size and timeout
TIMEOUT = 5
BUFFER_SIZE = 1024

# Define a server_mode function that takes an IP address, port, and file size as input
def server_mode(ip, port):
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
        print('ID                           Interval          RECIVED             Rate')
        print(f'{ip}:{port}      0.0 - {elapsed_time:.1f}       {received_data_mbits:.2f} MB         {rate:.2f} Mbps')

        # Close the client connection
        conn.close()

    # Create a server socket using IPv4 and TCP
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Bind the server socket to the IP address and port
        server_socket.bind((ip, int(port)))
        # Set the server to listen for incoming connections with a backlog of 5
        server_socket.listen(5)
        # Set a timeout of 30 seconds for the server
        server_socket.settimeout(100)
        # Print a message indicating the server is listening
        print("--------------------------------------------------")
        print(f"A simpleperf server is listening on port {port}")
        print("--------------------------------------------------")

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

# Define a client_mode function that takes server IP, server port, time duration, interval, parallel, and number of bytes as input
def client_mode(server_ip, server_port, time_duration, interval, parallel, num_bytes):

    # Define a function to check if the time duration has been exceeded
    def check_duration_exceeded(start_time, time_duration):
        return time.time() - start_time >= time_duration

    # Define a function to handle a single client connection
    def client_connection(client_addr, server_ip, server_port, time_duration, interval, num_bytes):
        try:
            # Create a connection to the server
            with socket.create_connection((server_ip, server_port)) as client_socket:
                # Set a timeout for the client socket
                client_socket.settimeout(TIMEOUT)

                # Print a message indicating the client is connected to the server
                print(f"Client connected with {server_ip} port {server_port}")


                # Initialize start time, sent data counter, last print time, interval ID, and header print flag
                start_time = time.time()
                sent_data = 0
                last_print_time = start_time
                interval_id = 0
                header_printed = True

                # Print the header for the interval statistics
                if header_printed:
                    print(f'ID              Interval     Transfer        Bandwidth')
                    header_printed = False

                # Initialize a flag to track if the last interval has been printed
                last_interval_printed = False

                # Loop to send data to the server until the time duration is exceeded or the specified number of bytes have been sent
                while not check_duration_exceeded(start_time, time_duration) and (num_bytes == 0 or sent_data < num_bytes):
                    try:
                        # Calculate the amount of data to send in the current iteration
                        to_send = min(BUFFER_SIZE, num_bytes - sent_data) if num_bytes > 0 else BUFFER_SIZE
                        # Send the data to the server
                        client_socket.sendall(b'0' * to_send)
                        # Update the sent data counter
                        sent_data += to_send
                    except BrokenPipeError:
                        # Handle a broken pipe error when the server closes the connection
                        print("Connection closed by server")
                        client_socket.close()
                        break

                    # Sleep for a short period to avoid overwhelming the server
                    time.sleep(0.001)

                    # Update the current time
                    current_time = time.time()
                    # Check if it's time to print the interval statistics
                    if current_time - last_print_time >= interval:
                        # Calculate the elapsed time, transfer, and bandwidth
                        elapsed_time = current_time - start_time
                        transfer = (sent_data / (1024 * 1024))
                        bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)
                        # Print the interval statistics
                        print(f'{client_addr} {elapsed_time - interval:.1f} - {elapsed_time:.1f}s {transfer:.2f}MB {bandwidth:.2f}Mbps')

                        # Update the last print time and interval ID
                        last_print_time = current_time
                        interval_id += 1
                        last_interval_printed = True
                    else:
                        last_interval_printed = False
                
                #print("Ute av tabell")
                # If the last interval hasn't been printed, print it
                if not last_interval_printed:
                    elapsed_time = time_duration
                    transfer = (sent_data / (1024 * 1024))
                    bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)
                    print(f'{client_addr} {elapsed_time - interval:.1f} - {elapsed_time:.1f}s {transfer:.2f}MB {bandwidth:.2f}Mbps')

                # Send a 'BYE' message to the server to indicate the end of the connection
                client_socket.sendall(b'BYE')
                #print("Har sendt bye til server")

                # Wait for an 'ACK: BYE' message from the server
                while True:
                    #print("Rett før socket.recv")
                    try:
                        data = client_socket.recv(BUFFER_SIZE)
                        #print("Rett før if")
                        if data == b'ACK: BYE':
                            #print("Nå skal jeg stoppe")
                            break
                    except socket.timeout:
                        #print("Client timed out waiting for 'ACK: BYE' message from the server")
                        break
                #print("Skal kalkulere tid, transfer og bandwidth")
                # Calculate the total elapsed time, transfer, and bandwidth
                end_time = time.time()
                elapsed_time = end_time - start_time
                transfer = (sent_data / (1024 * 1024))
                bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)

                # Print the total statistics
                print(f"\nSent {sent_data} KB in {elapsed_time:.2f} seconds. Total Transfer:{transfer:.1f}MB Bandwidth:{bandwidth:.2f}Mbps\n")

        # Handle any exceptions that occur during the client connection
        except Exception as e:
            print(f"Client error: {e}")

    # Define a function to initiate client connections
    def initiate_client_connections(server_ip, server_port, time_duration, interval, parallel, num_bytes):
    # Sleep for 1 second before starting client connections
        time.sleep(1)

        # Print a message indicating the client is connecting to the server
        print("-------------------------------------------------------------------------")
        print(f"A simpleperf client connecting to server {server_ip}, port {server_port}")
        print("-------------------------------------------------------------------------")

        # Initialize a list to store client threads
        threads = []
        # Create and start client threads
        for i in range(parallel):
            local_ip = socket.gethostbyname(socket.gethostname())
            client_addr = f"{local_ip}:{server_port + i + 1}"
            t = threading.Thread(target=client_connection, name=f"client_connection-{i}", args=(client_addr, server_ip, server_port, time_duration, interval, num_bytes))
            threads.append(t)
            t.start()

        # Wait for all threads to finish
        for t in threads:
            try:
                t.join()
            except KeyboardInterrupt:
                print("Interrupted by user. Terminating client connections.")
                for t in threads:
                    t.join()
                break

    # Call the initiate_client_connections function
    initiate_client_connections(server_ip, server_port, time_duration, interval, parallel, num_bytes)


# Main function
def main():
    # Initialize argument parser
    parser = argparse.ArgumentParser(description="Simpleperf network throughput measurement tool")
    
    # Add mutually exclusive group for server and client modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", action="store_true", help="Server mode")
    group.add_argument("-c", "--client", action="store_true", help="Client mode")

    # Add arguments for IP address binding and port number
    parser.add_argument("-b", "--bind", help="IP address to bind to (server mode)")
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

   # Run server or client mode based on the provided argument
    if args.server:
        server_mode(args.bind, args.port)
    elif args.client:
        client_mode(args.server_ip, args.port, args.time * 2, args.interval, args.parallel, num_bytes)

# Run the main function
if __name__ == "_main_":
    main()