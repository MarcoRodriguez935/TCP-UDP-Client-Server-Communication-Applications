# UDP Client-Server Application
# Project Members: Marco Rodriguez and Derek Castro
# Sample commands for each node:
# server -t 1.txt -i 20
# server -t 2.txt -i 20
# server -t 3.txt -i 20
# server -t 4.txt -i 20

import socket
import os
import threading
import time
import ipaddress
import json

num_nodes = 0
num_neighbors = 0

# Dictionary to hold each nodes' IP and Port
nodes = {
    1: {"ip": "", "port": 0},
    2: {"ip": "", "port": 0},
    3: {"ip": "", "port": 0},
    4: {"ip": "", "port": 0}
}

# Dictionary to hold each nodes' tables
tables = {
    1: [],
    2: [],
    3: [],
    4: []
}

my_id = 0
my_ip = ""
my_port = 0

top_file = ""
update_interval = 0

packets_received = 0


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    myip = s.getsockname()[0]
    s.close()
    return myip


device_ip = get_ip()


# If file is valid
def file_exists(file):
    proj_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(proj_dir, file)
    return os.path.isfile(file_path)


# Gets this node's IP address and Port number from node tables
def get_info(my_id):
    global my_ip, my_port
    my_ip = nodes[my_id]["ip"]
    my_port = nodes[my_id]["port"]


# Reads the entered file and obtains data
def parse_file(top_file):
    global num_nodes
    global num_neighbors

    try:
        with open(top_file, 'r') as file:
            for line_num, line in enumerate(file, 1):
                line_list = line.split()
                match line_num:
                    case 1:
                        num_nodes = int(line_list[0])
                    case 2:
                        num_neighbors = int(line_list[0])
                    case 3 | 4 | 5 | 6:
                        neighbor_id = int(line_list[0])
                        nodes[neighbor_id]["ip"] = line_list[1]
                        nodes[neighbor_id]["port"] = int(line_list[2])
                    case _:
                        # Topology lines defining neighbor + cost
                        dest_id = int(line_list[1])
                        cost = float(line_list[2])
                        # initially next hop is same as dest if direct neighbor
                        tables[my_id].append([dest_id, cost, dest_id])
    except FileNotFoundError:
        print("The specified file does not exist")
    except Exception as e:
        print(str(e))


# Checks if IP is valid
def check_ip(ip_add):
    try:
        ipaddress.ip_address(ip_add)
        return True
    except ValueError:
        return False


# DV Update Logic
def update_dv(my_id, neighbor_id, neighbor_table):
    updated = False
    cost_to_neighbor = None
    for dest, cost, _ in tables[my_id]:
        if dest == neighbor_id:
            cost_to_neighbor = float(cost)
            break
    if cost_to_neighbor is None or cost_to_neighbor == float('inf'):
        return False

    for dest, neighbor_cost, _ in neighbor_table:
        neighbor_cost = float(neighbor_cost)
        if dest == my_id:
            continue
        new_cost = cost_to_neighbor + neighbor_cost
        found = False
        for i, (d, my_cost, nh) in enumerate(tables[my_id]):
            if d == dest:
                found = True
                if new_cost < float(my_cost):
                    tables[my_id][i][1] = new_cost
                    tables[my_id][i][2] = neighbor_id
                    updated = True
                break
        if not found:
            tables[my_id].append([dest, new_cost, neighbor_id])
            updated = True
    return updated


