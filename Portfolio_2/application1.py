import argparse
import socket
import struct
import time
import logging
from struct import *

# Set up logging to display information level logs and above with a specific format
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Define constants for the DRTP flags, window size and timeout
SYN = 0b1000  # Synchronization flag
ACK = 0b0100  # Acknowledgement flag
FIN = 0b0010  # Finish flag
RST = 0b0001  # Reset flag
WINDOW_SIZE = 0 # Size of the window for flow control
#TIMEOUT = 2.0  # Timeout period for receiving packets

# Define the format of the DRTP header
HEADER_FORMAT = '!IIHH'

# Define the size of the data part of a DRTP packet, in bytes
PACKET_DATA_SIZE = 1460  

# Function to parse a DRTP header from a string
def parse_header(header):
    header_from_msg = unpack(HEADER_FORMAT, header)
    return header_from_msg

# Function to parse the flags from a flags field
def parse_flags(flags):
    syn = flags & (1 << 3)  # SYN flag is the 4th bit from the right
    ack = flags & (1 << 2)  # ACK flag is the 3rd bit from the right
    fin = flags & (1 << 1)  # FIN flag is the 2nd bit from the right
    return syn, ack, fin

def send_packet(sock, packet, address):
    packet_header = struct.pack(HEADER_FORMAT, packet['seq'], packet['ack'], packet['flags'], packet['window'])
    sock.sendto(packet_header + packet['data'], address)

# Function to receive a DRTP packet from a socket
def receive_packet(sock):
    try:
        data, address = sock.recvfrom(1472)  # Maximum DRTP packet size is 1472 bytes
    except socket.timeout:
        logging.warning("Socket timeout occurred. Ignoring this packet.")
        return None, None
    
    data_len = len(data)
    if data_len < 12:  # If the packet is smaller than the header size, it's invalid
        logging.warning("Received data is less than 12 bytes. Ignoring this packet.")
        packet = None
    else: 
        packet_header = struct.unpack(HEADER_FORMAT, data[:12])  # Unpack the header from the first 12 bytes of the packet
        packet = {'seq': packet_header[0], 'ack': packet_header[1], 'flags': packet_header[2], 'window': packet_header[3], 'data': data[12:]}
        logging.info(f"Received packet with seq {packet['seq']}")  # Log the sequence number of the received packet
    return packet, address

# Function to create a DRTP packet from sequence number, acknowledgment number, flags, window size and data
def create_packet(seq, ack, flags, win, data):
    header = pack (HEADER_FORMAT, seq, ack, flags, win)
    packet = header + data
    """Create a DRTP packet"""
    #return {'seq': seq, 'ack': ack, 'flags': flags, 'window': window, 'data': data}
    return packet

# Function to send an ACK packet
def send_ack(sock, address, seq):
    # Create an ACK packet with the received sequence number
    packet = create_packet(0, seq, ACK, WINDOW_SIZE, b'')
    # Log the sequence number of the ACK packet
    logging.info(f"Sent ack for seq: {seq}")
    # Send the ACK packet
    send_packet(sock, packet, address)

# Function to receive an ACK packet and check if it acknowledges the sent packet
def receive_ack(sock, seq):
    # Receive a packet
    packet, _ = receive_packet(sock)
    # If the received packet is an ACK packet for the sent packet
    if packet and packet['ack'] == seq:
        # Log the sequence number of the acknowledged packet
        logging.info(f"Received final ACK for packet: {seq}")  
    # Return True if the received packet is an ACK for the sent packet, False otherwise
    return packet and packet['ack'] == seq

# Function to read a file and divide it into DRTP packets
def read_file_into_packets(filename):
    # If no filename is provided, log an error and exit the program
    if filename is None:
        logging.error("No file specified for transfer. Please specify a file with the -f option.")
        exit(1)

    # Create an empty list to store the packets
    packets = []
    # Initialize the sequence number to 0
    seq = 0

    # Open the file in read binary mode
    with open(filename, 'rb') as f:
        while True:
            # Read 1460 bytes from the file
            data = f.read(1460)
            # If no more data is available, exit the loop
            if not data:
                break

            # Create a packet with the read data
            packet = create_packet(seq, 0, 0, WINDOW_SIZE, data)
            # Add the packet to the list of packets
            packets.append(packet)
            # Increase the sequence number by 1
            seq += 1

    # Return the list of packets
    return packets

