import argparse
import socket
import struct
import time
import logging
from struct import *

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Define constants for flags
SYN = 0b1000
ACK = 0b0100
FIN = 0b0010
RST = 0b0001
WINDOW_SIZE = 5
TIMEOUT = 2.0  # Increased timeout to deal with synchronization issue

# Header format
HEADER_FORMAT = '!IIHH'

# Size of the data in each packet, in bytes
PACKET_DATA_SIZE = 1460  
def parse_header(header):
    #taks a header of 12 bytes as an argument,
    #unpacks the value based on the specified header_format
    #and return a tuple with the values
    header_from_msg = unpack(HEADER_FORMAT, header)
    #parse_flags(flags)
    return header_from_msg


def parse_flags(flags):
    syn = flags & (1 << 3)
    ack = flags & (1 << 2)
    fin = flags & (1 << 1)
    return syn, ack, fin

def send_packet(sock, packet, address):
    """Send a packet over a socket"""
    packet_header = struct.pack(HEADER_FORMAT, packet['seq'], packet['ack'], packet['flags'], packet['window'])
    sock.sendto(packet_header + packet['data'], address)

def receive_packet(sock):
    """Receive a packet from a socket"""
    try:
        data, address = sock.recvfrom(1472)  # header (12) + data (1460) = 1472 bytes
    except socket.timeout:
        logging.warning("Socket timeout occurred. Ignoring this packet.")
        return None, None
    
    data_len = len(data)
    if data_len < 12:
        # handle it
        logging.warning("Received data is less than 12 bytes. Ignoring this packet.")
        packet = None
    else: 
        packet_header = struct.unpack(HEADER_FORMAT, data[:12])  # 12 bytes header data[:12] header, user's data = data[12:]
        packet = {'seq': packet_header[0], 'ack': packet_header[1], 'flags': packet_header[2], 'window': packet_header[3], 'data': data[12:]}
        logging.info(f"Received packet with seq {packet['seq']}")  # Endret melding
        return packet, address

    return packet, address


def create_packet(seq, ack, flags, win, data):
    header = pack (HEADER_FORMAT, seq, ack, flags, win)
    packet = header + data
    """Create a DRTP packet"""
    #return {'seq': seq, 'ack': ack, 'flags': flags, 'window': window, 'data': data}
    return packet

def send_ack(sock, address, seq):
    """Send an ACK packet"""
    packet = create_packet(0, seq, ACK, WINDOW_SIZE, b'')
    logging.info(f"Sent ack for seq: {seq}")  # Endret melding
    send_packet(sock, packet, address)

def receive_ack(sock, seq):
    """Receive an ACK packet and return whether it acknowledges the given sequence number"""
    packet, _ = receive_packet(sock)
    if packet and packet['ack'] == seq:
        logging.info(f"Received final ACK for packet: {seq}")  
    return packet and packet['ack'] == seq

def read_file_into_packets(filename):
    """Read a file and divide it into DRTP packets"""
    if filename is None:
        logging.error("No file specified for transfer. Please specify a file with the -f option.")
        exit(1)

    packets = []
    seq = 0

    with open(filename, 'rb') as f:
        while True:
            data = f.read(1460)  # Maximum safe UDP payload is 508 bytes
            if not data:
                break

            packet = create_packet(seq, 0, 0, WINDOW_SIZE, data)
            packets.append(packet)
            seq += 1

    return packets

def make_packets(file_name):
    """Read a file and divide it into DRTP packets"""
    if file_name is None:
        logging.error("No file specified for transfer. Please specify a file with the -f option.")
        exit(1)

    packets = []
    seq = 0

    with open(file_name, 'rb') as f:
        while True:
            data = f.read(PACKET_DATA_SIZE)
            if not data:
                break

            packet = create_packet(seq, 0, 0, WINDOW_SIZE, data)
            packets.append(packet)
            seq += 1

    return packets

def send_fin(sock, address):
    """Send a FIN packet"""
    fin_packet = create_packet(0, FIN, WINDOW_SIZE, b'')
    send_packet(sock, fin_packet, address)

# Define methods for reliability functions
def stop_and_wait_send(sock, file_name, address):
    with open(file_name, 'rb') as f:
        seq = 0
        while True:
            data = f.read(PACKET_DATA_SIZE)
            if not data:
                break
            packet = create_packet(seq, 0, 0, WINDOW_SIZE, data)
            while True:
                try:
                    send_packet(sock, packet, address)
                    receive_ack(sock, seq + 1)
                    break
                except TimeoutError:
                    continue  # resend packet
            seq += 1

