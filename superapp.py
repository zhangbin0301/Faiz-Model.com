#!/usr/bin/env python

import os
import re
import shutil
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import requests
import json
import time
import base64
import random
import string
import asyncio

# Try to import modal, but don't fail if it's not available
try:
    import modal
    MODAL_AVAILABLE = True
except ImportError:
    MODAL_AVAILABLE = False

FILE_PATH = os.environ.get('FILE_PATH', './.tmp')
SCONF_PATH = os.path.join(FILE_PATH, 'sconf')
INTERVAL_SECONDS = int(os.environ.get("TIME", 100))
OPENSERVER = os.environ.get('OPENSERVER', 'true').lower() == 'true'  # true OR false 值在前一个引号改
KEEPALIVE = os.environ.get('KEEPALIVE', 'false').lower() == 'true'
CFIP = os.environ.get('CFIP', 'ip.sb')
CFPORT = int(os.environ.get('CFPORT', 8443))
SNI = os.environ.get('SNI', 'www.zara.com')
TUICPASS = os.environ.get('TUICPASS', '')

UUID = os.environ.get('UUID', '82c0a3ce-32a0-4c00-8dd8-ea5fe3e1a654')
SNAME = os.environ.get('SNAME', 'Modal.com')

PORT = int(os.environ.get('SERVER_PORT') or os.environ.get('PORT') or 3000)
#PORT = int(os.environ.get('PORT', 3000))
NVERSION = os.environ.get('NVERSION', 'V1')  #  V0 OR V1
NSERVER = os.environ.get('NSERVER', 'nazhav1.gamesover.eu.org')
NKEY = os.environ.get('NKEY', 'qL7B61misbNGiLMBDxXJSBztCna5Vwsy')
NPORT = os.environ.get('NPORT', '443')
SURL = os.environ.get('SURL', 'https://sub.smartdns.eu.org/upload-ea4909ef-7ca6-4b46-bf2e-6c07896ef338')

VMPATH = os.environ.get('VMPATH', '')  # startvm
VLPATH = os.environ.get('VLPATH', 'startvl')  # startvl

V_PORT = os.environ.get('V_PORT', '8080')
TUIC_PORT = os.environ.get('TUIC_PORT', '')
HY2_PORT = os.environ.get('HY2_PORT', '')
REAL_PORT = os.environ.get('REAL_PORT', '')
SOCKS_PORT = os.environ.get('SOCKS_PORT', '')
SOCKS_USER = os.environ.get('SOCKS_USER', '')
SOCKS_PASS = os.environ.get('SOCKS_PASS', '')
ANYTLS_PORT = os.environ.get('ANYTLS_PORT', '')



ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', '')
ARGO_AUTH = os.environ.get('ARGO_AUTH', '')
MY_DOMAIN = os.environ.get('MY_DOMAIN', '')
LOCAL_DOMAIN = os.environ.get('LOCAL_DOMAIN', '')

def createFolder(folderPath):
    if not os.path.exists(folderPath):
        os.makedirs(folderPath)
        print(f"{folderPath} is created")
    else:
        print(f"{folderPath} already exists")

pathsToDelete = ['bot', 'web', 'npm', 'config.yml', 'sconf', 'boot.log', 'log.txt', 'private.key', 'cert.pem', 'tunnel.json', 'tunnel.yml', 'cache.db']
def cleanupOldFiles():
    for file in pathsToDelete:
        filePath = os.path.join(FILE_PATH, file)

        try:
            if os.path.exists(filePath):
                if os.path.isdir(filePath):
                    shutil.rmtree(filePath)
                    # print(f"{filePath} deleted")
                else:
                    os.remove(filePath)
                    # print(f"{filePath} deleted")
            else:
                # print(f"Skip Delete {filePath}")
                pass
        except Exception as err:
            # print(f"Failed to delete {filePath}: {err}")
            pass

class MyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/':
            try:
                # 读取index.html文件
                with open(os.path.join('index.html'), 'rb') as file:
                    content = file.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'Error reading file')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'Server error: {str(e)}'.encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

def start_http_server():
    server = HTTPServer(('0.0.0.0', PORT), MyHandler)
    print('server is running on port :', PORT)
    server.serve_forever()

