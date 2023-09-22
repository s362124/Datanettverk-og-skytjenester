import argparse
import socket
import time
import threading
import re

BUFFER_SIZE = 1000
TIMEOUT = 5

def server_mode(ip, port, file_size):
    # Parse file size from command line arguments
    size_match = re.match(r'^(\d+)([KMGT]B)$', file_size, re.IGNORECASE)
    if not size_match:
        print(f"Invalid file size: {file_size}")
        return
    size = int(size_match.group(1))
    unit = size_match.group(2).upper()
    if unit == 'KB':
        size *= 1024
    elif unit == 'MB':
        size *= 1024 * 1024
    elif unit == 'GB':
        size *= 1024 * 1024 * 1024
    elif unit == 'TB':
        size *= 1024 * 1024 * 1024 * 1024

    print(f"A simpleperf server is listening on port {port}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((ip, port))
        server_socket.listen(1)
        conn, addr = server_socket.accept()

        with conn:
            print(f"A simpleperf client with {addr} is connected with {ip}:{port}")
            start_time = time.time()
            received_data = 0
            while True:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    break
                received_data += len(data)
                if data == b'BYE':
                    conn.sendall(b'ACK: BYE')
                    break

            end_time = time.time()

            elapsed_time = end_time - start_time
            rate = (received_data / 1000) / elapsed_time
            print(f"Received {received_data} bytes in {elapsed_time:.2f} seconds. Bandwidth: {rate:.2f} MB/s")

def print_stats_header():
    print("{:<15} {:<15} {:<15} {:<15}".format("ID", "Interval", "Transfer", "Bandwidth"))

def print_stats(id, ip, port, start_time, end_time, transfer, bandwidth):
    print("{:<15} {:<7.1f}-{:<7.1f} {:<8.1f} MB {:<12.2f} Mbps".format(f"{ip}:{port}", start_time, end_time, transfer, bandwidth))

def client_mode(server_ip, server_port, time_duration, interval, parallel):
    print(f"A simpleperf client connecting to server {server_ip}, port {server_port}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_ip, server_port))
        print(f"Client connected with {server_ip} port {server_port}")
        start_time = time.time()
        sent_data = 0
        last_print_time = start_time
        interval_id = 0

        print_stats_header()

        while time.time() - start_time < time_duration:
            client_socket.sendall(b'0' * BUFFER_SIZE)
            sent_data += BUFFER_SIZE
            time.sleep(0.001)

            if time.time() - last_print_time >= interval:
                elapsed_time = time.time() - start_time
                transfer = (sent_data / (1024 * 1024))
                bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)  # Convert to Mbps
                print_stats(interval_id, server_ip, server_port, max(0, elapsed_time - interval), elapsed_time, transfer, bandwidth)  # Use max function to prevent negative values
                last_print_time = time.time()
                interval_id += 1

        # Print the final interval
        elapsed_time = time_duration
        transfer = (sent_data / (1024 * 1024))
        bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)
        print_stats(interval_id, server_ip, server_port, elapsed_time - interval, elapsed_time, transfer, bandwidth)

        client_socket.sendall(b'BYE')

        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if data == b'ACK: BYE':
                break

        end_time = time.time()
        elapsed_time = end_time - start_time
        transfer = (sent_data / (1024 * 1024))
        bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)  # Convert to Mbps
        print(f"Sent {sent_data} KB in {elapsed_time:.2f} seconds. Total Transfer:{transfer:.1f}MB Bandwidth:{bandwidth:.2f}Mbps")

def main():
    parser = argparse.ArgumentParser(description="Simpleperf network throughput measurement tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", action="store_true", help="Server mode")
    group.add_argument("-c", "--client", action="store_true", help="Client mode")
    parser.add_argument("-b", "--bind", default="", help="IP address to bind to (server mode)")
    parser.add_argument("-p", "--port", type=int, default=8170, help="Port number to use")
    parser.add_argument("-I", "--server_ip", help="Server IP address (client mode)")
    parser.add_argument("-t", "--time", type=int, default=10, help="Time duration in seconds (client mode)")
    parser.add_argument("-f", "--file_size", default="10MB", help="File size for data transfer (e.g. 10MB, 1GB)")
    parser.add_argument("-i", "--interval", type=int, default=5, help="Print statistics per z seconds (client mode)")
    parser.add_argument("-P", "--parallel", type=int, default=1, choices=range(1, 6), help="Create parallel connections to connect to the server and send data (min: 1, max: 5)")

    args = parser.parse_args()

    if args.server:
        server_mode(args.bind, args.port, args.file_size)
    elif args.client:
        if not args.server_ip:
            parser.error("The following argument is required: -I/--server_ip")
        client_mode(args.server_ip, args.port, args.time, args.interval, args.parallel)

if __name__ == "__main__":
    main()