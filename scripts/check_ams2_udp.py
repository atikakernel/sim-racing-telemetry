
import socket

UDP_IP = "0.0.0.0"
UDP_PORT = 5606

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening for AMS2 on {UDP_IP}:{UDP_PORT}...")

while True:
    data, addr = sock.recvfrom(2048)
    print(f"Received message: {len(data)} bytes from {addr}")