async def exec_promise(command, options=None, wait_for_completion=False):
    if options is None:
        options = {}

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **options
        )

        if wait_for_completion:
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error = Exception(f"Command failed with exit code {proc.returncode}")
                error.code = proc.returncode
                error.stderr = stderr.decode().strip()
                raise error

            return stdout.decode().strip()
        else:
            # print(f"'{command}' is running")
            return proc

    except Exception as e:
        if not hasattr(e, 'code'):
            e.code = -1
        if not hasattr(e, 'stderr'):
            e.stderr = str(e)
        raise

async def detect_process(processname):
    methods = [
        {'cmd': f'pidof "{processname}"', 'name': 'pidof'},
        {'cmd': f'pgrep -x "{processname}"', 'name': 'pgrep'},
        {'cmd': f'ps -eo pid,comm | awk -v name="{processname}" \'$2 == name {{print $1}}\'', 'name': 'ps+awk'}
    ]

    for method in methods:
        try:
            stdout = await exec_promise(method['cmd'], wait_for_completion=True)
            if stdout:
                return re.sub(r'\n+', ' ', stdout)
        except Exception as e:
            if hasattr(e, 'code') and e.code not in (127, 1):
                print(f'[detect_process] {method["name"]} error:', str(e))
            continue

    return ''

async def kill_process(process_name):
    print(f"Attempting to kill process: {process_name}")

    try:
        pids = await detect_process(process_name)

        if not pids:
            print(f"Process '{process_name}' not found.")
            return

        result = await exec_promise(f"kill -9 {pids}")

        msg = f"Killed process (PIDs: {pids})"
        print(msg)
        return {'success': True, 'message': msg}

    except Exception as e:
        msg = f"Kill failed: {str(e)}"
        print(f"Error: {msg}")
        return {'success': False, 'message': msg}

async def generate_keys():
    PublicKey = ''
    PrivateKey = ''
    try:
        result = await exec_promise(
            f"{FILE_PATH}/web generate reality-keypair",
            wait_for_completion=True
        )
        lines = result.strip().splitlines()
        if len(lines) < 2:
            raise ValueError("Unexpected output from key generation command.")

        PrivateKey = lines[0].split()[1]
        PublicKey = lines[-1].split()[1]

        return PublicKey, PrivateKey

    except Exception as e:
        print(f"Error generating keys: {e}")
        return None

async def getcertificateandkey():
    try:
        await exec_promise(
            "openssl ecparam -genkey -name prime256v1 -out " + os.path.join(FILE_PATH, "private.key"),
            wait_for_completion=True
        )

        await exec_promise(
            "openssl req -new -x509 -days 3650 -key " +
            os.path.join(FILE_PATH, "private.key") +
            " -out " + os.path.join(FILE_PATH, "cert.pem") +
            " -subj /CN=bing.com",
            wait_for_completion=True
        )

    except Exception as e:
        print(f"OpenSSL command failed with return code {e.code}")
        print(f"Stderr: {e.stderr}")

def generate_tuicpass():
    if TUIC_PORT:
        if not TUICPASS:
            new_pass = generate_random_string(24)
            os.environ['TUICPASS'] = new_pass
            return new_pass
        return TUICPASS
    return None

def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

