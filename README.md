**TCP Chat & UDP Distance Vector Routing**

This repository contains two distinct Python-based network applications: a **TCP Client-Server Chat** for real-time communication and a **UDP Distance Vector Routing Protocol** simulation that counts the shortest paths between nodes.

**1. TCP Chat Application**

A multi-threaded chat application allowing users to establish multiple concurrent TCP connections to exchange messages


**How to Run**

Start the application by specifying a listening port:

*python chat.py <port_number>*


**Available Commands**

Once the program is running, you can use the following commands:
- myip: Displays the IP address of the current process
- myport: Displays the listening port of the current process
- connect <destination_ip> <port>: Establishes a TCP connection to a peer
- list: Shows all active connections with their unique IDs
- send <connection_id> <message>: Sends a message to a specific connected peer
- terminate <connection_id>: Safely closes a specific connection
- exit: Closes all connections and terminates the process


**2. UDP Distance Vector Routing**

A decentralized routing simulation where multiple nodes exchange routing tables to find the least-cost path to every other node in the network using the Distance Vector algorithm.


**Topology Configuration**

This application relies on *.txt* files to define the network structure. The format is as follows:
1. Number of total nodes
2. Number of neighbors for the current node
3. Server list (ID, IP, and Port)
4. Link Costs (Source ID, Destination ID, Cost)


**How to Run**

You must initialize each node with its specific topology file and a routing update interval:

*python dv.py
server -t <topology_file.txt> -i <interval_in_seconds>*


**Available Commands**
- display: shows the current routing table (Destination, Cost, and Next Hop)
- update <ID1> <ID2> <new_cost>: Manually updates the link cost between this node and a neighbor
- step: Forces an immediate routing update to be sent to all neighbors
- packets: Displays the number of routing packets received since this command was last run
- disable <ID>: Simulates a link failure by setting the cost to a neighbor to infinity
- crash: Simulates a node failure, notifying neighbors before exiting


**Technical Features**

- **Concurrency:** Uses Python's threading library to handle simultaneous listening and user input
- **Socket Programming:** Demonstrates both SOCK_STREAM (TCP) for reliable messaging and SOCK_DGRAM (UDP) for protocol updates
- **Dynamic Routing:** The UDP application implements Distance Vector logic, where receiving a neighbor's table triggers a recalculation of the local shortest path
- **JSON Serialization:** Routing updates are exchanged as JSON objects for clean data parsing


**Project Members**
- Marco Rodriguez
- Derek Castro
