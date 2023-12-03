#!/usr/bin/env python3

import argparse
import os
import socket
import sys

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
            sock.connect((args.host, int(args.port)))

            with open(args.file, "rb") as f:
                data = f.read(50000)
                while data:
                    total_sent = 0
                    while total_sent < len(data):
                        sent = sock.send(data[total_sent:])
                        total_sent += sent
                        data = f.read(50000)

             # Gracefully terminate the connection
            sock.sendFinPacket()
            sock.expectFinAck()

            # Wait for incoming FIN packets
            start_time = time.time()
            while time.time() - start_time < 2:
                pkt = sock._recv()
                if pkt and pkt.isFin:
                    # Respond to each incoming FIN with an ACK packet
                    sock.sendAckPacket()

            # Close connection
            sock.close()
    except RuntimeError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)

if __name__ == '__main__':
    start()