import asyncio
import websockets
import json

async def test_research_websocket():
    session_id = "test_verbose"
    uri = f"ws://localhost:8080/api/research/ws/{session_id}"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected!\n")

            message = {"content": "Tell me about Elwynn Forest in 3 sentences"}
            print(f"Sending: {message['content']}\n")
            await websocket.send(json.dumps(message))

            print("Response (streaming):")
            print("-" * 60)

            chunk_count = 0
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)

                    if data.get("type") == "token":
                        chunk_count += 1
                        print(data.get("content"), end="", flush=True)
                    elif data.get("type") == "done":
                        print("\n" + "-" * 60)
                        print(f"\n✓ Done! Received {chunk_count} token chunks")
                        break
                    else:
                        print(f"\nReceived: {data}")

                except asyncio.TimeoutError:
                    print("\n\n✗ Timeout waiting for response")
                    break

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_research_websocket())