# Listens to incoming updates from other nodes
def listener(sock):
    global packets_received
    while True:
        try:
            data, address = sock.recvfrom(1024)
            message = data.decode()
            try:
                msg_obj = json.loads(message)

                # Update on receiving end
                if msg_obj.get("type") == "update":
                    s1 = msg_obj["server1"]
                    s2 = msg_obj["server2"]
                    new_cost = msg_obj["new_cost"]

                    if my_id in (s1, s2):
                        if my_id == s1:
                            neighbor_id = s2
                        else:
                            neighbor_id = s1

                        updated = False

                        for i, (n_id, cost, next_hop) in enumerate(tables[my_id]):
                            if n_id == neighbor_id:
                                tables[my_id][i][1] = new_cost
                                updated = True
                                print(f"Updated link cost between {s1} and {s2} -> {new_cost}")
                                break
                        if not updated:
                            tables[my_id].append([neighbor_id, new_cost, neighbor_id])
                            print(f"New Link between {s1} and {s2} -> {new_cost}")
                    continue

                if msg_obj.get("type") == "disable":
                    s1 = msg_obj["server1"]
                    s2 = msg_obj["server2"]

                    if my_id == s1 or my_id == s2:
                        other = s2 if my_id == s1 else s1

                        for i, (nid, cost, next_hop) in enumerate(tables[my_id]):
                            if nid == other:
                                tables[my_id][i][1] = float('inf')
                                print(f"[DISABLE] Link between {s1} and {s2} disabled -> cost INF")

                        send_update(sock, my_id)
                    continue

                # Handle server crash
                if msg_obj.get("type") == "crash":
                    server_id = msg_obj["server_id"]
                    if server_id == my_id:
                        continue

                    for i, (n_id, cost, next_hop) in enumerate(tables[my_id]):
                        if n_id == server_id:
                            tables[my_id][i][1] = float("inf")
                            print(f"[CRASH] Updated link cost between {my_id} and {server_id} -> inf")
                            break

                    send_update(sock, my_id)
                    continue

                # DV Update
                sender_id = msg_obj["sender"]
                neighbor_table = msg_obj["table"]

                print(f"\nReceived a message from server {sender_id}")
                packets_received += 1

                # Call update_dv() to merge tables
                updated = update_dv(my_id, sender_id, neighbor_table)

                if updated:
                    print("> Routing table updated.")
                else:
                    print("> No changes in routing table.")
            except json.JSONDecodeError:
                print(f"\nReceived raw message: {message}")

            print("> ", end="", flush=True)

        except socket.timeout:
            continue
        except OSError:
            break


# Sends the node's current table to other nodes periodically
def send_periodic_update(sock, my_id, update_interval):
    while True:
        msg = json.dumps({"sender": my_id, "table": tables[my_id]})
        for neighbor_id, cost, _ in tables[my_id]:
            if neighbor_id != my_id and cost != float("inf"):
                sock.sendto(msg.encode(), (nodes[neighbor_id]["ip"], nodes[neighbor_id]["port"]))
        time.sleep(update_interval)


# Immediately sends the node's table to other nodes (step)
def send_update(sock, my_id):
    msg = json.dumps({"sender": my_id, "table": tables[my_id]})
    for neighbor_id, cost, _ in tables[my_id]:
        if neighbor_id != my_id and cost != float("inf"):
            sock.sendto(msg.encode(), (nodes[neighbor_id]["ip"], nodes[neighbor_id]["port"]))


# Sends a crash message to all other nodes
def crash(sock, my_id):
    crash_msg = json.dumps({
        "type": "crash",
        "server_id": my_id,
    })
    for neighbor_id, cost, _ in tables[my_id]:
        if neighbor_id != my_id and cost != float("inf"):
            sock.sendto(crash_msg.encode(), (nodes[neighbor_id]["ip"], nodes[neighbor_id]["port"]))
            print(f"Sent crash update to Node {neighbor_id}")


