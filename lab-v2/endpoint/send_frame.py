#!/usr/bin/env python3
"""Send one ARP broadcast frame from an isolated lab dataplane interface."""
import argparse
import socket
import struct

def build_frame(mac: str, sender_ip: str, target_ip: str = "198.18.0.254") -> bytes:
    src = bytes.fromhex(mac.replace(":", ""))
    if len(src) != 6 or src[0] & 1:
        raise ValueError("Source MAC must be a valid unicast 6-byte address")
    ethernet = b"\xff" * 6 + src + struct.pack("!H", 0x0806)
    arp_header = struct.pack("!HHBBH", 1, 0x0800, 6, 4, 1)
    arp_body = src + socket.inet_aton(sender_ip) + b"\x00" * 6 + socket.inet_aton(target_ip)
    return (ethernet + arp_header + arp_body).ljust(60, b"\x00")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface", default="eth1")
    parser.add_argument("--mac", required=True)
    parser.add_argument("--sender-ip", required=True)
    args = parser.parse_args()
    if args.interface != "eth1":
        parser.error("Only isolated lab dataplane interface eth1 is permitted")
    frame = build_frame(args.mac, args.sender_ip)
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003)) as sock:
        sock.bind((args.interface, 0))
        sock.send(frame)

if __name__ == "__main__":
    main()
