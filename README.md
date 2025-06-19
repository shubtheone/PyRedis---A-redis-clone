# PyRedis Documentation
## Overview

PyRedis is a simplified Redis-like in-memory data structure server implemented in Python. It provides core Redis functionality including multiple data types, key expiration, and a Redis-compatible command interface. I've used lists and dictionaries to make the datatypes become more compatible. For now it only conists of few data types (main ones).

![image](https://github.com/user-attachments/assets/ddcf4c27-d959-45be-a276-04fe84d18716)


## Architecture

### Core Components

1. **PyRedisServer**: Main server class that handles client connections and command processing
2. **PyRedisClient**: Simple client implementation for testing and demonstration
3. **Thread-safe operations**: Uses threading.RLock for concurrent access
4. **Background expiration**: Automatic cleanup of expired keys

### Data Storage

- **Main Storage**: Dictionary-based key-value store (`self.data`)
- **Expiration Storage**: Separate dictionary for key expiration timestamps (`self.expiry`)
- **Data Types**: Each value is stored as `{'type': 'data_type', 'value': actual_value}`

## Supported Data Types

### 1. Strings

Simple key-value pairs storing string values.

**Commands:**

- `SET key value` - Set string value
- `GET key` - Get string value
- `INCR key` - Increment integer value by 1
- `DECR key` - Decrement integer value by 1

**Example:**

```
> SET name "PyRedis"
+OK
> GET name
+PyRedis
> SET counter 10
+OK
> INCR counter
:11
```

### 2. Lists

Ordered collections of strings, supporting operations at both ends.

**Commands:**

- `LPUSH key element [element ...]` - Push elements to left (beginning)
- `RPUSH key element [element ...]` - Push elements to right (end)
- `LPOP key` - Pop element from left
- `RPOP key` - Pop element from right
- `LLEN key` - Get length of list
- `LRANGE key start stop` - Get range of elements

**Example:**

```
> LPUSH mylist a b c
:3
> LRANGE mylist 0 -1
*3
+c
+b
+a
> RPOP mylist
+a
```

### 3. Sets

Unordered collections of unique strings.

**Commands:**

- `SADD key member [member ...]` - Add members to set
- `SREM key member [member ...]` - Remove members from set
- `SMEMBERS key` - Get all members
- `SCARD key` - Get set cardinality (size)
- `SISMEMBER key member` - Check if member exists

**Example:**

```
> SADD fruits apple banana cherry
:3
> SISMEMBER fruits apple
:1
> SREM fruits banana
:1
> SMEMBERS fruits
*2
+apple
+cherry
```

### 4. Hashes

Maps between string fields and string values.

**Commands:**

- `HSET key field value [field value ...]` - Set hash fields
- `HGET key field` - Get hash field value
- `HDEL key field [field ...]` - Delete hash fields
- `HKEYS key` - Get all field names
- `HVALS key` - Get all field values
- `HGETALL key` - Get all fields and values

**Example:**

```
> HSET user name John age 30 city NYC
:3
> HGET user name
+John
> HGETALL user
*6
+name
+John
+age
+30
+city
+NYC
```

## Key Management

### General Commands

- `DEL key [key ...]` - Delete keys
- `EXISTS key [key ...]` - Check if keys exist
- `KEYS pattern` - Find keys matching pattern (supports * and ? wildcards)
- `FLUSHALL` - Clear all data

### Expiration

- `EXPIRE key seconds` - Set key expiration in seconds
- `TTL key` - Get remaining time to live in seconds

**TTL Return Values:**

- `-2`: Key does not exist or has expired
- `-1`: Key exists but has no expiration
- `>0`: Remaining seconds until expiration

## Protocol

PyRedis uses a simplified version of the Redis Serialization Protocol (RESP).

### Response Types

|Prefix|Type|Description|
|---|---|---|
|`+`|Simple String|Success responses, string values|
|`:`|Integer|Numeric responses|
|`-`|Error|Error messages|
|`$-1`|Null|Null/non-existent values|
|`*`|Array|Multi-value responses|

### Examples

**Simple String:**

```
+OK
+Hello World
```

**Integer:**

```
:42
:0
```

**Error:**

```
-ERR unknown command 'INVALID'
-ERR wrong number of arguments
```

**Array:**

```
*3
+apple
+banana
+cherry
```

## Implementation Details

### Thread Safety

- Uses `threading.RLock` for thread-safe operations
- All data modifications are protected by locks
- Supports concurrent client connections

### Memory Management

- Automatic cleanup of empty collections (lists, sets, hashes)
- Background thread for expired key cleanup
- In-memory storage only (no persistence)

### Error Handling

- Type checking for operations (prevents string operations on lists, etc.)
- Argument validation for all commands
- Graceful handling of network errors

### Expiration System

- Keys can be set to expire after a specified number of seconds
- Background cleanup thread runs every second
- Lazy expiration check on key access

## Usage Examples

### Starting the Server

```python
from pyredis import PyRedisServer

# Create and start server
server = PyRedisServer(host='localhost', port=6379)
server.start()  # Blocks until shutdown
```

### Using the Client

```python
from pyredis import PyRedisClient

# Connect to server
client = PyRedisClient(host='localhost', port=6379)
client.connect()

# Execute commands
response = client.execute('SET greeting "Hello, PyRedis!"')
print(response)  # +OK

response = client.execute('GET greeting')
print(response)  # +Hello, PyRedis!

client.disconnect()
```

### Command Line Usage

You can also connect using any Redis client or telnet:

```bash
# Using telnet
telnet localhost 6379
> PING
+PONG
> SET key value
+OK
> GET key
+value
```

## Performance Characteristics

### Time Complexity

|Operation|Time Complexity|Notes|
|---|---|---|
|GET/SET|O(1)|Hash table lookup|
|LPUSH/RPUSH|O(1)|List append/prepend|
|LPOP/RPOP|O(1)|List pop operations|
|SADD/SREM|O(1)|Set add/remove|
|SMEMBERS|O(N)|N = set size|
|LRANGE|O(S+N)|S = start offset, N = elements|
|KEYS|O(N)|N = total keys (avoid in production)|

### Memory Usage

- Each key-value pair has overhead for type information
- Sets and hashes use Python's built-in data structures
- No memory optimization for large datasets

## Limitations

### Missing Redis Features

- No persistence (data lost on restart)
- No clustering or replication
- No pub/sub messaging
- No Lua scripting
- No transactions
- Limited data types (no sorted sets, streams, etc.)
- No authentication
- No configuration commands

### Performance Limitations

- Single-threaded command processing per client
- No memory optimization
- Python GIL limits true parallelism
- No pipelining support

### Protocol Limitations

- Simplified RESP implementation
- No binary-safe string handling
- Limited error reporting

## Extending PyRedis

### Adding New Commands

1. Add command handler method:

```python
def _cmd_newcommand(self, args: List[str]) -> str:
    # Validate arguments
    if len(args) != expected_count:
        return "-ERR wrong number of arguments"
    
    # Process command
    # Return appropriate response
    return "+OK"
```

2. Register in `_process_command`:

```python
elif cmd == 'NEWCOMMAND':
    return self._cmd_newcommand(args)
```

### Adding New Data Types

1. Update data storage format
2. Add type checking in relevant commands
3. Implement type-specific operations
4. Handle cleanup for empty collections

## Testing

### Running the Demo

```python
# Run the built-in demonstration
python pyredis.py
```

### Unit Testing Framework

```python
import unittest
from pyredis import PyRedisServer, PyRedisClient
import threading
import time

class TestPyRedis(unittest.TestCase):
    def setUp(self):
        self.server = PyRedisServer(port=6381)
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()
        time.sleep(0.1)
        
        self.client = PyRedisClient(port=6381)
        self.client.connect()
    
    def tearDown(self):
        self.client.disconnect()
        self.server.stop()
    
    def test_string_operations(self):
        self.assertEqual(self.client.execute('SET key value'), '+OK')
        self.assertEqual(self.client.execute('GET key'), '+value')
    
    # Add more tests...

if __name__ == '__main__':
    unittest.main()
```

## Troubleshooting

### Common Issues

**Server won't start:**

- Check if port is already in use
- Verify host/port configuration
- Check firewall settings

**Client connection fails:**

- Ensure server is running
- Verify host/port match
- Check network connectivity

**Commands return errors:**

- Verify command syntax
- Check argument count
- Ensure data types match expected operations

**Memory issues:**

- Monitor memory usage for large datasets
- Use FLUSHALL to clear all data
- Restart server to free memory

### Debugging Tips

1. Enable debug logging in server
2. Use telnet for manual command testing
3. Monitor server output for error messages
4. Check client/server version compatibility

## Future Enhancements

### Potential Improvements

- Add persistence with RDB/AOF formats
- Implement clustering support
- Add pub/sub messaging
- Optimize memory usage
- Add authentication
- Support binary-safe strings
- Implement pipelining
- Add sorted sets data type
- Create comprehensive test suite
- Add configuration file support

### Performance Optimizations

- Use asyncio for better concurrency
- Implement connection pooling
- Add memory-efficient data structures
- Optimize command parsing
- Add lazy loading for large values

This documentation provides a comprehensive guide to understanding, using, and extending the PyRedis implementation. The system demonstrates core Redis concepts while remaining simple enough for educational purposes and small-scale applications.