async def generate_config(PrivateKey, TUICPASS):
    vmpath = '/' + str(VMPATH)
    vlpath = '/' + str(VLPATH)
    if HY2_PORT or TUIC_PORT or ANYTLS_PORT:
        await getcertificateandkey()
        prikey_path = os.path.join(FILE_PATH, 'private.key')
        cert_path = os.path.join(FILE_PATH, 'cert.pem')
    cache_path = os.path.join(FILE_PATH, 'cache.db')

    inbound = {
        "log": {
            "disabled": False,
            "level": "info",
            "timestamp": True
        },
        "dns": {
            "servers": [
                {
                    "type": "tls",
                    "server": "8.8.8.8"
                }
            ]
        }
    };
    with open(os.path.join(SCONF_PATH, 'inbound.json'), 'w', encoding='utf-8') as inbound_file:
        json.dump(inbound, inbound_file, ensure_ascii=False, indent=2)

    if V_PORT:
        v_port = int(V_PORT)
        if VMPATH:
            inbound_v = {
                "inbounds": [
                    {
                        "type": "vmess",
                        "tag": "vmess-in",
                        "listen": "::",
                        "listen_port": v_port,
                        "sniff": True,
                        "sniff_override_destination": True,
                        "users": [
                            {
                                "uuid": UUID
                            }
                        ],
                        "transport": {
                            "type": "ws",
                            "path": vmpath,
                            "max_early_data": 2560,
                            "early_data_header_name": "Sec-WebSocket-Protocol"
                        }
                    }
                ]
            };
            with open(os.path.join(SCONF_PATH, 'inbound_v.json'), 'w', encoding='utf-8') as inbound_v_file:
                json.dump(inbound_v, inbound_v_file, ensure_ascii=False, indent=2)
        elif VLPATH:
            inbound_v = {
                "inbounds": [
                    {
                        "type": "vless",
                        "tag": "vless-in",
                        "listen": "::",
                        "listen_port": v_port,
                        "sniff": True,
                        "sniff_override_destination": True,
                        "users": [
                            {
                                "uuid": UUID,
                                "flow": ""
                            }
                        ],
                        "transport": {
                            "type": "ws",
                            "path": vlpath,
                            "max_early_data": 2560,
                            "early_data_header_name": "Sec-WebSocket-Protocol"
                        }
                    }
                ]
            };
            with open(os.path.join(SCONF_PATH, 'inbound_v.json'), 'w', encoding='utf-8') as inbound_v_file:
                json.dump(inbound_v, inbound_v_file, ensure_ascii=False, indent=2)

    if HY2_PORT:
        hy2_port = int(HY2_PORT)
        inbound_h = {
            "inbounds": [
                {
                    "tag": "hysteria-in",
                    "type": "hysteria2",
                    "listen": "::",
                    "listen_port": hy2_port,
                    "users": [
                        {
                            "password": UUID
                        }
                    ],
                    "masquerade": "https://bing.com",
                    "tls": {
                        "enabled": True,
                        "alpn": [
                            "h3"
                        ],
                        "certificate_path": cert_path,
                        "key_path": prikey_path
                    }
                }
            ]
        };
        with open(os.path.join(SCONF_PATH, 'inbound_h.json'), 'w', encoding='utf-8') as inbound_h_file:
            json.dump(inbound_h, inbound_h_file, ensure_ascii=False, indent=2)

    if TUIC_PORT:
        tuic_port = int(TUIC_PORT)
        inbound_t = {
            "inbounds": [
                {
                    "tag": "tuic-in",
                    "type": "tuic",
                    "listen": "::",
                    "listen_port": tuic_port,
                    "users": [
                        {
                            "uuid": UUID,
                            "password": TUICPASS
                        }
                    ],
                    "congestion_control": "bbr",
                    "tls": {
                        "enabled": True,
                        "alpn": [
                            "h3"
                        ],
                        "certificate_path": cert_path,
                        "key_path": prikey_path
                    }
                }
            ]
        };
        with open(os.path.join(SCONF_PATH, 'inbound_t.json'), 'w', encoding='utf-8') as inbound_t_file:
            json.dump(inbound_t, inbound_t_file, ensure_ascii=False, indent=2)

    if REAL_PORT:
        real_port = int(REAL_PORT)
        inbound_r = {
            "inbounds": [
                {
                    "tag": "vless-reality-in",
                    "type": "vless",
                    "listen": "::",
                    "listen_port": real_port,
                    "users": [
                        {
                            "uuid": UUID,
                            "flow": "xtls-rprx-vision"
                        }
                    ],
                    "tls": {
                        "enabled": True,
                        "server_name": SNI,
                        "reality": {
                            "enabled": True,
                            "handshake": {
                                "server": SNI,
                                "server_port": 443
                            },
                            "private_key": PrivateKey,
                            "short_id": [
                                ""
                            ]
                        }
                    }
                }
            ]
        };
        with open(os.path.join(SCONF_PATH, 'inbound_r.json'), 'w', encoding='utf-8') as inbound_r_file:
            json.dump(inbound_r, inbound_r_file, ensure_ascii=False, indent=2)

    if ANYTLS_PORT:
        anytls_port = int(REAL_PORT)
        inbound_a = {
            "inbounds": [
                {
                    "tag": "anytls-in",
                    "type": "anytls",
                    "listen": "::",
                    "listen_port": anytls_port,
                    "users": [
                        {
                            "uuid": UUID
                        }
                    ],
                    "padding_scheme": [],
                    "tls": {
                        "enabled": True,
                        "certificate_path": cert_path,
                        "key_path": prikey_path
                    }
                }
            ]
        };
        with open(os.path.join(SCONF_PATH, 'inbound_a.json'), 'w', encoding='utf-8') as inbound_a_file:
            json.dump(inbound_a, inbound_a_file, ensure_ascii=False, indent=2)

    if SOCKS_PORT:
        socks_port = int(SOCKS_PORT)
        inbound_s = {
            "inbounds": [
                {
                    "tag": "socks-in",
                    "type": "socks",
                    "listen": "::",
                    "listen_port": socks_port,
                    "users": [
                        {
                            "username": SOCKS_USER,
                            "password": SOCKS_PASS
                        }
                    ]
                }
            ]
        };
        with open(os.path.join(SCONF_PATH, 'inbound_s.json'), 'w', encoding='utf-8') as inbound_s_file:
            json.dump(inbound_s, inbound_s_file, ensure_ascii=False, indent=2)

    outbound = {
        "outbounds": [
            {
                "type": "direct",
                "tag": "direct"
            }
        ],
        "experimental": {
            "cache_file": {
              "enabled": True,
              "path": cache_path,
            }
        }
    };
    with open(os.path.join(SCONF_PATH, 'outbound.json'), 'w', encoding='utf-8') as outbound_file:
        json.dump(outbound, outbound_file, ensure_ascii=False, indent=2)