# Function to read a file and divide it into DRTP packets
def make_packets(file_name):
    # If no filename is provided, log an error and exit the program
    if file_name is None:
        logging.error("No file specified for transfer. Please specify a file with the -f option.")
        exit(1)

    # Create an empty list to store the packets
    packets = []
    # Initialize the sequence number to 0
    seq = 0

    # Open the file in read binary mode
    with open(file_name, 'rb') as f:
        while True:
            # Read PACKET_DATA_SIZE bytes from the file
            data = f.read(PACKET_DATA_SIZE)
            # If no more data is available, exit the loop
            if not data:
                break

            # Create a packet with the read data
            packet = create_packet(seq, 0, 0, WINDOW_SIZE, data)
            # Add the packet to the list of packets
            packets.append(packet)
            # Increase the sequence number by 1
            seq += 1

    # Return the list of packets
    return packets

# Function to send a FIN (finish) packet
def send_fin(sock, address):
    # Create a FIN packet
    fin_packet = create_packet(0, FIN, WINDOW_SIZE, b'')
    # Send the FIN packet
    send_packet(sock, fin_packet, address)

def stop_and_wait_send(sock, file_name, address):
    # Start time
    start_time = time.time()

    # Initialize sent_bytes to zero
    sent_bytes = 0

    # Get the file extension
    file_extension = file_name.split('.')[-1]
    # Create a packet with the file extension
    ext_packet = create_packet(0, 0, 0, 0, file_extension.encode())
    # Send the packet with the file extension
    sock.sendto(ext_packet, address)
    # Log the file extension
    print(f"Sent file extension: {file_extension}")

    # Open the file in read binary mode
    with open(file_name, 'rb') as f:
        # Start sequence number from 1 as 0 is used for file extension packet
        seq = 1

        ack_loss_simulated = False  

        while True:
            # Read PACKET_DATA_SIZE bytes from the file
            data = f.read(PACKET_DATA_SIZE)
            # If no more data is available, exit the loop
            if not data:
                break

            # Create a packet with the read data
            packet = create_packet(0, seq, 0, 0, data)
            # Send the packet
            sock.sendto(packet, address)
            # Update sent_bytes
            sent_bytes += len(packet)
            # Log the sequence number of the sent packet
            print(f"Sent packet with seq: {seq}")

            try:
                # Try to receive an ACK packet
                packet, address = sock.recvfrom(1472)
                # Parse the header of the received packet
                _, ack, flag, _ = parse_header(packet[:12])

                # If we have not simulated ack loss yet, and sequence number is 5 (example)
                if not ack_loss_simulated and seq == 5:
                    # Skip this ack, do not print it, and do not increment sequence number
                    ack_loss_simulated = True
                    continue
                # Log the received acknowledgment
                print(f"Received ack: {ack}")
            except socket.timeout:
                # If a timeout occurs, resend the packet
                continue

            # Increment the sequence number
            seq += 1

        # Create a FIN packet to indicate the end of the transmission
        fin_packet = create_packet(0, seq, FIN, 0, b'')
        # Send the FIN packet
        sock.sendto(fin_packet, address)
        # Update sent_bytes
        sent_bytes += len(fin_packet)
        # Log the sequence number of the sent FIN packet
        print(f"Sent FIN packet with seq: {seq}")

    # End time
    end_time = time.time()
    # Duration
    duration = end_time - start_time

    # Calculate and print the total throughput and the number of bytes sent
    rate = round((sent_bytes / duration) * 8 / 1000000, 2)
    no_of_bytes = round(sent_bytes / 1024, 2)
    print(f'Total throughput: {rate} Mbps and the number of bytes sent {no_of_bytes} KB')

