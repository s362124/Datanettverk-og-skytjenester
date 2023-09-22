import socket
import select
import time
import threading
import argparse
import re

BUFFER_SIZE = 4096
TIMEOUT = 5

class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def handle_connection(self, conn, addr):
        start_time = time.time()
        received_data = 0

        while True:
            data = conn.recv(BUFFER_SIZE)
            if data == b'BYE':
                conn.sendall(b'ACK: BYE')
                break
            received_data += len(data)

        end_time = time.time()
        elapsed_time = end_time - start_time
        received_data_mbits = (received_data * 8 / (1000 * 1000))
        rate = received_data_mbits / elapsed_time

        print('ID                           Interval          RECIVED             Rate')
        print(f'{self.ip}:{self.port}      0.0 - {elapsed_time:.1f}       {received_data_mbits:.2f} MB         {rate:.2f} Mbps')

        conn.close()

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.ip, int(self.port)))
            server_socket.listen(5)
            server_socket.settimeout(30)

            print("--------------------------------------------------")
            print(f"A simpleperf server is listening on port {self.port}")
            print("--------------------------------------------------")

            while True:
                try:
                    conn, addr = server_socket.accept()
                    print(f"New connection from: {addr[0]}:{addr[1]}")
                    print(f"A simpleperf client with {addr[0]}:{addr[1]} is connected with {self.ip}:{self.port}")

                    client_thread = threading.Thread(target=self.handle_connection, args=(conn, addr))
                    client_thread.start()

                except socket.timeout:
                    print("Server timeout: No new connections")
                    break
                except Exception as e:
                    print(f"Server error: {e}")
                    break

def server_mode(ip, port):
    server = Server(ip, port)
    server.run()

# The rest of the code remains the same
# The rest of the code remains the same
def client_mode(server_ip, server_port, time_duration, interval, parallel, num_bytes):
    def run_connection(i, server_ip, server_port, time_duration, interval, num_bytes):
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            client_addr = f"{local_ip}:{server_port + i}"
            with socket.create_connection((server_ip, server_port)) as client_socket:
                print(f"Client {client_addr} connected with {server_ip} port {server_port}")

                start_time = time.time()
                sent_data = 0
                last_print_time = start_time

                print(f'ID              Interval     Transfer        Bandwidth')

                while time.time() - start_time < time_duration and (num_bytes == 0 or sent_data < num_bytes):
                    to_send = min(BUFFER_SIZE, num_bytes - sent_data) if num_bytes > 0 else BUFFER_SIZE
                    client_socket.sendall(b'0' * to_send)
                    sent_data += to_send

                    time.sleep(0.001)

                    if time.time() - last_print_time >= interval:
                        elapsed_time = time.time() - start_time
                        transfer = (sent_data / (1024 * 1024))
                        bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)
                        print(f'{client_addr} {elapsed_time - interval:.1f} - {elapsed_time:.1f}s {transfer:.2f}MB {bandwidth:.2f}Mbps')
                        last_print_time = time.time()

                client_socket.sendall(b'BYE')

                while True:
                    data = client_socket.recv(BUFFER_SIZE)
                    if data == b'ACK: BYE':
                        break

                elapsed_time = time.time() - start_time
                transfer = (sent_data / (1024 * 1024))
                bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)
                print(f"\nSent {sent_data} KB in {elapsed_time:.2f} seconds. Total Transfer:{transfer:.1f}MB Bandwidth:{bandwidth:.2f}Mbps\n")


        except Exception as e:
            print(f"Client error: {e}")

    def start_client_connections(server_ip, server_port, time_duration, interval, parallel, num_bytes):
        time.sleep(1)

        print("--------------------------------------------------")
        print(f"A simpleperf client connecting to server {server_ip}, port {server_port}")
        print("--------------------------------------------------")

        threads = []
        for i in range(parallel):
            t = threading.Thread(target=run_connection, args=(i, server_ip, server_port, time_duration, interval, num_bytes), name=f"client_connection-{i}")
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    start_client_connections(server_ip, server_port, time_duration, interval, parallel, num_bytes)



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
    parser.add_argument("-I", "--server_ip", default="127.0.0.1", help="Server IP address (client mode)")
    parser.add_argument("-t", "--time", type=int, default=25, help="Total duration in seconds for which data should be generated")
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

    if args.server:
        server_mode(args.bind, args.port)  # Removed args.format
    elif args.client:
        try:
            client_mode(args.server_ip, args.port, args.time, args.interval, args.parallel, num_bytes)
        except ConnectionRefusedError:
            print(f"Cannot connect to server {args.server_ip} on port {args.port}. Make sure the server is running.")

# Run the main function
if __name__ == "__main__":
    main()