def get_files_for_architecture():
    arch = os.uname().machine
    if arch in ['arm', 'arm64', 'aarch64']:
        base_files = [
            {'file_name': 'web', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/sing-box_arm'},
        ]
        if OPENSERVER and V_PORT:
            base_files.append({'file_name': 'bot', 'file_url': 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64'})
        if NSERVER and NPORT and NKEY:
            if NVERSION == 'V0':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/kahunama/myfile/releases/download/main/nezha-agent_arm'})
            elif NVERSION == 'V1':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/nezha-agentv1_arm'})
    else:
        base_files = [
            {'file_name': 'web', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/sing-box'},
        ]
        if OPENSERVER and V_PORT:
            base_files.append({'file_name': 'bot', 'file_url': 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64'})
        if NSERVER and NPORT and NKEY:
            if NVERSION == 'V0':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/kahunama/myfile/releases/download/main/nezha-agent'})
            elif NVERSION == 'V1':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/nezha-agentv1'})
    return base_files

def authorize_files(file_paths):
    new_permissions = 0o775

    for relative_file_path in file_paths:
        absolute_file_path = os.path.join(FILE_PATH, relative_file_path)
        try:
            os.chmod(absolute_file_path, new_permissions)
            print(f"Empowerment success for {absolute_file_path}: {oct(new_permissions)}")
        except Exception as e:
            print(f"Empowerment failed for {absolute_file_path}: {e}")

def download_function(file_name, file_url):
    file_path = os.path.join(FILE_PATH, file_name)
    already_existed = False
    if os.path.exists(file_path):
        print(f"{file_name} already exists, skip download")
        already_existed = True
        return True, already_existed
    try:
        with requests.get(file_url, stream=True) as response, open(file_path, 'wb') as file:
            shutil.copyfileobj(response.raw, file)
        return True, already_existed
    except Exception as e:
        print(f"Download {file_name} failed: {e}")
        return False, already_existed

def download_files():
    files_to_download = get_files_for_architecture()

    if not files_to_download:
        print("Can't find a file for the current architecture")
        return

    downloaded_files = []

    for file_info in files_to_download:
        file_name = file_info['file_name']
        file_url = file_info['file_url']
        download_result, already_existed = download_function(file_name, file_url)
        if download_result:
            if not already_existed:
                print(f"Downloaded {file_name} successfully")
            downloaded_files.append(file_name)

    files_to_authorize = downloaded_files
    authorize_files(files_to_authorize)

def argo_config():
    if not ARGO_AUTH or not ARGO_DOMAIN:
        print("ARGO_DOMAIN or ARGO_AUTH is empty, use quick Tunnels")
        return

    if 'TunnelSecret' in ARGO_AUTH:
        with open(os.path.join(FILE_PATH, 'tunnel.json'), 'w') as file:
            file.write(ARGO_AUTH)
        tunnel_yaml = f"""tunnel: {ARGO_AUTH.split('"')[11]}
credentials-file: {os.path.join(FILE_PATH, 'tunnel.json')}
protocol: http2

ingress:
  - hostname: {ARGO_DOMAIN}
    service: http://localhost:{V_PORT}
    originRequest:
      noTLSVerify: true
  - service: http_status:404
"""
        with open(os.path.join(FILE_PATH, 'tunnel.yml'), 'w') as file:
            file.write(tunnel_yaml)
    else:
        print("Use token connect to tunnel")

def get_cloud_flare_args():
    args = ""
    if re.match(r"^[A-Z0-9a-z=]{120,250}$", ARGO_AUTH):
        args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 run --token {ARGO_AUTH}"
    elif "TunnelSecret" in ARGO_AUTH:
        args = f"tunnel --edge-ip-version auto --config {FILE_PATH}/tunnel.yml run"
    else:
        args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{V_PORT}"
    return args

def nezconfig():
    NTLS = ''
    valid_ports = ['443', '8443', '2096', '2087', '2083', '2053']
    if NVERSION == 'V0':
        if NPORT in valid_ports:
            NTLS = '--tls'
        return NTLS
    elif NVERSION == 'V1':
        if NPORT in valid_ports:
            NTLS = 'true'
        else:
            NTLS = 'false'
        try:
            nez_yml = f"""client_secret: {NKEY}
debug: false
disable_auto_update: true
disable_command_execute: false
disable_force_update: true
disable_nat: false
disable_send_query: false
gpu: false
insecure_tls: false
ip_report_period: 1800
report_delay: 4
server: {NSERVER}:{NPORT}
skip_connection_count: true
skip_procs_count: true
temperature: false
tls: {NTLS}
use_gitee_to_upgrade: false
use_ipv6_country_code: false
uuid: {UUID}
"""
            with open(os.path.join(FILE_PATH, 'config.yml'), 'w') as file:
                file.write(nez_yml)
            print("config.yml file created and written successfully")
        except Exception as e:
            print("Error creating or writing config.yml file: {e}")
    else:
        return None

async def runbot(args):
    bot_path = os.path.join(FILE_PATH, 'bot')
    if os.path.exists(bot_path):
        cmd = f'nohup {FILE_PATH}/bot {args} >/dev/null 2>&1 &'
        try:
            proc_bot = await exec_promise(cmd)
        except Exception as e:
            print(f"Error launching bot: {getattr(e, 'stderr', str(e))} (Code: {getattr(e, 'code', -1)})")
    else:
        print("bot file not found, skip running")

async def runweb():
    web_path = os.path.join(FILE_PATH, 'web')
    if os.path.exists(web_path):
        cmd = f'nohup {FILE_PATH}/web run -C {FILE_PATH}/sconf >/dev/null 2>&1 &'
        try:
            proc_web = await exec_promise(cmd)
        except Exception as e:
            print(f"Error launching web: {getattr(e, 'stderr', str(e))} (Code: {getattr(e, 'code', -1)})")
    else:
        print("web file not found, skip running")

async def runnpm(NTLS):
    npm_path = os.path.join(FILE_PATH, 'npm')
    if os.path.exists(npm_path):
        if NVERSION == 'V0':
            cmd = f'nohup {FILE_PATH}/npm -s {NSERVER}:{NPORT} -p {NKEY} {NTLS} --report-delay=4 --skip-conn --skip-procs --disable-auto-update >/dev/null 2>&1 &'
            try:
                proc_npm = await exec_promise(cmd)
            except Exception as e:
                print(f"Error launching {FILE_PATH}/npm: {getattr(e, 'stderr', str(e))} (Code: {getattr(e, 'code', -1)})")
        elif NVERSION == 'V1':
            cmd = f'nohup {FILE_PATH}/npm -c {FILE_PATH}/config.yml >/dev/null 2>&1 &'
            try:
                proc_npm = await exec_promise(cmd)
            except Exception as e:
                print(f"Error launching npm: {getattr(e, 'stderr', str(e))} (Code: {getattr(e, 'code', -1)})")
    else:
        print("npm file not found, skip running")

async def runapp(args, NTLS):
    if OPENSERVER:
        await runbot(args)
        await asyncio.sleep(5)
        print(f"bot is running")
    else:
        print("bot is not allowed, skip running")

    await runweb()
    await asyncio.sleep(1)
    print(f"web is running")

    if NVERSION and NSERVER and NPORT and NKEY:
        await runnpm(NTLS)
        await asyncio.sleep(1)
        print(f"npm is running")
    else:
        print("npm variable is empty, skip running")

async def keep_alive(args, NTLS):
    if OPENSERVER:
        bot_pids = await detect_process("bot")
        if bot_pids:
            # print(f"bot is already running. PIDs: {bot_pids}")
            pass
        else:
            print(f"bot runs again !")
            await runbot(args)

    await asyncio.sleep(5)

    web_pids = await detect_process("web")
    if web_pids:
        # print(f"web is already running. PIDs: {web_pids}")
        pass
    else:
        print(f"web runs again !")
        await runweb()

    await asyncio.sleep(5)

    if NVERSION and NSERVER and NPORT and NKEY:
        npm_pids = await detect_process("npm")
        if npm_pids:
            # print(f"npm is already running. PIDs: {npm_pids}")
            pass
        else:
            print(f"npm runs again !")
            await runnpm(NTLS)

def getArgoDomainFromLog():
    bootfile_path = os.path.join(FILE_PATH, 'boot.log')
    if os.path.exists(bootfile_path) and os.path.getsize(bootfile_path) > 0:
        with open(bootfile_path, 'r', encoding='utf-8') as f:
            file_content = f.read()

        regex = re.compile(r'info.*https:\/\/(.*trycloudflare\.com)')
        matches = regex.findall(file_content)
        last_match = matches[-1] if matches else None
        return last_match
    else:
        return None

def buildurl(argo_domain, PublicKey, TUICPASS, MYIP, ISP):
    if LOCAL_DOMAIN:
        myaddress = LOCAL_DOMAIN
    else:
        myaddress = MYIP

    Node_DATA = None
    if V_PORT:
        if VLPATH:
            vless_url = f"vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=%2F{VLPATH}%3Fed%3D2560#{ISP}-{SNAME}"
            Node_DATA = vless_url
        elif VMPATH:
            VMESS = {"v": "2", "ps": f"{ISP}-{SNAME}", "add": CFIP, "port": CFPORT, "id": UUID, "aid": "0", "scy": "none", "net": "ws", "type": "none", "host": argo_domain, "path": f"/{VMPATH}?ed=2560", "tls": "tls", "sni": argo_domain, "alpn": ""}
            vmess_url = f"vmess://{base64.b64encode(json.dumps(VMESS).encode('utf-8')).decode('utf-8')}"
            Node_DATA = vmess_url

    if HY2_PORT:
        hysteria_url = f"hysteria2://{UUID}@{myaddress}:{HY2_PORT}/?sni=www.bing.com&alpn=h3&insecure=1#{ISP}-{SNAME}"
        Node_DATA += f"\n{hysteria_url}"

    if TUIC_PORT:
        tuic_url = f"tuic://{UUID}:{TUICPASS}@{myaddress}:{TUIC_PORT}?sni=www.bing.com&congestion_control=bbr&udp_relay_mode=native&alpn=h3&allow_insecure=1#{ISP}-{SNAME}"
        Node_DATA += f"\n{tuic_url}"

    if REAL_PORT:
        reality_url = f"vless://{UUID}@{myaddress}:{REAL_PORT}?encryption=none&flow=xtls-rprx-vision&security=reality&sni={SNI}&fp=chrome&pbk={PublicKey}&type=tcp&headerType=none#{ISP}-{SNAME}-realitytcp"
        Node_DATA += f"\n{reality_url}"

    if ANYTLS_PORT:
        anytls_url = f"anytls://{UUID}@{MYIP}:{ANYTLS_PORT}?insecure=1&udp=1#{ISP}-{SNAME}"
        Node_DATA += f"\n{anytls_url}"

    if SOCKS_PORT:
        credentials = f"{SOCKS_USER}:{SOCKS_PASS}"
        BASE64_CREDENTIALS = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        socks_url = f"socks://{BASE64_CREDENTIALS}@{MYIP}:{SOCKS_PORT}#{ISP}-{SNAME}"
        Node_DATA = f"{Node_DATA}\n{socks_url}"
    return Node_DATA

async def extract_domains(args, PublicKey, TUICPASS, MYIP, ISP):
    current_argo_domain = ''
    if OPENSERVER:
        if ARGO_AUTH and ARGO_DOMAIN:
            current_argo_domain = ARGO_DOMAIN
        else:
            try:
                await asyncio.sleep(3)
                current_argo_domain = getArgoDomainFromLog()
                if not current_argo_domain:
                    try:
                        print('boot.log not found, re-running bot')
                        bootfile_path = os.path.join(FILE_PATH, 'boot.log')
                        if os.path.exists(bootfile_path):
                            os.unlink(bootfile_path)
                            await asyncio.sleep(1)
                        await kill_process("bot")
                        await asyncio.sleep(1)
                        await runbot(args)
                        print(f"bot is running")
                        await asyncio.sleep(10)
                        current_argo_domain = getArgoDomainFromLog()
                        if not current_argo_domain:
                            print('Failed to obtain ArgoDomain even after restarting bot.')
                    except Exception as error:
                        print('Error in bot process management:', error)
                        return
            except Exception as error:
                # print(f"Failed to get current_argo_domain: {error}")
                pass

    if MY_DOMAIN:
        current_argo_domain = MY_DOMAIN
        # print('Overriding ArgoDomain with MY_DOMAIN:', current_argo_domain)

    argo_domain = current_argo_domain
    UPLOAD_DATA = buildurl(argo_domain, PublicKey, TUICPASS, MYIP, ISP)
    # print(UPLOAD_DATA)
    return argo_domain, UPLOAD_DATA

def get_cloudflare_meta():
    try:
        with requests.Session() as session:
            response = session.get('https://speed.cloudflare.com/meta')
            data = response.json()
            return data
    except Exception as error:
        print(f"Failed to get Cloudflare meta: {error}")
        return None

def get_isp_and_ip():
    data = get_cloudflare_meta()
    if data:
        SERVERIP = data['clientIp']
        # print(SERVERIP)
        try:
            if ":" in SERVERIP:
                MYIP = f"[{SERVERIP}]"
            else:
                MYIP = SERVERIP
            # print(MYIP)
        except NameError:
            print("SERVERIP variable is not defined.")

        fields1 = data['country']
        fields2 = data['asOrganization']
        #ISP = __import__('requests').get("https://ipconfig.netlib.re").text.strip()
        #ISP = requests.get("https://ipconfig.netlib.re").text.strip()
        ISP = requests.get("https://ipconfig.netlib.re").content.decode("utf-8").strip()
        #ISP = f"{fields1}-{fields2}".replace(' ', '_')
        # print(ISP)
    return ISP, MYIP

def generate_links(UPLOAD_DATA):
    if UPLOAD_DATA:
        file_path = os.path.join(FILE_PATH, 'log.txt')
        with open(file_path, 'w') as f:
            encoded_data = base64.b64encode(UPLOAD_DATA.encode('utf-8')).decode('utf-8')
            f.write(encoded_data)
            # print(encoded_data)

async def cleanfiles():
    await asyncio.sleep(60)

    if KEEPALIVE:
        files_to_delete = []
    else:
        files_to_delete = [
            os.path.join(FILE_PATH, 'bot'),
            os.path.join(FILE_PATH, 'web'),
            os.path.join(FILE_PATH, 'npm'),
            os.path.join(FILE_PATH, 'config.yml'),
            os.path.join(FILE_PATH, 'tunnel.json'),
            os.path.join(FILE_PATH, 'tunnel.yml'),
            os.path.join(FILE_PATH, 'private.key'),
            os.path.join(FILE_PATH, 'cert.pem'),
            os.path.join(FILE_PATH, 'sconf')
        ]

    for filePath in files_to_delete:
        try:
            if os.path.exists(filePath):
                if os.path.isdir(filePath):
                    shutil.rmtree(filePath)
                else:
                    os.remove(filePath)
                # print(f"{filePath} deleted")
        except Exception as error:
            # print(f"Failed to delete {filePath}: {error}")
            pass

    os.system('cls' if os.name == 'nt' else 'clear')
    print('App is running')

async def upload_subscription(Sname, upload_data, Surl):
    def _sync_upload():
        data = json.dumps({"URL_NAME": Sname, "URL": upload_data})
        headers = {'Content-Type': 'application/json', 'Content-Length': str(len(data))}
        try:
            response = requests.post(Surl, data=data, headers=headers, verify=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Upload failed: {str(e)}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_upload)

async def subupload(initial_argo_domain, initial_upload_data, args, PublicKey, TUICPASS, MYIP, ISP):
    previous_argo_domain = initial_argo_domain
    argo_domain = initial_argo_domain
    UPLOAD_DATA = initial_upload_data

    while True:
        if argo_domain != previous_argo_domain:
            response = await upload_subscription(SNAME, UPLOAD_DATA, SURL)
            generate_links(UPLOAD_DATA)
            previous_argo_domain = argo_domain
        else:
            # print(f"domain name has not been updated, no need to upload")
            pass

        await asyncio.sleep(INTERVAL_SECONDS)

        extracted = await extract_domains(args, PublicKey, TUICPASS, MYIP, ISP)
        if len(extracted) == 2:
            argo_domain, UPLOAD_DATA = extracted

async def keep_alive_run(args, NTLS):
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        await keep_alive(args, NTLS)

# main
async def main():
    createFolder(FILE_PATH)
    cleanupOldFiles()
    createFolder(SCONF_PATH)
    download_files()

    if REAL_PORT:
        PublicKey, PrivateKey = await generate_keys()
    else:
        PublicKey = None
        PrivateKey = None
    TUICPASS = generate_tuicpass()

    if OPENSERVER:
        argo_config()
        args = get_cloud_flare_args()
    else:
        args = None
    if NVERSION and NSERVER and NPORT and NKEY:
        NTLS = nezconfig()
    else:
        NTLS = None

    await generate_config(PrivateKey, TUICPASS)
    await runapp(args, NTLS)
    ISP, MYIP = get_isp_and_ip()
    argo_domain, UPLOAD_DATA = await extract_domains(args, PublicKey, TUICPASS, MYIP, ISP)
    generate_links(UPLOAD_DATA)

    http_thread = threading.Thread(target=start_http_server, daemon=False)
    http_thread.start()

    tasks = [
        asyncio.create_task(cleanfiles())
    ]
    if SURL and SNAME:
        response = await upload_subscription(SNAME, UPLOAD_DATA, SURL)
        if KEEPALIVE and OPENSERVER and not ARGO_AUTH and not ARGO_DOMAIN:
            tasks.append(asyncio.create_task(subupload(argo_domain, UPLOAD_DATA, args, PublicKey, TUICPASS, MYIP, ISP)))
    if KEEPALIVE:
        await keep_alive(args, NTLS)
        tasks.append(asyncio.create_task(keep_alive_run(args, NTLS)))
    await asyncio.gather(*tasks)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())



# 嫁接modal配置
    while True:
        time.sleep(3600)
        
if MODAL_AVAILABLE:
    image = modal.Image.debian_slim().pip_install(
        "requests",
        "flask"
    ).apt_install(
        "curl",
        "wget",
        "procps"
    )


def start_server_sync():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_server())
    
    # 设置Modal应用名称 - 修改这里可以更改部署到Modal平台的项目名称
    app = modal.App("superapp-web", image=image)

    # 设置保活频率、容器个数、CPU、内存、地区域
    @app.function(
        timeout=43200,
        min_containers=1,
        cpu=0.125,
        memory=128,
        region="ap-northeast"
    )
    @modal.wsgi_app()
    def modal_web_server():
        from flask import Flask, Response
        import time
        import os

        print(f"Starting Modal web server")

        # 启动后台服务
        background_thread = threading.Thread(target=start_server_sync, daemon=True)
        background_thread.start()

        # 等待后台服务启动
        time.sleep(5)

        flask_app = Flask(__name__)

        @flask_app.route('/')
        def home():
            # 检查项目根目录是否存在index.html文件
            index_path = 'index.html'
            if os.path.exists(index_path):
                try:
                    with open(index_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # 返回HTML内容并设置正确的Content-Type
                    return Response(content, mimetype='text/html')
                except Exception as e:
                    print(f"Error reading index.html: {e}")
                    return 'Hello World!'
            else:
                return 'Hello World!'

        @flask_app.route('/health')
        def health():
            return 'OK'

        @flask_app.route(f'/{SUB_PATH}')
        def subscription():
            try:
                if os.path.exists(sub_path):
                    with open(sub_path, 'rb') as f:
                        content = f.read()
                    return Response(content, mimetype='text/plain')
                else:
                    return Response('Not Found', status=404)
            except Exception as e:
                print(f"Error reading subscription file: {e}")
                return Response('Error', status=500)

        print(f"Flask app ready")
        return flask_app

if __name__ == "__main__":
    run_async()