def stop_and_wait_receive(sock, filename):
    """Stop-and-Wait reliability function for receiving files"""
    seq_num = 0
    #ack_num = 0
    window = 64

    with open(filename, 'wb') as f:
        while True:
            packet, addr = receive_packet(sock)
            #logging.debug("Received packet: %s", packet)  # Logging out data received
            if packet['flags'] & FIN:
            
                #print("received a fin message from the client")
                send_ack(sock, addr, packet['seq'] + 1)
                break

            if packet['seq'] == seq_num:
                f.write(packet['data'])
                seq_num += 1

            ack_packet = create_packet(seq_num, seq_num, ACK, window, b'')
            send_packet(sock, ack_packet, addr)

def GBN_send(sock, file_name, address):
    """Go-Back-N reliability function for sending files"""
    seq_num = 0
    window_size = 10
    base = 0

    # Call make_packets function to create a list of packets
    packets = make_packets(file_name)

    # Number of packets
    num_packets = len(packets)

    while base < num_packets:
        # Send all the packets in the window
        for i in range(base, min(base + window_size, num_packets)):
            print("Sending packet with sequence number:", i)  # Debugging print
            send_packet(sock, packets[i], address)

        # Start a timer
        start_time = time.time()

        while True:
            try:
                # Try to receive ACK
                ack_num = receive_ack(sock, seq_num)

                # If we receive an ACK for the first in-flight packet
                if ack_num >= base:
                    base = ack_num + 1
                    print(f"Received ACK for packet number {ack_num}, moving base to {base}")  # Existing line
                    # Add a new line to log information
                    logging.info(f"Received ACK for packet number {ack_num}, moving base to {base}")

            except socket.timeout:
                # If timeout, break the loop to resend all packets in the window
                print("Timeout occurred, resending the packets")  # Debugging print
                break

            # Check if the time has exceeded the timeout
            if time.time() - start_time > TIMEOUT:
                print("Timeout exceeded, resending the packets")  # Debugging print
                break

            # Add a condition to break out of the loop when all packets have been acknowledged
            if base == num_packets:
                print("All packets have been acknowledged, breaking out of the loop.")
                break

    # Send FIN packet
    send_fin(sock, address)

def GBN_receive(sock, filename, address):
    """Go-Back-N reliability function for receiving files"""
    expected_seq_num = 0

    with open(filename, 'wb') as f:
        while True:
            try:
                logging.info("Waiting to receive packet...")
                packet, _ = receive_packet(sock)
                logging.info(f"Received packet with seq num: {packet['seq']}")
                
                if packet['seq'] == expected_seq_num:
                    logging.info("Writing packet data to file...")
                    f.write(packet['data'])
                    
                    logging.info(f"Sending ACK for packet: {expected_seq_num}")
                    send_ack(sock, address, expected_seq_num)
                    expected_seq_num += 1
                else:
                    logging.info(f"Packet out of order. Sending ACK for the last received in-order packet: {expected_seq_num - 1}")
                    send_ack(sock, address, expected_seq_num - 1)
                
                if packet['flags'] & FIN:
                    logging.info("FIN flag detected. Breaking the loop.")
                    break
            except socket.timeout:
                logging.warning("Socket timeout. Continuing to next packet...")
                continue
            except Exception as e:
                logging.error(f"Error receiving packet: {str(e)}")
                continue

def SR(sock, filename, address):
    """Selective-Repeat reliability function"""
    packets = read_file_into_packets(filename)
    base = 0
    next_seq_num = 0
    acked = [False] * len(packets)

    while base < len(packets):
        while next_seq_num < min(base + WINDOW_SIZE, len(packets)):
            if not acked[next_seq_num]:
                send_packet(sock, packets[next_seq_num], address)
            next_seq_num += 1

        # Wait for ACKs
        try:
            while True:
                ack_packet, _ = receive_packet(sock)
                if ack_packet['flags'] == ACK:
                    ack = ack_packet['ack']
                    if base <= ack < min(base + WINDOW_SIZE, len(packets)):
                        acked[ack] = True
                        while acked[base]:
                            base += 1
                        # Add a new line to log information
                        logging.info(f"Received ACK for packet number {ack}, moving base to {base}")
                if base == len(packets):
                    break
        except socket.timeout:
            continue