# Function to receive files using Stop-and-Wait protocol
def stop_and_wait_receive(sock, filename, address):
    # Initial sequence number and window size
    seq_num = 0
    window = 0

    # First packet contains the file extension
    packet, addr = sock.recvfrom(1472)  # Receive the packet
    _, seq, flag, _ = parse_header(packet[:12])  # Parse the header
    file_extension = packet[12:].decode()  # Decode the file extension from the packet data
    print(f"Received file extension: {file_extension}")  # Print the received file extension

    # Use the received extension to create the file
    filename = f'received_file.{file_extension}'  # Create filename

    # Send ACK for the file extension packet
    ack_packet = create_packet(seq_num + 1, seq_num + 1, ACK, window, b'')  # Create ACK packet
    sock.sendto(ack_packet, addr)  # Send ACK packet
    print(f"Sent ack for packet: {seq_num}")  # Print ACK message
    seq_num += 1  # Increment sequence number

    # Open the file in write binary mode
    with open(filename, 'wb') as f:
        # Initialize a variable to simulate ack loss
        ack_loss_simulated = False

        while True:
            packet, addr = sock.recvfrom(1472)  # Receive the packet
            _, seq, flag, _ = parse_header(packet[:12])  # Parse the header
            print(f"Received packet: {seq}")  # Print received packet sequence number
            data = packet[12:]  # Extract data from the packet

            # If the sequence number of the received packet matches the expected sequence number
            if seq == seq_num:
                f.write(data)  # Write the received data into the file
                seq_num += 1  # Increment sequence number

            # If we have not simulated ack loss yet, and sequence number is 5 (example)
            if not ack_loss_simulated and seq == 5:
                # Skip this ack, do not send it
                ack_loss_simulated = True
                continue

            # Create and send ACK packet for the received packet
            ack_packet = create_packet(seq_num, seq_num, ACK, window, b'')
            sock.sendto(ack_packet, addr)
            print(f"Sent ack for packet: {seq_num}")  # Print ACK message

            # Check if this is the last packet
            _, _, fin_flag = parse_flags(flag)
            if fin_flag:
                print("File received successfully!")  # Print successful file received message
                break

def SR_send(sock, file_name, address):
    WINDOW_SIZE = 15
    sock.settimeout(0.5)  # 500 ms timeout

    # Initialize sent_bytes to zero
    sent_bytes = 0

    # Start time
    start_time = time.time()

    # Get the file extension
    file_extension = file_name.split('.')[-1]
    # Create a packet with the file extension
    ext_packet = create_packet(0, 0, 0, 0, file_extension.encode())
    # Send the packet with the file extension
    sock.sendto(ext_packet, address)
    sent_bytes += len(ext_packet) # Update sent_bytes
    # Log the file extension
    print(f"Sent file extension: {file_extension}")

    base = 1
    next_seq_num = 1
    packets = {}
    acked = {}

    # Open the file in read binary mode
    with open(file_name, 'rb') as f:
        while True:
            while next_seq_num < base + WINDOW_SIZE:
                data = f.read(PACKET_DATA_SIZE)
                if not data:
                    break
                packet = create_packet(0, next_seq_num, 0, 0, data)
                sock.sendto(packet, address)
                sent_bytes += len(packet) # Update sent_bytes
                packets[next_seq_num] = packet
                acked[next_seq_num] = False
                print(f"Sent packet with seq: {next_seq_num}")
                next_seq_num += 1

            # Acknowledgement and retransmission
            while base != next_seq_num:
                try:
                    packet, address = sock.recvfrom(1472)
                    _, ack, _, _ = parse_header(packet[:12])
                    print(f"Received ack: {ack}")
                    if ack in acked and not acked[ack]:  # Make sure it's an ACK for a packet we sent
                        acked[ack] = True
                        while base in acked and acked[base]:  # Move the base if we can
                            base += 1
                except socket.timeout:  # If no ACK was received, resend all unacknowledged packets
                    for seq_num in range(base, next_seq_num):
                        if not acked[seq_num]:
                            print(f"Resending packet with seq: {seq_num}")
                            sock.sendto(packets[seq_num], address)

            if not data:  # If we've sent all data
                break

    # now that all packets have been acknowledged, send the FIN packet
    fin_packet = create_packet(0, next_seq_num, FIN, 0, b'')
    sock.sendto(fin_packet, address)
    sent_bytes += len(fin_packet) # Update sent_bytes
    print(f"Sent FIN packet with seq: {next_seq_num}")

    # End time
    end_time = time.time()
    # Duration
    duration = end_time - start_time

    # Calculate and print the total throughput and the number of bytes sent
    rate = round((sent_bytes / duration) * 8 / 1000000, 2)
    no_of_bytes = round(sent_bytes / 1024, 2)
    print(f'Total throughput: {rate} Mbps and the number of bytes sent {no_of_bytes} KB')

