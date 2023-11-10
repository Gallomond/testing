import sys
import argparse
import socket
import signal
import os

import confundo

# for testing, replace socket.socket with confundo.Socket()
# or just use the reference server (check Piazza or consult the instructor)

# the server can only work in a single threaded mode, one client at a time (no parallel,
# neither concurrent nor threaded---simplifications in the socket implementation)

# Other than that, standard socket interface should work

def handle_client(client_sock, file_path):
    try:
        with open(file_path, 'rb') as file:
            data = file.read(50000)
            while data:
                client_sock.send_data_packet(data)
                data = file.read(50000)

        # Gracefully terminate the connection
        client_sock.receive_fin_packet()
        client_sock.send_ack_packet()

    except FileNotFoundError:
        sys.stderr.write(f"ERROR: File not found: {file_path}\n")
    except RuntimeError as e:
        sys.stderr.write(f"ERROR: {e}\n")

    finally:
        # Close the client socket
        client_sock.close()

def start():
    parser = argparse.ArgumentParser(description="Confundo Server")
    parser.add_argument("port", help="Port number to bind the server to", type=int)
    parser.add_argument("file", help="Path to the file to send to clients")
    args = parser.parse_args()

    try:
        # Create a server socket
        server_sock = confundo.Socket()
        server_sock.bind(('localhost', args.port))
        server_sock.listen(1)  # Allow only one connection in the queue

        while True:
            # Accept a client connection
            client_sock, client_addr = server_sock.accept()

            # Handle the client in a separate function
            handle_client(client_sock, args.file)

    except KeyboardInterrupt:
        print("Server terminated by user.")
    finally:
        # Close the server socket
        server_sock.close()

if __name__ == '__main__':
    start()