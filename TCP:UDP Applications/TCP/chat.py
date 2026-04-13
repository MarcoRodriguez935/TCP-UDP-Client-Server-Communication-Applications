# TCP Client-Server Application
# Project Members: Marco Rodriguez and Derek Castro
# This project presents a TCP chat app that allows back and forth
# communication between users through the use of sockets


import sys
import socket
import threading
import errno

# List that will hold established connections via tuples (sockets, ip addresses, port numbers)
conn_list = []

host_initialized = threading.Event()  # to ensure host starts before client

try:
    port = int(sys.argv[1])
except (IndexError, ValueError):  # close on absent port argument or non-integer port
    print("Invalid Port Number.")
    sys.exit("Failed to start connection. Exiting.")


# Get Device IP
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    myip = s.getsockname()[0]
    s.close()
    return myip


myip = get_ip()


# Signal when client-side exits
client_shutdown = threading.Event()


# Handles connections and incoming messages
def handle_connection(connection_socket, address):
    try:
        # After the connect feature is successfully done, the sender sends their ip and port
        try:
            peer_info = connection_socket.recv(1024).decode()
            peer_info_values = peer_info.split()
            other_ip = peer_info_values[0]
            other_port = int(peer_info_values[1])
        except (IndexError, ValueError):
            print("Invalid User Information. Closing connection")
            connection_socket.close()
            return

        conn_list.append((connection_socket, other_ip, other_port))

        print("\nConnection with", address, "has been added to list.\n")
        print("> ", end="", flush=True)

        # While client is still running
        while not client_shutdown.is_set():
            # receive data in bytes
            data = connection_socket.recv(1024)

            if not data:
                print("\n\nConnection with (" + other_ip + ", " + str(other_port) + ") has been terminated. \n")
                print("> ", end="", flush=True)
                break

            message = data.decode()

            if message == "close":
                print("\n\nConnection with (" + other_ip + ", " + str(other_port) + ") has been terminated. \n")
                print("> ", end="", flush=True)
                break
            else:
                print()
                print("\nMessage received from (" + other_ip + ", " + str(other_port) + ")")
                print("Message: \"" + str(message) + "\"\n")
                print("> ", end="", flush=True)
    except OSError:
        pass
    finally:
        delete_conn(connection_socket)
        connection_socket.close()


# Deletes a connection from the list based on socket
def delete_conn(socket):
    for i, (s, ip, p) in enumerate(conn_list):
        if s == socket:
            del conn_list[i]
            break