def run_as_server(args):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((args.i, args.p))
        print("Waiting for SYN from client...")  # Endret melding
        
        
        while True:
            # Receive SYN from client
            packet, address = sock.recvfrom(1472)  # wait for client connection without timeout
            _,_, flag, _ = parse_header(packet[:12])
            syn_flag, _, _, = parse_flags(flag)
            if syn_flag:
                print("SYN received from client")  # Endret melding
            
            
            if not packet or struct.unpack(HEADER_FORMAT, packet[:12])[2] != SYN:
                continue

            # Send SYN-ACK back to client
            #send_ack(sock, address, struct.unpack(HEADER_FORMAT, packet[:12])[0] + 1)
            syn_ack = create_packet(0,0,12,0,b'')
            sock.sendto(syn_ack, address)
            print("SYN-ACK sent to client")  # Endret melding

            # Receive final ACK from client
            packet, address = sock.recvfrom(1472)
            _,_, flag, _ = parse_header(packet[:12])
            _, ack_flag, _, = parse_flags(flag)
            
            if ack_flag:
                print("ACK received from client: Connection established successfully!")  # Endret melding

            # Set a timeout of 0.5 seconds
            sock.settimeout(0.5)

            # Define the file name to save received data
            file_name = 'received_file.txt'

            # Receive file
            if args.r == 'stop_and_wait':
                stop_and_wait_receive(sock, file_name)
                break  # Add break statement here
            elif args.r == 'GBN':
                GBN_receive(sock, file_name, address)
                break  # Add break statement here
            elif args.r == 'SR':
                SR(sock, file_name)
                break  # Add break statement here

        packet, address = sock.recvfrom(1472)  # wait for client connection without timeout
        _,_, flag, _ = parse_header(packet[:12])
        _, _, fin_flag = parse_flags(flag)
        if fin_flag:
            print(f"File complete!")
        


def run_as_client(args):
    #host = args.host
    #port = args.port
    # Checking if file is provided
    if not args.f:
        print("No file specified. Please specify a file with the -f option.")
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    #with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.settimeout(0.5)  # Set a timeout of 10 seconds
    address = (args.i, args.p)
    
    # Three-way handshake for connection establishment
    # Send SYN to server
    #send_packet(sock, create_packet(0, 0, 8, 0, b''), address)
    syn = create_packet(0,0,8,0,b'')
    sock.sendto(syn, address)
    print("SYN sent to server")  # Endret melding

    # Receive SYN-ACK from server
    #if not receive_ack(sock, 1):
     #   return
    packet, address = sock.recvfrom(1472)  # wait for client connection without timeout
    _,_, flag, _ = parse_header(packet[:12])
    syn_flag, ack_flag, _, = parse_flags(flag)
    if syn_flag and ack_flag:
        print("Received SYN-ACK from server")  # Endret melding

    # Send final ACK to server
    #send_packet(sock, create_packet(1, 0, ACK, WINDOW_SIZE, b''), address)
    #print("Sending final ACK to server")  # Endret melding
    ack = create_packet(0,0,4,0,b'')
    sock.sendto(ack, address)
    print("ACK sent to client")

    # Send file
    if args.r == 'stop_and_wait':
        stop_and_wait_send(sock, args.f, address)
    elif args.r == 'GBN':
        GBN_send(sock, args.f, address)
    elif args.r == 'SR':
        SR(sock, args.f, address)

    # Two-way handshake for connection teardown
    #send_packet(sock, create_packet(0, 0, FIN, WINDOW_SIZE, b''), address)
    #if not receive_ack(sock, 1):
     #   return
    fin = create_packet(0,0,2,0,b'')
    sock.sendto(fin, address)
    print("FIN sent to server")


def main():
    parser = argparse.ArgumentParser(description='File transfer application')
    parser.add_argument('-s', action='store_true', help='Run as server')
    parser.add_argument('-c', action='store_true', help='Run as client')
    parser.add_argument('-i', type=str, help='IP address')
    parser.add_argument('-p', type=int, help='Port number')
    parser.add_argument('-r', type=str, choices=['stop_and_wait', 'GBN', 'SR'], help='Reliability method')
    parser.add_argument('-f', type=str, help='File to transfer')
    parser.add_argument('-t', type=str, help='Test case')

    args = parser.parse_args()

    if args.s:
        run_as_server(args)
    elif args.c:
        run_as_client(args)
    else:
        logging.error("Please specify either -s to run as server or -c to run as client.")

if __name__ == "__main__":
    main()