#!/usr/bin/env python3
"""
PyRedis - A Redis Clone Implementation in Python
-by Shub (Blackth0rns)
===============================================

A simplified Redis-like in-memory data structure server implementation
that supports basic Redis commands and data types.
"""

import socket
import threading
import time
import json
import re
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict
import heapq


class PyRedisServer:
    """
    Main PyRedis server class that handles client connections and command processing.

    Supports the following Redis data types and commands:
    - Strings: GET, SET, DEL, EXISTS, INCR, DECR
    - Lists: LPUSH, RPUSH, LPOP, RPOP, LLEN, LRANGE
    - Sets: SADD, SREM, SMEMBERS, SCARD, SISMEMBER
    - Hashes: HSET, HGET, HDEL, HKEYS, HVALS, HGETALL
    - Expiration: EXPIRE, TTL
    - General: KEYS, FLUSHALL, PING
    """

    def __init__(self, host='localhost', port=6379):
        self.host = host
        self.port = port
        self.data = {}  # Main data storage
        self.expiry = {}  # Key expiration timestamps
        self.lock = threading.RLock()  # Thread-safe operations
        self.running = False
        self.server_socket = None

    def start(self):
        """Start the PyRedis server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        print(f"PyRedis server started on {self.host}:{self.port}")

        # Start expiry cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_expired_keys, daemon=True)
        cleanup_thread.start()

        try:
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                except OSError:
                    if self.running:
                        raise
        except KeyboardInterrupt:
            print("\nShutting down PyRedis server...")
        finally:
            self.stop()

    def stop(self):
        """Stop the PyRedis server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

    def _handle_client(self, client_socket, addr):
        """Handle individual client connections."""
        print(f"Client connected from {addr}")

        try:
            while self.running:
                data = client_socket.recv(1024).decode('utf-8').strip()
                if not data:
                    break

                response = self._process_command(data)
                client_socket.send(f"{response}\n".encode('utf-8'))

        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            client_socket.close()
            print(f"Client {addr} disconnected")

    def _process_command(self, command_str: str) -> str:
        """Process a Redis command and return the response."""
        try:
            parts = self._parse_command(command_str)
            if not parts:
                return "-ERR empty command"

            cmd = parts[0].upper()
            args = parts[1:]

            # Route command to appropriate handler
            if cmd == 'PING':
                return self._cmd_ping(args)
            elif cmd == 'SET':
                return self._cmd_set(args)
            elif cmd == 'GET':
                return self._cmd_get(args)
            elif cmd == 'DEL':
                return self._cmd_del(args)
            elif cmd == 'EXISTS':
                return self._cmd_exists(args)
            elif cmd == 'INCR':
                return self._cmd_incr(args)
            elif cmd == 'DECR':
                return self._cmd_decr(args)
            elif cmd == 'LPUSH':
                return self._cmd_lpush(args)
            elif cmd == 'RPUSH':
                return self._cmd_rpush(args)
            elif cmd == 'LPOP':
                return self._cmd_lpop(args)
            elif cmd == 'RPOP':
                return self._cmd_rpop(args)
            elif cmd == 'LLEN':
                return self._cmd_llen(args)
            elif cmd == 'LRANGE':
                return self._cmd_lrange(args)
            elif cmd == 'SADD':
                return self._cmd_sadd(args)
            elif cmd == 'SREM':
                return self._cmd_srem(args)
            elif cmd == 'SMEMBERS':
                return self._cmd_smembers(args)
            elif cmd == 'SCARD':
                return self._cmd_scard(args)
            elif cmd == 'SISMEMBER':
                return self._cmd_sismember(args)
            elif cmd == 'HSET':
                return self._cmd_hset(args)
            elif cmd == 'HGET':
                return self._cmd_hget(args)
            elif cmd == 'HDEL':
                return self._cmd_hdel(args)
            elif cmd == 'HKEYS':
                return self._cmd_hkeys(args)
            elif cmd == 'HVALS':
                return self._cmd_hvals(args)
            elif cmd == 'HGETALL':
                return self._cmd_hgetall(args)
            elif cmd == 'EXPIRE':
                return self._cmd_expire(args)
            elif cmd == 'TTL':
                return self._cmd_ttl(args)
            elif cmd == 'KEYS':
                return self._cmd_keys(args)
            elif cmd == 'FLUSHALL':
                return self._cmd_flushall(args)
            else:
                return f"-ERR unknown command '{cmd}'"

        except Exception as e:
            return f"-ERR {str(e)}"

    def _parse_command(self, command_str: str) -> List[str]:
        """Parse a command string into parts, handling quoted strings."""
        parts = []
        current = ""
        in_quotes = False
        escape_next = False

        for char in command_str:
            if escape_next:
                current += char
                escape_next = False
            elif char == '\\':
                escape_next = True
            elif char == '"' and not in_quotes:
                in_quotes = True
            elif char == '"' and in_quotes:
                in_quotes = False
            elif char.isspace() and not in_quotes:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char

        if current:
            parts.append(current)

        return parts

    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired."""
        if key in self.expiry:
            if time.time() > self.expiry[key]:
                with self.lock:
                    self.data.pop(key, None)
                    self.expiry.pop(key, None)
                return True
        return False

    def _cleanup_expired_keys(self):
        """Background thread to clean up expired keys."""
        while self.running:
            current_time = time.time()
            expired_keys = []

            with self.lock:
                for key, expiry_time in self.expiry.items():
                    if current_time > expiry_time:
                        expired_keys.append(key)

                for key in expired_keys:
                    self.data.pop(key, None)
                    self.expiry.pop(key, None)

            time.sleep(1)  # Check every second

    # String Commands
    def _cmd_ping(self, args: List[str]) -> str:
        """PING command - test connection."""
        if args:
            return f"+{args[0]}"
        return "+PONG"

    def _cmd_set(self, args: List[str]) -> str:
        """SET key value - set string value."""
        if len(args) < 2:
            return "-ERR wrong number of arguments for 'set' command"

        key, value = args[0], args[1]

        with self.lock:
            self.data[key] = {'type': 'string', 'value': value}
            # Remove any existing expiry
            self.expiry.pop(key, None)

        return "+OK"

    def _cmd_get(self, args: List[str]) -> str:
        """GET key - get string value."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'get' command"

        key = args[0]

        if self._is_expired(key):
            return "$-1"

        with self.lock:
            if key not in self.data:
                return "$-1"

            data = self.data[key]
            if data['type'] != 'string':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            return f"+{data['value']}"

    def _cmd_del(self, args: List[str]) -> str:
        """DEL key [key ...] - delete keys."""
        if not args:
            return "-ERR wrong number of arguments for 'del' command"

        deleted = 0
        with self.lock:
            for key in args:
                if key in self.data:
                    del self.data[key]
                    self.expiry.pop(key, None)
                    deleted += 1

        return f":{deleted}"

    def _cmd_exists(self, args: List[str]) -> str:
        """EXISTS key [key ...] - check if keys exist."""
        if not args:
            return "-ERR wrong number of arguments for 'exists' command"

        count = 0
        for key in args:
            if not self._is_expired(key) and key in self.data:
                count += 1

        return f":{count}"

    def _cmd_incr(self, args: List[str]) -> str:
        """INCR key - increment integer value."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'incr' command"

        key = args[0]

        with self.lock:
            if self._is_expired(key) or key not in self.data:
                self.data[key] = {'type': 'string', 'value': '1'}
                return ":1"

            data = self.data[key]
            if data['type'] != 'string':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            try:
                value = int(data['value'])
                value += 1
                data['value'] = str(value)
                return f":{value}"
            except ValueError:
                return "-ERR value is not an integer or out of range"

    def _cmd_decr(self, args: List[str]) -> str:
        """DECR key - decrement integer value."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'decr' command"

        key = args[0]

        with self.lock:
            if self._is_expired(key) or key not in self.data:
                self.data[key] = {'type': 'string', 'value': '-1'}
                return ":-1"

            data = self.data[key]
            if data['type'] != 'string':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            try:
                value = int(data['value'])
                value -= 1
                data['value'] = str(value)
                return f":{value}"
            except ValueError:
                return "-ERR value is not an integer or out of range"

    # List Commands
    def _cmd_lpush(self, args: List[str]) -> str:
        """LPUSH key element [element ...] - push to left of list."""
        if len(args) < 2:
            return "-ERR wrong number of arguments for 'lpush' command"

        key = args[0]
        elements = args[1:]

        with self.lock:
            if self._is_expired(key) or key not in self.data:
                self.data[key] = {'type': 'list', 'value': []}

            data = self.data[key]
            if data['type'] != 'list':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            # Insert at beginning (left)
            for element in reversed(elements):
                data['value'].insert(0, element)

            return f":{len(data['value'])}"

    def _cmd_rpush(self, args: List[str]) -> str:
        """RPUSH key element [element ...] - push to right of list."""
        if len(args) < 2:
            return "-ERR wrong number of arguments for 'rpush' command"

        key = args[0]
        elements = args[1:]

        with self.lock:
            if self._is_expired(key) or key not in self.data:
                self.data[key] = {'type': 'list', 'value': []}

            data = self.data[key]
            if data['type'] != 'list':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            # Append to end (right)
            data['value'].extend(elements)

            return f":{len(data['value'])}"

    def _cmd_lpop(self, args: List[str]) -> str:
        """LPOP key - pop from left of list."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'lpop' command"

        key = args[0]

        if self._is_expired(key):
            return "$-1"

        with self.lock:
            if key not in self.data:
                return "$-1"

            data = self.data[key]
            if data['type'] != 'list':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            if not data['value']:
                return "$-1"

            element = data['value'].pop(0)

            # Clean up empty list
            if not data['value']:
                del self.data[key]

            return f"+{element}"

    def _cmd_rpop(self, args: List[str]) -> str:
        """RPOP key - pop from right of list."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'rpop' command"

        key = args[0]

        if self._is_expired(key):
            return "$-1"

        with self.lock:
            if key not in self.data:
                return "$-1"

            data = self.data[key]
            if data['type'] != 'list':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            if not data['value']:
                return "$-1"

            element = data['value'].pop()

            # Clean up empty list
            if not data['value']:
                del self.data[key]

            return f"+{element}"

    def _cmd_llen(self, args: List[str]) -> str:
        """LLEN key - get length of list."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'llen' command"

        key = args[0]

        if self._is_expired(key) or key not in self.data:
            return ":0"

        data = self.data[key]
        if data['type'] != 'list':
            return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

        return f":{len(data['value'])}"

    def _cmd_lrange(self, args: List[str]) -> str:
        """LRANGE key start stop - get range of list elements."""
        if len(args) != 3:
            return "-ERR wrong number of arguments for 'lrange' command"

        key = args[0]
        try:
            start = int(args[1])
            stop = int(args[2])
        except ValueError:
            return "-ERR value is not an integer or out of range"

        if self._is_expired(key) or key not in self.data:
            return "*0"

        data = self.data[key]
        if data['type'] != 'list':
            return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

        lst = data['value']
        length = len(lst)

        # Handle negative indices
        if start < 0:
            start = max(0, length + start)
        if stop < 0:
            stop = length + stop

        # Clamp to valid range
        start = max(0, min(start, length - 1))
        stop = min(stop, length - 1)

        if start > stop or start >= length:
            return "*0"

        result = lst[start:stop + 1]
        response = f"*{len(result)}"
        for item in result:
            response += f"\n+{item}"

        return response

    # Set Commands
    def _cmd_sadd(self, args: List[str]) -> str:
        """SADD key member [member ...] - add members to set."""
        if len(args) < 2:
            return "-ERR wrong number of arguments for 'sadd' command"

        key = args[0]
        members = args[1:]

        with self.lock:
            if self._is_expired(key) or key not in self.data:
                self.data[key] = {'type': 'set', 'value': set()}

            data = self.data[key]
            if data['type'] != 'set':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            added = 0
            for member in members:
                if member not in data['value']:
                    data['value'].add(member)
                    added += 1

            return f":{added}"

    def _cmd_srem(self, args: List[str]) -> str:
        """SREM key member [member ...] - remove members from set."""
        if len(args) < 2:
            return "-ERR wrong number of arguments for 'srem' command"

        key = args[0]
        members = args[1:]

        if self._is_expired(key) or key not in self.data:
            return ":0"

        with self.lock:
            data = self.data[key]
            if data['type'] != 'set':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            removed = 0
            for member in members:
                if member in data['value']:
                    data['value'].remove(member)
                    removed += 1

            # Clean up empty set
            if not data['value']:
                del self.data[key]

            return f":{removed}"

    def _cmd_smembers(self, args: List[str]) -> str:
        """SMEMBERS key - get all members of set."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'smembers' command"

        key = args[0]

        if self._is_expired(key) or key not in self.data:
            return "*0"

        data = self.data[key]
        if data['type'] != 'set':
            return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

        members = list(data['value'])
        response = f"*{len(members)}"
        for member in members:
            response += f"\n+{member}"

        return response

    def _cmd_scard(self, args: List[str]) -> str:
        """SCARD key - get cardinality (size) of set."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'scard' command"

        key = args[0]

        if self._is_expired(key) or key not in self.data:
            return ":0"

        data = self.data[key]
        if data['type'] != 'set':
            return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

        return f":{len(data['value'])}"

    def _cmd_sismember(self, args: List[str]) -> str:
        """SISMEMBER key member - check if member exists in set."""
        if len(args) != 2:
            return "-ERR wrong number of arguments for 'sismember' command"

        key = args[0]
        member = args[1]

        if self._is_expired(key) or key not in self.data:
            return ":0"

        data = self.data[key]
        if data['type'] != 'set':
            return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

        return ":1" if member in data['value'] else ":0"

    # Hash Commands
    def _cmd_hset(self, args: List[str]) -> str:
        """HSET key field value [field value ...] - set hash fields."""
        if len(args) < 3 or len(args) % 2 == 0:
            return "-ERR wrong number of arguments for 'hset' command"

        key = args[0]

        with self.lock:
            if self._is_expired(key) or key not in self.data:
                self.data[key] = {'type': 'hash', 'value': {}}

            data = self.data[key]
            if data['type'] != 'hash':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            added = 0
            for i in range(1, len(args), 2):
                field = args[i]
                value = args[i + 1]
                if field not in data['value']:
                    added += 1
                data['value'][field] = value

            return f":{added}"

    def _cmd_hget(self, args: List[str]) -> str:
        """HGET key field - get hash field value."""
        if len(args) != 2:
            return "-ERR wrong number of arguments for 'hget' command"

        key = args[0]
        field = args[1]

        if self._is_expired(key) or key not in self.data:
            return "$-1"

        data = self.data[key]
        if data['type'] != 'hash':
            return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

        if field not in data['value']:
            return "$-1"

        return f"+{data['value'][field]}"

    def _cmd_hdel(self, args: List[str]) -> str:
        """HDEL key field [field ...] - delete hash fields."""
        if len(args) < 2:
            return "-ERR wrong number of arguments for 'hdel' command"

        key = args[0]
        fields = args[1:]

        if self._is_expired(key) or key not in self.data:
            return ":0"

        with self.lock:
            data = self.data[key]
            if data['type'] != 'hash':
                return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

            deleted = 0
            for field in fields:
                if field in data['value']:
                    del data['value'][field]
                    deleted += 1

            # Clean up empty hash
            if not data['value']:
                del self.data[key]

            return f":{deleted}"

    def _cmd_hkeys(self, args: List[str]) -> str:
        """HKEYS key - get all hash field names."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'hkeys' command"

        key = args[0]

        if self._is_expired(key) or key not in self.data:
            return "*0"

        data = self.data[key]
        if data['type'] != 'hash':
            return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

        keys = list(data['value'].keys())
        response = f"*{len(keys)}"
        for k in keys:
            response += f"\n+{k}"

        return response

    def _cmd_hvals(self, args: List[str]) -> str:
        """HVALS key - get all hash field values."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'hvals' command"

        key = args[0]

        if self._is_expired(key) or key not in self.data:
            return "*0"

        data = self.data[key]
        if data['type'] != 'hash':
            return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

        values = list(data['value'].values())
        response = f"*{len(values)}"
        for v in values:
            response += f"\n+{v}"

        return response

    def _cmd_hgetall(self, args: List[str]) -> str:
        """HGETALL key - get all hash fields and values."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'hgetall' command"

        key = args[0]

        if self._is_expired(key) or key not in self.data:
            return "*0"

        data = self.data[key]
        if data['type'] != 'hash':
            return "-ERR WRONGTYPE Operation against a key holding the wrong kind of value"

        items = []
        for k, v in data['value'].items():
            items.extend([k, v])

        response = f"*{len(items)}"
        for item in items:
            response += f"\n+{item}"

        return response

    # Expiration Commands
    def _cmd_expire(self, args: List[str]) -> str:
        """EXPIRE key seconds - set key expiration."""
        if len(args) != 2:
            return "-ERR wrong number of arguments for 'expire' command"

        key = args[0]
        try:
            seconds = int(args[1])
        except ValueError:
            return "-ERR value is not an integer or out of range"

        if self._is_expired(key) or key not in self.data:
            return ":0"

        with self.lock:
            self.expiry[key] = time.time() + seconds

        return ":1"

    def _cmd_ttl(self, args: List[str]) -> str:
        """TTL key - get key time to live."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'ttl' command"

        key = args[0]

        if self._is_expired(key):
            return ":-2"

        if key not in self.data:
            return ":-2"

        if key not in self.expiry:
            return ":-1"

        ttl = int(self.expiry[key] - time.time())
        return f":{max(0, ttl)}"

    # General Commands
    def _cmd_keys(self, args: List[str]) -> str:
        """KEYS pattern - find keys matching pattern."""
        if len(args) != 1:
            return "-ERR wrong number of arguments for 'keys' command"

        pattern = args[0]

        # Convert Redis pattern to regex
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        regex = re.compile(f'^{regex_pattern}$')

        matches = []
        for key in list(self.data.keys()):
            if not self._is_expired(key) and regex.match(key):
                matches.append(key)

        response = f"*{len(matches)}"
        for match in matches:
            response += f"\n+{match}"

        return response

    def _cmd_flushall(self, args: List[str]) -> str:
        """FLUSHALL - clear all data."""
        with self.lock:
            self.data.clear()
            self.expiry.clear()

        return "+OK"


class PyRedisClient:
    """
    Simple PyRedis client for testing and demonstration.
    """

    def __init__(self, host='localhost', port=6379):
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        """Connect to PyRedis server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))

    def disconnect(self):
        """Disconnect from PyRedis server."""
        if self.socket:
            self.socket.close()
            self.socket = None

    def execute(self, command: str) -> str:
        """Execute a command and return the response."""
        if not self.socket:
            raise ConnectionError("Not connected to server")

        self.socket.send(f"{command}\n".encode('utf-8'))
        response = self.socket.recv(4096).decode('utf-8').strip()
        return response


