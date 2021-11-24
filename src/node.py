import socket, sys, threading, fcntl, struct, time, uvicorn, requests, math
from time import sleep
from fastapi import FastAPI, Request

# ---------- CONFIGURABLE CONSTANTS ----------
INTERFACE_NAME = b'eth1'
BROADCAST_PORT = 37023
BROADCAST_IP = '10.0.1.255'
HTTP_PORT = 8000
NEW_CLIENT_TIMEOUT = 60
NODE_DISCONNECT_TIMEOUT = 30

# ---------- CONSTANTS ----------
LEADER_HEARTBEAT_MSG = b'leader_heartbeat'
SHOUT_MSG = b'shout'
REGISTER_ENDPOINT = '/register'
INIT_STATE = 'INIT'
LEADER_STATE = 'LEADER'
FOLLOWER_STATE = 'FOLLOWER'
NO_COLOR = 'GREY'
GREEN_COLOR = 'GREEN'
RED_COLOR = 'RED'
HEALTH_FILE = 'health.log'

# ---------- GLOBALS ----------
state = INIT_STATE
node_id = 'unknown'
color = NO_COLOR

# ---------- HELPERS ----------
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', INTERFACE_NAME[:15]))[20:24])

def get_timestamp():
    return int(time.time())

def wait_for_interface():
    global node_id
    success = False
    while success == False:
        try:
            node_id = get_ip_address(); success = True
        except:
            sleep(1)

def log(a):
    print('[' + node_id + '] <' + state + '> ' + a); sys.stdout.flush()

def log_health():
    with open(HEALTH_FILE, 'w+') as f:
        f.write(str(get_timestamp()))

def set_udp_sock():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    return s

# ---------- LEADER STATE ----------
fastapi_app = FastAPI()
discovered_clients = {}

def next_color(client_ip):
    node_count = len(list(discovered_clients.keys()))
    target_green_count = math.ceil(node_count / 3.0)
    current_green_count = [i[0] for i in list(discovered_clients.values())].count(GREEN_COLOR)
    if discovered_clients[client_ip][0] == GREEN_COLOR:
        return GREEN_COLOR if current_green_count <= target_green_count else RED_COLOR
    return GREEN_COLOR if current_green_count < target_green_count else RED_COLOR

def leader_tick(server):
    global discovered_clients
    log_health()
    server.sendto(LEADER_HEARTBEAT_MSG, (BROADCAST_IP, BROADCAST_PORT))
    for client_ip in list(discovered_clients.keys()):
        if client_ip != get_ip_address() and get_timestamp() - discovered_clients[client_ip][1] > NODE_DISCONNECT_TIMEOUT:
            log("NODE " + client_ip + " disconnected!")
            discovered_clients.pop(client_ip, None)

def leader_init_timestamps():
    for client_ip in list(discovered_clients.keys()):
        if client_ip == get_ip_address():
            continue
        discovered_clients[client_ip] = (NO_COLOR, get_timestamp())

def leader_stage__server():
    # wait for http server and color itself
    http_ready = False
    while not http_ready:
        try:
            r = requests.get(url = 'http://' + get_ip_address() + ':' + str(HTTP_PORT) + REGISTER_ENDPOINT); http_ready = True
            log('My color is ' + r.json())
        except Exception as e:
            sleep(1)
    # run leader tick every 2 seconds
    leader_init_timestamps()
    server = set_udp_sock()
    server.bind((get_ip_address(), 0))
    while True:
        leader_tick(server)
        sleep(2)

@fastapi_app.get(REGISTER_ENDPOINT)
def register(req: Request):
    global discovered_clients
    if req.client.host not in discovered_clients:
        discovered_clients[req.client.host] = (NO_COLOR, get_timestamp())
    color = next_color(req.client.host); discovered_clients[req.client.host] = (color, get_timestamp())
    return color

def leader_stage():
    server_thread = threading.Thread(target=leader_stage__server); server_thread.start()
    uvicorn.run(fastapi_app, host=get_ip_address(), port=HTTP_PORT)

# ---------- FOLLOWER STATE ----------
leader_ip = ''

def follower_tick():
    log_health()
    try:
        r = requests.get(url = 'http://' + leader_ip  + ':' + str(HTTP_PORT) + REGISTER_ENDPOINT, timeout=10)
        log('My color is ' + r.json())
        return False
    except Exception as e:
        return True

def follower_stage():
    while True:
        if follower_tick():
            break
        sleep(5)

# ---------- INIT STATE ----------
halt_server = False
last_client_discovered = 0

def am_i_leader():
    clients = list(discovered_clients.keys()); clients.sort()
    return clients[-1] == get_ip_address()

def init_stage__server():
    # shout every 2 seconds
    server = set_udp_sock(); server.bind((get_ip_address(), 0))
    while True:
        if halt_server:
            break
        server.sendto(SHOUT_MSG, (BROADCAST_IP, BROADCAST_PORT))
        sleep(2)

def init_stage__client():
    global halt_server
    global discovered_clients
    global last_client_discovered
    global state
    global leader_ip
    client = set_udp_sock(); client.bind((BROADCAST_IP, BROADCAST_PORT))
    client.settimeout(5.0)
    while True:
        try:
            data, (ip, port) = client.recvfrom(1024)
            if data == SHOUT_MSG:
                if ip not in discovered_clients:
                    log('adding new node ' + ip)
                    discovered_clients[ip] = (NO_COLOR, get_timestamp())
                    last_client_discovered = get_timestamp()
                elif (last_client_discovered != 0 and
                        get_timestamp() - last_client_discovered > NEW_CLIENT_TIMEOUT and am_i_leader()):
                    state = LEADER_STATE; halt_server = True
                    break
            if data == LEADER_HEARTBEAT_MSG:
                log('received leader heartbeat')
                state = FOLLOWER_STATE; leader_ip = ip; halt_server = True
                break
        except Exception as e:
            pass

def init_stage():
    server_thread = threading.Thread(target=init_stage__server)
    client_thread = threading.Thread(target=init_stage__client)
    server_thread.start(); client_thread.start()
    server_thread.join(); client_thread.join()
    log('changing state to ' + state)
    if state == LEADER_STATE:
        leader_stage()
    else:
        follower_stage()

# ---------- MAIN ----------

def init_globals():
    global state
    global discovered_clients
    global leader_ip
    global halt_server
    global last_client_discovered
    global color
    state = INIT_STATE
    discovered_clients = {}
    leader_ip = ''
    halt_server = False
    last_client_discovered = 0
    color = NO_COLOR

def main():
    global state
    wait_for_interface()
    while True:
        init_globals()
        init_stage()

if __name__ == "__main__":
    main()