# Handles client-side operations
def client_side():
    print("\nType \"help\" to view available commands.\n")
    try:
        # keep getting user input
        while not client_shutdown.is_set():
            userinput = input("> ")

            match userinput:
                case "help":
                    print("\n - help: displays information about UI options.\n"
                          " - myip: displays ip address of process.\n"
                          " - myport: displays listening port of process.\n"
                          " - connect <destination> <port no>: establishes TCP connection to the ip address "
                          "<destination> at specified port number <port_num>.\n"
                          " - list: lists all connections including connection id, ip address, & port number.\n"
                          " - terminate <connection id>: removes the specified connection from the list.\n"
                          " - send <connection id> <message>: sends a message to the specified connection.\n"
                          " - exit: closes all connections and terminates the current process.\n")
                case "myip":
                    print("\nThis process' IP address is " + myip + ".\n")
                case "myport":
                    print("\nThis process' listening port is " + str(port) + ".\n")
                case k if "connect" in k:
                    try:
                        str_list = userinput.split()
                        target_ip = str_list[1]
                        target_port = int(str_list[2])
                        try:
                            if any(other_ip == target_ip and other_port == target_port
                                   for (_, other_ip, other_port) in conn_list):
                                print("\nConnection already exists.\n")
                            elif (target_ip == myip) and (target_port == port):
                                print("\nCannot connect to own connection.\n")
                            else:
                                # Create new socket
                                s = socket.socket()
                                s.settimeout(5)
                                s.connect((target_ip, target_port))

                                # Send own info for other host to add to list & connect
                                my_info = f"{myip} {port}"
                                s.send(my_info.encode())
                                s.settimeout(None)

                                # Add successful connection to list

                                conn_list.append((s, target_ip, target_port))
                                print("\nSuccessful connection with " + target_ip + " at port no. "
                                      + str(target_port) + "\n")

                                # Receives incoming messages from connected user
                                # Fixed the following bug:
                                #     1)  server1 -> server2
                                #     2)  server2 tries to send message to server1
                                #     3)  message successfully sent by server2 but server1 can't see it
                                recv_thread = threading.Thread(
                                    target=recv_messages,
                                    args=(s, target_ip, target_port),
                                    daemon=True)
                                recv_thread.start()
                        except (OSError, ValueError, OverflowError, socket.timeout):
                            print("\nInvalid Destination Address &/or Port Number.\n")
                        except IndexError:
                            print("\nInvalid Input. Must follow format: connect <dest. address> <port no.>.\n")
                    except IndexError:
                        print("\nInvalid Input: Must follow format: connect <IP address> <port>\n")
                case "list":
                    print("\nID\t|\tIP ADDRESS\t|\tPORT NUMBER")
                    for id in range(len(conn_list)):
                        print(str(id) + "\t\t" + str(conn_list[id][1]) + "\t\t" + str(conn_list[id][2]))
                    print()
                case k if "terminate" in k:
                    try:
                        str_list = userinput.split()
                        conn_id = int(str_list[1])

                        # If list is empty
                        if len(conn_list) == 0:
                            print("\nNo connections to terminate.\n")
                        else:
                            try:
                                print("\nConnection with " + conn_list[conn_id][1] + " has been terminated.\n")

                                # Send termination to address at id
                                s_id = conn_list[conn_id][0]
                                s_id.send("close".encode())
                                s_id.close()

                                delete_conn(s_id)
                            except IndexError:
                                print("\nConnection does not exist.\n")
                    except IndexError:
                        print("\nNo Connection ID entered.\n")
                case k if "send" in k:
                    try:
                        str_list = userinput.split()
                        conn_id = int(str_list[1])
                        s_id = conn_list[conn_id][0]
                        message = " ".join(str_list[2:])
                        if message == "":  # if no message after connection id
                            print("\nNo message to send.\n")
                            continue
                        print("\nMessage sent to connection ID " + str(conn_id) + ": \"" + message + "\".\n")
                        s_id.send(message.encode())
                    except IndexError:
                        print("\nConnection does not exist.\n")
                    except ValueError:
                        print("\nInvalid Input. Must follow format: send <connection id> <message>.\n")
                case "exit":
                    print("\nConnections Terminated:")
                    if len(conn_list) != 0:
                        for s, ip, p in conn_list[:]:
                            s.send("close".encode())
                            s.close()
                            print(" - (" + ip + ", " + str(p) + ")")
                            delete_conn(s)

                    # Signal client shutdown to terminate host thread
                    client_shutdown.set()
                    break
                case _:
                    print("\nInvalid command. Type \"help\" to view available commands.\n")
    except ConnectionRefusedError:
        print("The port number is invalid.")


# Listens to incoming messages from connections made to other servers (similar to handle_connections)
# For ex. allows S1 to receive messages from S2 if S1 -> S2
def recv_messages(sock, other_ip, other_port):
    try:
        while not client_shutdown.is_set():
            data = sock.recv(1024)
            if not data:
                print("\n\nConnection with (" + other_ip + ", " + str(other_port) + ") has been terminated. \n")
                print("> ", end="", flush=True)
                break
            message = data.decode()
            if message == "close":
                print("\n\nConnection with (" + other_ip + ", " + str(other_port) + ") has been terminated. \n")
                print("> ", end="", flush=True)
                break
            else:
                print()
                print("\nMessage received from (" + other_ip + ", " + str(other_port) + ")")
                print("Message: \"" + str(message) + "\"\n")
                print("> ", end="", flush=True)
    except OSError:
        pass
    finally:
        delete_conn(sock)
        sock.close()


def start_host():
    try:
        s = socket.socket()
        s.bind(('0.0.0.0', port))
        host_initialized.set()
    except OverflowError:  # port out of range
        print("Port Number must be between 0 and 65535.")
        client_shutdown.set()
        return
    # Refuse connection if port is active
    except OSError as e:  # Map OSError based on errno (standard error traceback from OS module)
        if e.errno == errno.EADDRINUSE:
            print("Port Number is already in use.")

    s.listen(3)  # Pauses for 1 second

    s.settimeout(1)  # While client still running

    while not client_shutdown.is_set():
        try:
            # accept connection request
            connection_socket, address = s.accept()
            print()
            print("\nGot connection from " + str(address) + ".")

            thread = threading.Thread(target=handle_connection, args=(connection_socket, address), daemon=True)
            thread.start()
        except socket.timeout:
            continue


def main():
    # Host Thread
    h_thread = threading.Thread(target=start_host, daemon=True)
    h_thread.start()

    # wait until host is initialized
    host_initialized.wait(timeout=1)  # 1 sec timeout to avoid hanging if host fails to start

    if not host_initialized.is_set():
        print("Failed to start connection. Exiting.")
        client_shutdown.set()
        h_thread.join()
        return

    # Client Thread
    c_thread = threading.Thread(target=client_side)
    c_thread.start()

    c_thread.join()

    # Signal client shutdown
    client_shutdown.set()
    h_thread.join()

    print("Program Exited Successfully.")


main()