def SR_receive(sock, filename, address):
    # Initial sequence number and window size
    seq_num = 0
    window = 15

    expected_seq_num = 1

    buffer = {}  # Buffer to hold out-of-order packets

    # First packet contains the file extension
    packet, addr = sock.recvfrom(1472)  # Receive the packet
    _, seq, flag, _ = parse_header(packet[:12])  # Parse the header
    file_extension = packet[12:].decode()  # Decode the file extension from the packet
    # Send ACK for the file extension packet
    ack_packet = create_packet(seq_num + 1, seq_num + 1, ACK, window, b'')  # Create ACK packet
    sock.sendto(ack_packet, addr)  # Send ACK packet
    print(f"Sent ack for packet: {seq_num}")  # Print ACK message
    seq_num += 1  # Increment sequence number

    # Use the received extension to create the file
    filename = f'received_file.{file_extension}'  # Create filename

    # Open the file in write binary mode
    with open(filename, 'wb') as f:
        while True:
            packet, addr = sock.recvfrom(1472)  # Receive the packet
            _, seq, flag, _ = parse_header(packet[:12])  # Parse the header
            print(f"Received packet: {seq}")  # Print received packet sequence number
            data = packet[12:]  # Extract data from the packet

            if seq >= expected_seq_num and seq < expected_seq_num + window:  # If packet is within current window
                if seq == expected_seq_num:
                    f.write(data)  # Write the received data into the file
                    expected_seq_num += 1

                    # Write consecutive packets in buffer to file
                    while expected_seq_num in buffer:
                        f.write(buffer[expected_seq_num])  # Write the received data into the file
                        del buffer[expected_seq_num]  # Remove packet from buffer
                        expected_seq_num += 1
                else:
                    buffer[seq] = data

                # Send ack for received packet
                ack_packet = create_packet(seq, seq, ACK, window, b'')
                sock.sendto(ack_packet, addr)
                print(f"Sent ack for packet: {seq}")  # Print ACK message
            elif seq < expected_seq_num:  # If packet is out of order
                ack_packet = create_packet(seq, seq, ACK, window, b'')
                sock.sendto(ack_packet, addr)
                print(f"Sent ack for packet: {seq}")  # Print ACK message

            # Check if this is the last packet
            _, _, fin_flag = parse_flags(flag)
            if fin_flag:
                print("File received successfully!")  # Print successful file received message
                break

# Function to send files using Go-Back-N protocol
def GBN_send(sock, file_name, address):
    WINDOW_SIZE = 15
    sock.settimeout(0.5)  # 500 ms timeout

    # Initialize sent_bytes to zero
    sent_bytes = 0

    # Start time
    start_time = time.time()

    # Get the file extension
    file_extension = file_name.split('.')[-1]
    # Create a packet with the file extension
    ext_packet = create_packet(0, 0, 0, 0, file_extension.encode())
    # Send the packet with the file extension
    sock.sendto(ext_packet, address)
    sent_bytes += len(ext_packet)  # Update sent_bytes
    # Log the file extension
    print(f"Sent file extension: {file_extension}")

    base = 1
    next_seq_num = 1
    packets = {}

    # Open the file in read binary mode
    with open(file_name, 'rb') as f:
        while True:
            while next_seq_num < base + WINDOW_SIZE:
                data = f.read(PACKET_DATA_SIZE)
                if not data:
                    break
                packet = create_packet(0, next_seq_num, 0, 0, data)
                sock.sendto(packet, address)
                sent_bytes += len(packet)  # Update sent_bytes
                packets[next_seq_num] = packet
                print(f"Sent packet with seq: {next_seq_num}")
                next_seq_num += 1

            while True:
                try:
                    packet, address = sock.recvfrom(1472)
                    _, ack, flag, _ = parse_header(packet[:12])
                    print(f"Received ack: {ack}")
                    base = ack + 1
                    if base == next_seq_num:
                        break
                except socket.timeout:
                    for seq_num in range(base, next_seq_num):
                        print(f"Resending packet with seq: {seq_num}")
                        sock.sendto(packets[seq_num], address)

            if not data:
                break

        # Create a FIN packet to indicate the end of the transmission
        fin_packet = create_packet(0, next_seq_num, FIN, 0, b'')
        # Send the FIN packet
        sock.sendto(fin_packet, address)
        sent_bytes += len(fin_packet)  # Update sent_bytes
        # Log the sequence number of the sent FIN packet
        print(f"Sent FIN packet with seq: {next_seq_num}")

    # End time
    end_time = time.time()
    # Duration
    duration = end_time - start_time

    # Calculate and print the total throughput and the number of bytes sent
    rate = round((sent_bytes / duration) * 8 / 1000000, 2)
    no_of_bytes = round(sent_bytes / 1024, 2)
    print(f'Total throughput: {rate} Mbps and the number of bytes sent {no_of_bytes} KB')

