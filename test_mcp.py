#!/usr/bin/env python3
import json
import sys

# Send initialize request
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "1.0.0",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0.0"}
    }
}
print(json.dumps(request))
print()  # Empty line to signal end of request
sys.stdout.flush()