import argparse
import socket
import time
import threading
import re

BUFFER_SIZE = 1000
TIMEOUT = 5
def parse_size(size_str):
    size_match = re.match(r'^(\d+)([BKM]B?)$', size_str, re.IGNORECASE)
    if not size_match:
        raise ValueError(f"Invalid size format: {size_str}")
    size = int(size_match.group(1))
    unit = size_match.group(2).upper()
    if unit == 'KB' or unit == 'K':
        size *= 1024
    elif unit == 'MB' or unit == 'M':
        size *= 1024 * 1024
    # No need for else, as 'B' doesn't require any conversion
    return size


def handle_connection(conn, addr, ip, port):
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
    conn.close()
    end_time = time.time()

    elapsed_time = end_time - start_time
    rate = (received_data / 1000) / elapsed_time
    print(f"Received {received_data} bytes in {elapsed_time:.2f} seconds. Bandwidth: {rate:.2f} MB/s")

def parse_file_size(file_size):
    size_match = re.match(r'^(\d+)([KMGT]B)$', file_size, re.IGNORECASE)
    if not size_match:
        return None
    size = int(size_match.group(1))
    unit = size_match.group(2).upper()
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
    return size

def server_mode(ip, port, file_size):
    size = parse_file_size(file_size)
    if not size:
        print(f"Invalid file size: {file_size}")
        return

    def handle_client(conn, addr):
        handle_connection(conn, addr, ip, port)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((ip, int(port)))
        server_socket.listen(5)
        server_socket.settimeout(30)  # Timeout after 30 seconds of inactivity
        print(f"A simpleperf server is listening on port {port}")

        while True:
            try:
                conn, addr = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_thread.start()

            except socket.timeout:
                print("Server timeout: No new connections")
                break
            except Exception as e:
                print(f"Server error: {e}")
                break

def print_stats_header():
    print("{:<15} {:<15} {:<15} {:<15}".format("ID", "Interval", "Transfer", "Bandwidth"))

def print_stats(id, client_addr, server_ip, server_port, start_time, end_time, transfer, bandwidth):
    print("{:<15} {:<7.1f}-{:<7.1f} {:<8.1f} MB {:<12.2f} Mbps".format(f"{client_addr}", start_time, end_time, transfer, bandwidth))

def check_duration_exceeded(start_time, time_duration):
    return time.time() - start_time >= time_duration

def client_connection(client_addr, server_ip, server_port, time_duration, interval, num_bytes):
    print(f"A simpleperf client connecting to server {server_ip}, port {server_port}")

    try:
        with socket.create_connection((server_ip, server_port)) as client_socket:
            print(f"Client {client_addr} connected with {server_ip} port {server_port}")
            #print(f"Client IP:port connected with {server_ip} port {server_port}\n")
            print()

            start_time = time.time()
            sent_data = 0
            last_print_time = start_time
            interval_id = 0

            print_stats_header()

            while not check_duration_exceeded(start_time, time_duration) and (num_bytes == 0 or sent_data < num_bytes):
                try:
                    to_send = min(BUFFER_SIZE, num_bytes - sent_data) if num_bytes > 0 else BUFFER_SIZE
                    client_socket.sendall(b'0' * to_send)
                    sent_data += to_send
                except BrokenPipeError:
                    print("Connection closed by server")
                    client_socket.close()
                    break

                time.sleep(0.001)

                if time.time() - last_print_time >= interval:
                    last_print_time = time.time()
                    interval_id += 1

            # Print the final interval
            elapsed_time = time_duration
            transfer = (sent_data / (1024 * 1024))
            bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)
            print_stats(interval_id, client_addr, server_ip, server_port, elapsed_time - interval, elapsed_time, transfer, bandwidth)  # Call print_stats only once

            client_socket.sendall(b'BYE')

            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if data == b'ACK: BYE':
                    break

            end_time = time.time()
            elapsed_time = end_time - start_time
            transfer = (sent_data / (1024 * 1024))
            bandwidth = (sent_data * 8) / (elapsed_time * 1000 * 1000)  # Convert to Mbps
            print(f"\nSent {sent_data} KB in {elapsed_time:.2f} seconds. Total Transfer:{transfer:.1f}MB Bandwidth:{bandwidth:.2f}Mbps\n")

    except Exception as e:
        print(f"Client error: {e}")

def client_mode(server_ip, server_port, time_duration, interval, parallel, num_bytes):
    #print(f"A simpleperf client connecting to server {server_ip}, port {server_port}\n")

    time.sleep(1)  # Give the server time to start up

    threads = []
    for i in range(parallel):
        # Get the local IP address to pass it as a client_addr parameter
        local_ip = socket.gethostbyname(socket.gethostname())
        client_addr = f"{local_ip}:{server_port + i + 1}"
        t = threading.Thread(target=client_connection, name=f"client_connection-{i}", args=(client_addr, server_ip, server_port, time_duration, interval, num_bytes))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

def main():
    parser = argparse.ArgumentParser(description="Simpleperf network throughput measurement tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", action="store_true", help="Server mode")
    group.add_argument("-c", "--client", action="store_true", help="Client mode")
    parser.add_argument("-b", "--bind", default="", help="IP address to bind to (server mode)")
    parser.add_argument("-p", "--port", type=int, default=8700, help="Port number to use")
    parser.add_argument("-I", "--server_ip", help="Server IP address (client mode)")
    parser.add_argument("-t", "--time", type=int, default=10, help="Time duration in seconds (client mode)")
    parser.add_argument("-f", "--file_size", default="10MB", help="File size for data transfer (e.g. 10MB, 1GB)")
    parser.add_argument("-i", "--interval", type=int, default=None, help="Print statistics per z seconds (client mode)")
    parser.add_argument("-P", "--parallel", type=int, default=1, choices=range(1, 6), help="Create parallel connections to connect to the server and send data (min: 1, max: 5)")
    parser.add_argument("-n", "--num", type=str, default="0B", help="Transfer number of bytes specified by -n flag, it should be either in B, KB or MB.")

    args = parser.parse_args()

    num_bytes = parse_size(args.num)
    if args.interval is None:
        args.interval = args.time

    if args.server:
        server_mode(args.bind, args.port, args.file_size)
    elif args.client:
        if not args.server_ip:
            parser.error("The following argument is required: -I/--server_ip")
        client_mode(args.server_ip, args.port, args.time, args.interval, args.parallel, num_bytes)

if __name__ == "__main__":
    main()