def GBN_receive(sock, filename, addr):
    # Initial sequence number and window size
    seq_num = 0
    window = 15

    expected_seq_num = 1

    # First packet contains the file extension
    packet, addr = sock.recvfrom(1472)  # Receive the packet
    _, seq, flag, _ = parse_header(packet[:12])  # Parse the header
    file_extension = packet[12:].decode()  # Decode the file extension from the packet data
    print(f"Received file extension: {file_extension}")  # Print the received file extension

    # Use the received extension to create the file
    filename = f'received_file.{file_extension}'  # Create filename

    # Send ACK for the file extension packet
    ack_packet = create_packet(seq_num + 1, seq_num + 1, ACK, window, b'')  # Create ACK packet
    sock.sendto(ack_packet, addr)  # Send ACK packet
    print(f"Sent ack for packet: {seq_num}")  # Print ACK message
    seq_num += 1  # Increment sequence number

    # Open the file in write binary mode
    with open(filename, 'wb') as f:
        while True:
            packet, addr = sock.recvfrom(1472)  # Receive the packet
            _, seq, flag, _ = parse_header(packet[:12])  # Parse the header
            print(f"Received packet: {seq}")  # Print received packet sequence number
            data = packet[12:]  # Extract data from the packet

            # If the sequence number of the received packet matches the expected sequence number
            if seq == expected_seq_num:
                f.write(data)  # Write the received data into the file
                expected_seq_num += 1

            # Create and send ACK packet for the received packet
            ack_packet = create_packet(expected_seq_num - 1, expected_seq_num - 1, ACK, window, b'')
            sock.sendto(ack_packet, addr)
            print(f"Sent ack for packet: {expected_seq_num - 1}")  # Print ACK message

            # Check if this is the last packet
            _, _, fin_flag = parse_flags(flag)
            if fin_flag and seq == expected_seq_num - 1:
                print("File received successfully!")  # Print successful file received message
                break

def run_as_server(args):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:  # Creating a UDP socket
        sock.bind((args.i, args.p))  # Binding the socket to a specific IP address and port
        print("Waiting for SYN from client...")  # Display message that the server is waiting for a connection

        while True:  # Infinite loop to keep the server running
            # Receive SYN from client
            packet, address = sock.recvfrom(1472)  # Waiting for a packet from a client
            _,_, flag, _ = parse_header(packet[:12])  # Parsing the header of the received packet
            syn_flag, _, _ = parse_flags(flag)  # Parsing the flags from the header
            if syn_flag:
                print("SYN received from client")  # If SYN flag is set, print that SYN is received
            
            # If the packet is not a SYN packet, wait for the next packet
            if not packet or struct.unpack(HEADER_FORMAT, packet[:12])[2] != SYN:
                continue

            # Send SYN-ACK back to client
            syn_ack = create_packet(0,0,12,0,b'')  # Create a SYN-ACK packet
            sock.sendto(syn_ack, address)  # Send the SYN-ACK packet to the client
            print("SYN-ACK sent to client")  # Print that SYN-ACK is sent to the client

            # Receive final ACK from client
            packet, address = sock.recvfrom(1472)  # Waiting for the ACK packet from the client
            _,_, flag, _ = parse_header(packet[:12])  # Parsing the header of the received packet
            _, ack_flag, _, = parse_flags(flag)  # Parsing the flags from the header
            
            if ack_flag:
                print("ACK received from client: Connection established successfully!")  # If ACK flag is set, print that ACK is received

             # Set a timeout of 0.5 seconds
            sock.settimeout(0.5)

            # Define the file name to save received data
            file_name = 'received_file.txt'

            # Receive file based on the selected reliability protocol
            if args.r == 'stop_and_wait':
                stop_and_wait_receive(sock, file_name, address)  # If stop and wait protocol is selected, call the appropriate function
            elif args.r == 'GBN':
                GBN_receive(sock, file_name, address)  # If Go-Back-N protocol is selected, call the appropriate function
            elif args.r == 'SR':
                SR_receive(sock, file_name, address)  # If Selective Repeat protocol is selected, call the appropriate function

                packet, address = sock.recvfrom(1472)  # Waiting for a packet from a client
                _,_, flag, _ = parse_header(packet[:12])  # Parsing the header of the received packet
                _, _, fin_flag = parse_flags(flag)  # Parsing the flags from the header
                if fin_flag:
                    print(f"File complete!")  # If FIN flag is set, print that file transmission is complete
                    break  # Exit the loop after receiving the file

            if args.r != 'SR':  # For non-SR protocols
                break  # Exit the loop

        print("Server is shutting down.")  # Indicate that the server is shutting down after the file is received

