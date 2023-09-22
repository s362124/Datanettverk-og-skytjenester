import socket
import time
import threading
import argparse
import re

DATA_SIZE = 4096
BREAK_TIME = 5

def server(ip, port):
    def manage_connection(connection1, adresse):
        initial_time = time.time()
        captured_data = 0
        received_data = True

        while received_data:
            try:
                data = connection1.recv(DATA_SIZE)

                if not data:
                    received_data = False
                else:
                    if data == b'BYE':
                        connection1.sendall(b'ACK: BYE')
                        received_data = False
                    else:
                        captured_data += len(data)
            except socket.error as e:
                print(f"Error receiving data from client {adresse[0]}:{adresse[1]} - {e}")
                received_data = False


        finish_time = time.time()
        time_spent = finish_time - initial_time
        data_transfer_rate = (captured_data * 8 / (1000 * 1000))
        rate = data_transfer_rate / time_spent

        print('ID                           Interval          RECEIVED             Rate')
        result_str = f'{adresse[0]}:{adresse[1]}      0.0 - {time_spent:.1f}       {data_transfer_rate:.2f} MB         {rate:.2f} Mbps'
        print(result_str)

        connection1.sendall(result_str.encode('utf-8'))
        connection1.close()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((ip, int(port)))
    server_socket.listen(5)

    print("--------------------------------------------------")
    print(f"A simpleperf server is listening on port {port}")
    print("--------------------------------------------------")

    while True:
        connection1, adresse = server_socket.accept()
        print(f"New client connection from {adresse[0]}:{adresse[1]}")
        threading.Thread(target=manage_connection, args=(connection1, adresse)).start()


# The rest of the code remains the same
def client (server_ip, server_port, time_span, interval, parallel, byte_count):
    def run_connection(i, server_ip, server_port, time_span, interval, byte_count):
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            local_port = server_port + i
            client_addr = f"{local_ip}:{local_port}"
            with socket.create_connection((server_ip, server_port)) as user_socket:
                print(f"Client connected with {server_ip} port {server_port}")

                begin_time = time.time()
                transmitted_data = 0
                last_output_time = begin_time

                print('ID              Interval     Transfer        Bandwidth')

                while time.time() - begin_time < time_span and (byte_count == 0 or transmitted_data < byte_count):
                    data_to_send = min(DATA_SIZE, byte_count - transmitted_data) if byte_count > 0 else DATA_SIZE
                    user_socket.sendall(b'0' * data_to_send)
                    transmitted_data += data_to_send

                    time.sleep(0.001)

                    
                    if time.time() - last_output_time >= interval:
                        time_spent = time.time() - begin_time
                        transfer = (transmitted_data / (1024 * 1024))
                        bandwidth = (transmitted_data * 8) / (time_spent * 1000 * 1000)
                        print(f'{client_addr} {time_spent - interval:.1f} - {time_spent:.1f}s {transfer:.2f}MB {bandwidth:.2f}Mbps')
                        last_output_time = time.time()

                # Print the last interval
                time_spent = time.time() - begin_time
                transfer = (transmitted_data / (1024 * 1024))
                bandwidth = (transmitted_data * 8) / (time_spent * 1000 * 1000)
                print(f'{client_addr} {time_spent - interval:.1f} - {time_spent:.1f}s {transfer:.2f}MB {bandwidth:.2f}Mbps')

                user_socket.sendall(b'BYE')
                data_timeout = 10  # Set a timeout for receiving data from the server
                user_socket.settimeout(data_timeout)

                while True:
                    try:
                        data = user_socket.recv(DATA_SIZE)
                        if data == b'ACK: BYE':
                            break
                    except socket.break_time:
                        break

                time_spent = time.time() - begin_time
                transfer = (transmitted_data / (1024 * 1024))
                bandwidth = (transmitted_data * 8) / (time_spent * 1000 * 1000)
                print(f'\n{client_addr} 0.0 - {time_spent:.1f}s {transfer:.2f}MB {bandwidth:.2f}Mbps')
                print(f'\nSent {transmitted_data} KB in {time_spent:.2f} seconds. Total Transfer:{transfer:.2f}MB Bandwidth:{bandwidth:.2f}Mbps')
                print()

        except Exception as e:
            print(f"Client error: {e}")


    # The start_client_connections function is modified
    def start_client_connections(server_ip, server_port, time_span, interval, parallel, byte_count):
        time.sleep(1)

        print("--------------------------------------------------")
        print(f"A simpleperf client connecting to server {server_ip}, port {server_port}")
        print("--------------------------------------------------")

        threads = []
        for i in range(parallel):
            t = threading.Thread(target=run_connection, args=(i, server_ip, server_port, time_span, interval, byte_count), name=f"client_connection-{i}")
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    start_client_connections(server_ip, server_port, time_span, interval, parallel, byte_count)


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
        server(args.bind, args.port)  # Removed args.format
    elif args.client:
        try:
            client(args.server_ip, args.port, args.time, args.interval, args.parallel, byte_count)
        except ConnectionRefusedError:
            print(f"Cannot connect to server {args.server_ip} on port {args.port}. Make sure the server is running.")

# Here we run the main function
if __name__ == "__main__":
    main()