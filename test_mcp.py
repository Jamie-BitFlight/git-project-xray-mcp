import asyncio
from fastmcp import Client
import json

from fastmcp.client.transports import StdioTransport

async def main():
    # Connect to the running xray-mcp server
    transport = StdioTransport(command="xray-mcp", args=[])
    client = Client(transport) 

    async with client:
        # 1. Send initialize request (handled automatically by Client context manager)
        # The client automatically sends initialize and waits for response
        
        # 2. Send build_index request
        print("Sending build_index request...")
        result = await client.call_tool(
            "build_index", 
            {
                "path": "/Users/srijanshukla/code/xray"
            }
        )
        
        # Print the result from build_index
        print("Build Index Result:")
        print(json.dumps(result.data, indent=2))

if __name__ == "__main__":
    asyncio.run(main())