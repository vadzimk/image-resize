# Notes

start docker-compose  
```shell
set -o allexport
source .env
set +o allexport
docker-compose up -d
```

https://pypi.org/project/minio/


https://min.io/docs/minio/linux/developers/python/API.html#listen-bucket-notification-bucket-name-prefix-suffix-events-s3-objectcreated-s3-objectremoved-s3-objectaccessed  
```python
with client.listen_bucket_notification(
    "my-bucket",
    prefix="my-prefix/",
    events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
) as events:
    for event in events:
        print(event)
```

```text
PASSED
tests/test_api.py::test_upload_file_returns_Project create_upload_file-->0h:0m:1s:937ms
response: {'project_id': '85653a59-b795-43e3-980f-7b314b8245e5',
 'state': 'init',
 'versions': {'big_1920': '85653a59-b795-43e3-980f-7b314b8245e5/photo_big_1920.jpeg',
              'big_thumb': '85653a59-b795-43e3-980f-7b314b8245e5/photo_big_thumb.jpeg',
              'd2500': '85653a59-b795-43e3-980f-7b314b8245e5/photo_d2500.jpeg',
              'original': '85653a59-b795-43e3-980f-7b314b8245e5/photo_original.jpeg',
              'thumb': '85653a59-b795-43e3-980f-7b314b8245e5/photo_thumb.jpeg'}}
```



## websockets basic app

basic fastapi websockets example app


Let's create a basic FastAPI application with WebSocket support. This example will include a simple WebSocket endpoint that allows clients to connect, send messages, and receive responses.
Pseudocode

    Setup FastAPI: Install FastAPI and Uvicorn.
    Create FastAPI app: Initialize a FastAPI application.
    Create WebSocket endpoint: Define an endpoint for WebSocket connections.
    Handle WebSocket connections: Accept and handle messages from WebSocket clients.
    Run the application: Use Uvicorn to run the FastAPI application.

Step-by-Step Plan

    Install required packages:

    bash

    pip install fastapi uvicorn

    Create the FastAPI application:
        Initialize the FastAPI app.
        Define a WebSocket endpoint.
        Handle incoming messages and send responses.

    Run the FastAPI application:
        Use Uvicorn to serve the FastAPI app.

Full Implementation

Here's the full implementation of a basic FastAPI application with WebSocket support.

```python

# app/main.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket Example</title>
    </head>
    <body>
        <h1>WebSocket Example</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id="messages">
        </ul>
        <script>
            const ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                const messages = document.getElementById('messages');
                const message = document.createElement('li');
                const content = document.createTextNode(event.data);
                message.appendChild(content);
                messages.appendChild(message);
            };
            function sendMessage(event) {
                const input = document.getElementById("messageText");
                ws.send(input.value);
                input.value = '';
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Instructions to Run the App

    Save the code:
        Save the code in a file named main.py inside an app directory.
    Run the FastAPI app:

    bash

    uvicorn app.main:app --reload

    Access the app:
        Open your web browser and go to http://localhost:8000/.

Explanation

    HTMLResponse: Serves a simple HTML page with JavaScript to interact with the WebSocket.
    WebSocket endpoint: Accepts WebSocket connections at /ws and handles incoming messages in an infinite loop.
    JavaScript: Connects to the WebSocket server, sends messages from the input field, and displays received messages.

Next Steps

a. Add more complex WebSocket handling, such as broadcasting messages to all connected clients.
b. Implement unit tests to ensure the WebSocket endpoints work as expected.


## To send S3 events to the WebSocket clients, you need to modify the listen_to_s3_events function to publish these events to a WebSocket manager. This manager will handle broadcasting messages to all connected WebSocket clients.

Here's how you can achieve this:

    Create a WebSocket manager to handle WebSocket connections.
    Modify listen_to_s3_events to publish events to WebSocket clients.
    Ensure the WebSocket endpoint can handle messages broadcasted by the manager.

Updated Full Implementation

```python

# app/main.py
import logging
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import asyncio
from s3 import listen_bucket_notification, S3Error  # Import your S3 listening function

logger = logging.getLogger("main")

executor = ThreadPoolExecutor(max_workers=1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    executor.submit(listen_to_s3_events, loop)
    yield
    executor.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket Example</title>
    </head>
    <body>
        <h1>WebSocket Example</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id="messages">
        </ul>
        <script>
            const ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                const messages = document.getElementById('messages');
                const message = document.createElement('li');
                const content = document.createTextNode(event.data);
                message.appendChild(content);
                messages.appendChild(message);
            };
            function sendMessage(event) {
                const input = document.getElementById("messageText");
                ws.send(input.value);
                input.value = '';
                event.preventDefault();
            }
        </script>
    </body>
</html>"""



@app.get("/")
async def get():
    return HTMLResponse(html)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

ws_manager = WebSocketManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.broadcast(f"Message text was: {data}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(websocket)

def listen_to_s3_events(loop):
    async def publish_event(message: str):
        await ws_manager.broadcast(message)
    
    try:
        with listen_bucket_notification("images", events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]) as events:
            for event in events:
                logger.info(event)
                asyncio.run_coroutine_threadsafe(publish_event(f"S3 Event: {event}"), loop)
    except S3Error as err:
        logger.error(f"S3 Error: {err}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
Explanation

    WebSocketManager Class: Manages WebSocket connections and broadcasts messages to all connected clients.
    listen_to_s3_events Function: Listens for S3 events and uses asyncio.run_coroutine_threadsafe to forward these events to the WebSocket manager's broadcast method.
    WebSocket Endpoint: Connects WebSocket clients and handles incoming messages by broadcasting them to all connected clients.

Instructions to Run the App

    Save the code:
        Save the code in a file named main.py inside an app directory.
    Run the FastAPI app:

    bash

    uvicorn app.main:app --reload

    Access the app:
        Open your web browser and go to http://localhost:8000/.

Next Steps

a. Add authentication to the WebSocket connections to secure the communication.
b. Implement unit tests for the WebSocket manager and S3 event handling logic.