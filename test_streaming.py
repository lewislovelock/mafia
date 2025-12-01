import asyncio
import httpx
import json
import uvicorn
from multiprocessing import Process
import time

# Function to run the server
def run_server():
    uvicorn.run("api:app", host="127.0.0.1", port=8000, log_level="error")

async def test_streaming():
    print("--- Starting Streaming Verification ---")
    
    # Start server in a separate process
    server_process = Process(target=run_server)
    server_process.start()
    
    # Wait for server to start
    time.sleep(2)
    
    try:
        async with httpx.AsyncClient() as client:
            # 1. Start the game
            print("Starting game...")
            response = await client.post("http://127.0.0.1:8000/start")
            print(f"Start response: {response.json()}")
            
            # 2. Connect to stream
            print("Connecting to stream...")
            async with client.stream("GET", "http://127.0.0.1:8000/stream", timeout=None) as response:
                print("Connected! Listening for events...")
                count = 0
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        event = json.loads(data)
                        print(f"Received Event: [{event['type']}] {event['agent']}: {event['content'][:50]}...")
                        count += 1
                        
                        # Stop after receiving some events to prove it works
                        if count >= 10:
                            print("Received 10 events. Verification successful.")
                            break
                            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")
    finally:
        server_process.terminate()
        server_process.join()

if __name__ == "__main__":
    asyncio.run(test_streaming())
