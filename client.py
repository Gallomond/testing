#!/usr/bin/env python3

import argparse
import os
import socket
import sys
import time

import confundo

parser = argparse.ArgumentParser("Parser")
parser.add_argument("host", help="Set Hostname")
parser.add_argument("port", help="Set Port Number", type=int)
parser.add_argument("file", help="Set File Directory")
args = parser.parse_args()

def start():
    try:
        with confundo.Socket() as sock:
            sock.settimeout(10)
            sock.connect((args.host, args.port))

            # Perform 3-way handshake
            sock.sendSynPacket()
            sock.expectSynAck()
            sock.sendAckPacket()

            with open(args.file, "rb") as f:
                chunk_size = 50000
                data = f.read(chunk_size)
                while data:
                    sock.sendDataPacket(data)
                    data = f.read(chunk_size)

            # Gracefully terminate the connection
            sock.sendFinPacket()
            sock.expectAckPacket()

            # Wait for incoming FIN packets
            start_time = time.time()
            while time.time() - start_time < 2:
                pkt = sock._recv()
                if pkt and pkt.isFin:
                    # Respond to each incoming FIN with an ACK packet
                    sock.sendAckPacket()

            # Close connection
            sock.close()

    except FileNotFoundError:
        sys.stderr.write(f"ERROR: File not found: {args.file}\n")
        sys.exit(1)
    except RuntimeError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)

if __name__ == '__main__':
    start()