def run_as_client(args):
    if not args.f:  # Check if a file is specified
        print("No file specified. Please specify a file with the -f option.")  # If not, print an error message
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create a UDP socket
    
    sock.settimeout(0.5)  # Set a timeout of 0.5 seconds
    address = (args.i, args.p)  # Define server address
   
    syn = create_packet(0,0,8,0,b'')  # Create a SYN packet
    sock.sendto(syn, address)  # Send the SYN packet to the server
    print("SYN sent to server")  # Print that SYN is sent to the server

    packet, address = sock.recvfrom(1472)  # Wait for a SYN-ACK packet from the server
    _,_, flag, _ = parse_header(packet[:12])  # Parsing the header of the received packet
    syn_flag, ack_flag, _, = parse_flags(flag)  # Parsing the flags from the header
    if syn_flag and ack_flag:  # If SYN and ACK flags are set
        print("Received SYN-ACK from server")  # Print that SYN-ACK is received from the server

   
    ack = create_packet(0,0,4,0,b'')  # Create an ACK packet
    sock.sendto(ack, address)  # Send the ACK packet to the server
    print("ACK sent to client")  # Print that ACK is sent to the server
    #print("ACK sent to server")

    # Send file based on the selected reliability protocol
    if args.r == 'stop_and_wait':
        stop_and_wait_send(sock, args.f, address)  # If stop and wait protocol is selected, call the appropriate function
    elif args.r == 'GBN':
        GBN_send(sock, args.f, address)  # If Go-Back-N protocol is selected, call the appropriate function
    elif args.r == 'SR':
        SR_send(sock, args.f, address)  # If Selective Repeat protocol is selected, call the appropriate function

    # Two-way handshake for connection teardown
    fin = create_packet(0,0,2,0,b'')  # Create a FIN packet
    sock.sendto(fin, address)  # Send the FIN packet to the server
    print("FIN sent to server")  # Print that FIN is sent to the server

def main():
    # Create a command-line argument parser
    parser = argparse.ArgumentParser(description='File transfer application')

    # Define command-line arguments
    parser.add_argument('-s', action='store_true', help='Run as server')
    parser.add_argument('-c', action='store_true', help='Run as client')
    parser.add_argument('-i', type=str, help='IP address')
    parser.add_argument('-p', type=int, help='Port number')
    parser.add_argument('-r', type=str, choices=['stop_and_wait', 'GBN', 'SR'], help='Reliability method')
    parser.add_argument('-f', type=str, help='File to transfer')
    parser.add_argument('-t', type=str, help='Test case')
    
    # Parse the command-line arguments
    args = parser.parse_args()

    # Check if the provided port number is within the valid range
    if args.p < 1024 or args.p > 65535:
        parser.error("The port number must be within the range [1024, 65535]")

    # Check the specified mode (server or client) and call the appropriate function
    if args.s:
        run_as_server(args)  # If -s flag is set, run the program as server
    elif args.c:
        run_as_client(args)  # If -c flag is set, run the program as client
    else:
        # If neither -s or -c is set, print an error message
        logging.error("Please specify either -s to run as server or -c to run as client.")

# Check if the script is run directly (not imported as a module), and if so, call the main function
if __name__ == "__main__":
    main()