def run_demo():
    """Run a demonstration of PyRedis functionality."""
    import time

    print("=== PyRedis Demo ===")

    # Start server in a separate thread
    server = PyRedisServer(port=6380)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    time.sleep(1)  # Give server time to start

    # Create client and connect
    client = PyRedisClient(port=6380)
    client.connect()

    try:
        print("\n1. Basic String Operations:")
        print(f"PING: {client.execute('PING')}")
        print(f"SET name 'PyRedis': {client.execute('SET name PyRedis')}")
        print(f"GET name: {client.execute('GET name')}")
        print(f"SET counter 10: {client.execute('SET counter 10')}")
        print(f"INCR counter: {client.execute('INCR counter')}")
        print(f"DECR counter: {client.execute('DECR counter')}")
        print(f"GET counter: {client.execute('GET counter')}")

        print("\n2. List Operations:")
        print(f"LPUSH mylist a b c: {client.execute('LPUSH mylist a b c')}")
        print(f"RPUSH mylist x y z: {client.execute('RPUSH mylist x y z')}")
        print(f"LLEN mylist: {client.execute('LLEN mylist')}")
        print(f"LRANGE mylist 0 -1: {client.execute('LRANGE mylist 0 -1')}")
        print(f"LPOP mylist: {client.execute('LPOP mylist')}")
        print(f"RPOP mylist: {client.execute('RPOP mylist')}")

        print("\n3. Set Operations:")
        print(f"SADD myset apple banana cherry: {client.execute('SADD myset apple banana cherry')}")
        print(f"SCARD myset: {client.execute('SCARD myset')}")
        print(f"SISMEMBER myset apple: {client.execute('SISMEMBER myset apple')}")
        print(f"SISMEMBER myset grape: {client.execute('SISMEMBER myset grape')}")
        print(f"SMEMBERS myset: {client.execute('SMEMBERS myset')}")
        print(f"SREM myset banana: {client.execute('SREM myset banana')}")

        print("\n4. Hash Operations:")
        print(f"HSET user name John age 30: {client.execute('HSET user name John age 30')}")
        print(f"HGET user name: {client.execute('HGET user name')}")
        print(f"HGET user age: {client.execute('HGET user age')}")
        print(f"HKEYS user: {client.execute('HKEYS user')}")
        print(f"HVALS user: {client.execute('HVALS user')}")
        print(f"HGETALL user: {client.execute('HGETALL user')}")

        print("\n5. Expiration:")
        print(f"SET temp_key temporary_value: {client.execute('SET temp_key temporary_value')}")
        print(f"EXPIRE temp_key 3: {client.execute('EXPIRE temp_key 3')}")
        print(f"TTL temp_key: {client.execute('TTL temp_key')}")
        print("Waiting 4 seconds...")
        time.sleep(4)
        print(f"GET temp_key (should be expired): {client.execute('GET temp_key')}")

        print("\n6. General Operations:")
        print(f"KEYS *: {client.execute('KEYS *')}")
        print(f"EXISTS name counter: {client.execute('EXISTS name counter')}")

    except Exception as e:
        print(f"Demo error: {e}")
    finally:
        client.disconnect()
        server.stop()
        print("\nDemo completed!")


def main():
    """Main function to start PyRedis server."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='PyRedis - Redis Clone Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, default=6379, help='Port to bind to (default: 6379)')
    parser.add_argument('--demo', action='store_true', help='Run demo instead of server')

    args = parser.parse_args()

    if args.demo:
        run_demo()
    else:
        print(f"Starting PyRedis server on {args.host}:{args.port}")
        print("Press Ctrl+C to stop the server")

        server = PyRedisServer(host=args.host, port=args.port)
        try:
            server.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
            server.stop()


if __name__ == "__main__":
    main()
