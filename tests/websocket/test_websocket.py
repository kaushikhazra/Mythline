import asyncio
import websockets
import json

async def test_research_websocket():
    session_id = "test_session_ws"
    uri = f"ws://localhost:8080/api/research/ws/{session_id}"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")

            message = {"content": "Hello, can you help me research Elwynn Forest?"}
            print(f"Sending: {message}")
            await websocket.send(json.dumps(message))

            print("Receiving response...")
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)

                    if data.get("type") == "token":
                        print(data.get("content"), end="", flush=True)
                    elif data.get("type") == "done":
                        print("\n\nDone!")
                        break
                    else:
                        print(f"\nReceived: {data}")

                except asyncio.TimeoutError:
                    print("\nTimeout waiting for response")
                    break

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_research_websocket())
