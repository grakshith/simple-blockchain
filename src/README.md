# Simple Blockchain

## Problem Setting

### Problem 1

A centralized blockchain maintains all the transactions and the nodes in the network need to execute the Lamport's distributed mutual exclusion algorithm to get exclusive access to the blockchain.

### Problem 2

Each node in the network maintains a blockchain of its own and executes transactions on behalf of the user. They can also send sync messages to all the other nodes to send their blockchain to others. Makes use of Wuu-Bernstein's algorithm for replicated dictionaries.

## Code

1. `client.py` - Implements Lamport's distributed mutual exclusion algorithm and other client functionality.
2. `client_replicated.py` - Implements Wuu-Bernstein's algorithm and other client side blockchain functionality.
3. `lamport.py` - Implements lamport's clock
4. `server.py` - Implements all functionality for the centralized blockchain.
5. `simple_socket.py` - Wrapper around the python socket library to ease the use of sockets in python code.

## Execution

The node configuration is done in the `config.cfg` file. Each entry denotes the port number at which the node is running (on a single system).

**Problem 1**

1. Run `server.py`
2. Run each `client.py` on a different terminal and specify the port number at which this node should run according to the config file.

**Problem 2**

1. Run each `client_replicated.py` on a different terminal and specify the port number at which this node should run according to the config file.