def main():
    global top_file, update_interval, my_id, tables, nodes, packets_received

    print("Please enter a topology file and routing update interval.\n")
    print(f"This device's IP Address is: {device_ip}\n")
    print("server -t <txt file> -i <interval in seconds>\n")

    info_established = False

    while not info_established:
        try:
            command = str(input("> "))
            command_list = command.split()

            if command_list[0] != 'server' or command_list[1] != '-t' or command_list[3] != '-i':
                print("Invalid command format. Use: server -t <txt file> -i <interval in seconds>")
            elif not file_exists(command_list[2]):
                print("File not found.")
            elif int(command_list[4]) < 0:
                print("Interval must be positive.")
            else:
                top_file = command_list[2]
                update_interval = int(command_list[4])
                info_established = True
        except (IndexError, ValueError):
            print("Invalid input format. Try again.")

    my_id = int(top_file[0])

    parse_file(top_file)
    get_info(my_id)

    if not check_ip(my_ip):
        print("Invalid IP.")
        return

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((my_ip, my_port))
        sock.settimeout(5)

        print(f"\nStarted node {my_id} at {my_ip}:{my_port}")
        print(f"Initial DV Table: {tables[my_id]}\n")

        listener_thread = threading.Thread(target=listener, args=(sock,), daemon=True)
        listener_thread.start()

        sender_thread = threading.Thread(target=send_periodic_update, args=(sock, my_id, update_interval), daemon=True)
        sender_thread.start()

        while True:
            command = input("> ")
            if not command:
                continue
            try:
                match command:
                    case m if "help" in command:
                        print("Commands:\n"
                              " help\n update <ID1> <ID2> <cost>\n step\n packets\n display\n disable <ID>\n crash\n")
                    case m if "send" in command: # Send a message to node (for testing)
                        command_list = command.split()
                        target_id = int(command_list[1])
                        msg = " ".join(command_list[2:])
                        sock.sendto(msg.encode(), (nodes[target_id]["ip"], nodes[target_id]["port"]))
                        print(f"Sent message to node {target_id}: {msg}")
                    case m if "update" in command:
                        command_list = command.split()
                        server1_id = int(command_list[1])
                        server2_id = int(command_list[2])
                        new_cost = float(command_list[3])
                        if server1_id != my_id:
                            print("\"update\" can only update links for this node.")
                            continue
                        for i, (nid, cost, nh) in enumerate(tables[my_id]):
                            if nid == server2_id:
                                tables[my_id][i][1] = new_cost
                                print(f"Updated link cost between {server1_id} and {server2_id} -> {new_cost}")
                                break
                        else:
                            tables[my_id].append([server2_id, new_cost, server2_id])
                            print(f"New link between {server1_id} and {server2_id} -> {new_cost}")

                        update_msg = json.dumps({
                            "type": "update",
                            "server1": server1_id,
                            "server2": server2_id,
                            "new_cost": new_cost
                        })
                        sock.sendto(update_msg.encode(), (nodes[server2_id]["ip"], nodes[server2_id]["port"]))
                    case m if "step" in command: # Immediately send out table updates
                        send_update(sock, my_id)
                        print("Step success.")
                    case m if "packets" in command: # Displays number of packets received since last invocation
                        print("Packets success.")
                        print(f"Packets received since last check: {packets_received}")
                        packets_received = 0
                    case m if "display" in command: # Displays this node's current table
                        print("Display success.")
                        print("Dest\tCost\tNext Hop")
                        for dest, cost, nh in sorted(tables[my_id], key=lambda x: x[0]):
                            c_str = str(cost) if cost != float('inf') else "inf"
                            print(f"{dest}\t{c_str}\t{nh}")
                    case m if "disable" in command: # Disables a link between this node and another node (sets to inf)
                        command_list = command.split()
                        target = int(command_list[1])

                        link_exists = False

                        for i, (nid, cost, nh) in enumerate(tables[my_id]):
                            if nid == target:
                                tables[my_id][i][1] = float('inf')
                                link_exists = True
                                print(f"Disabled link to Node {target} successful.")
                                break

                        if not link_exists:
                            print(f"Node {target} is not a direct neighbor.")
                            continue

                        disable_msg = json.dumps({
                            "type":"disable",
                            "server1":my_id,
                            "server2":target
                        })

                        sock.sendto(disable_msg.encode(), (nodes[target]["ip"], nodes[target]["port"]))

                        for nid, cost, nh in tables[my_id]:
                            if nid != my_id and nid != target:
                                sock.sendto(disable_msg.encode(), (nodes[nid]["ip"], nodes[nid]["port"]))
                    case m if "crash" in command: # Sends crash notification to other nodes before exiting
                        print(f"Node {my_id} crashing. Closing all connections.")
                        crash(sock, my_id)
                        time.sleep(5)
                        sock.close()
                        os._exit(0)
                    case _:
                        print("Unknown command. Type 'help' for a list of commands.")
            except Exception as e:
                print(str(e))

    except Exception as e:
        print(str(e))


if __name__ == "__main__":
    main()
