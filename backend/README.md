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
                logger.debug(event)
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


## To subscribe a web client to receive messages from a WebSocket endpoint about events from S3, you need to:

    Set up the WebSocket endpoint in FastAPI: Create an endpoint where clients can connect via WebSocket.
    Send messages to connected WebSocket clients when an S3 event occurs: Modify the listen_to_s3_events function to send relevant messages to connected clients.

Here's the complete code with the necessary changes:
WebSocket Endpoint

Add a WebSocket endpoint to your FastAPI app:

```python

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
from starlette.websockets import WebSocket
from concurrent.futures import ThreadPoolExecutor
import asyncio
from contextlib import asynccontextmanager
import json
import logging
from s3 import listen_bucket_notification, S3Error  # Assuming you have an s3 module

logger = logging.getLogger(__name__)

class WebsocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Any):
        for conn in self.active_connections:
            await conn.send_text(json.dumps(message))

ws_manager = WebsocketManager()
executor = ThreadPoolExecutor(max_workers=1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    executor.submit(listen_to_s3_events, loop)
    yield
    executor.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Process incoming message if necessary
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

app.include_router(router)

def listen_to_s3_events(loop: asyncio.AbstractEventLoop):
    async def publish_event(message: dict):
        await ws_manager.broadcast(message)

    try:
        with listen_bucket_notification("images", events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]) as events:
            for event in events:
                if event["EventName"].startswith("ObjectCreated"):
                    logger.debug(event)
                    asyncio.run_coroutine_threadsafe(publish_event(event), loop=loop)
    except S3Error as err:
        logger.error(f"S3 Error: {err}")
```
Client-Side Code

To receive messages from the WebSocket endpoint on the client side, you can use JavaScript:

```javascript

const websocket = new WebSocket("ws://yourserveraddress/ws");

websocket.onopen = function(event) {
    console.log("Connected to the WebSocket server.");
};

websocket.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log("Received a message from the server:", message);
    // Process the received S3 event message
};

websocket.onclose = function(event) {
    console.log("Disconnected from the WebSocket server.");
};

websocket.onerror = function(event) {
    console.error("WebSocket error observed:", event);
};
```
Explanation

    WebSocket Endpoint:
        A WebSocket endpoint /ws is added to handle WebSocket connections.
        ws_manager.connect adds the WebSocket connection to the list of active connections.
        ws_manager.disconnect removes the WebSocket connection from the list when the client disconnects.

    Broadcasting Messages:
        The broadcast method in WebsocketManager sends a JSON-encoded message to all active WebSocket connections.

    Listening to S3 Events:
        The listen_to_s3_events function listens for S3 events and, when an ObjectCreated event occurs, it publishes the event to connected WebSocket clients.

    Client-Side Code:
        The JavaScript code establishes a WebSocket connection to the /ws endpoint.
        It handles incoming messages, logging them to the console (or processing them as needed).

This setup ensures that when an ObjectCreated event occurs in the S3 bucket, connected web clients receive a message with the event payload.


## To filter the S3 events on the server side and only send messages to WebSocket clients when the object.key starts with a specific prefix (e.g., 38104499-c25e-4e30-8e24-fa6c6620aeb5), you can implement a subscription mechanism where clients specify the prefix they are interested in when they connect.

Here's how to modify the code to include this feature:
Server-Side Code

Update the WebsocketManager to handle subscriptions based on object key prefixes:

```python

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
from starlette.websockets import WebSocket
from concurrent.futures import ThreadPoolExecutor
import asyncio
from contextlib import asynccontextmanager
import json
import logging
from s3 import listen_bucket_notification, S3Error  # Assuming you have an s3 module
from typing import List, Dict

logger = logging.getLogger(__name__)

class WebsocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]

    async def broadcast(self, message: dict):
        for conn, prefix in self.subscriptions.items():
            if message['object']['key'].startswith(prefix):
                await conn.send_text(json.dumps(message))

    def subscribe(self, websocket: WebSocket, prefix: str):
        self.subscriptions[websocket] = prefix

ws_manager = WebsocketManager()
executor = ThreadPoolExecutor(max_workers=1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    executor.submit(listen_to_s3_events, loop)
    yield
    executor.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if "subscribe" in message:
                ws_manager.subscribe(websocket, message["subscribe"])
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

app.include_router(router)

def listen_to_s3_events(loop: asyncio.AbstractEventLoop):
    async def publish_event(message: dict):
        await ws_manager.broadcast(message)

    try:
        with listen_bucket_notification("images", events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]) as events:
            for event in events:
                if event["EventName"].startswith("ObjectCreated"):
                    logger.debug(event)
                    asyncio.run_coroutine_threadsafe(publish_event(event), loop=loop)
    except S3Error as err:
        logger.error(f"S3 Error: {err}")
```
Client-Side Code

Update the client-side code to send a subscription message when connecting:

```javascript

const websocket = new WebSocket("ws://yourserveraddress/ws");

websocket.onopen = function(event) {
    console.log("Connected to the WebSocket server.");
    // Send a subscription message with the prefix
    websocket.send(JSON.stringify({ subscribe: "38104499-c25e-4e30-8e24-fa6c6620aeb5" }));
};

websocket.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log("Received a message from the server:", message);
    // Process the received S3 event message
};

websocket.onclose = function(event) {
    console.log("Disconnected from the WebSocket server.");
};

websocket.onerror = function(event) {
    console.error("WebSocket error observed:", event);
};
```
Explanation

    Server-Side Code:
        WebsocketManager:
            subscriptions: A dictionary mapping each WebSocket connection to its subscribed prefix.
            broadcast: Modified to check the prefix before sending the message to each client.
            subscribe: Method to add a subscription for a specific WebSocket connection.
        WebSocket Endpoint:
            Listens for a subscription message from the client and registers the subscription using the subscribe method of WebsocketManager.
        listen_to_s3_events:
            Unchanged, but now the broadcast method will filter events based on the subscription prefixes.

    Client-Side Code:
        Sends a subscription message immediately after the WebSocket connection is established, specifying the prefix it is interested in.

This setup ensures that clients only receive messages for S3 events where the object.key starts with the specified prefix.


## To allow each WebSocket client to subscribe to multiple prefixes, you can modify the subscriptions dictionary to map each WebSocket connection to a list of prefixes. Here's how you can adjust the code to support multiple prefix subscriptions for each client:
Server-Side Code

Update the WebsocketManager class and WebSocket endpoint to handle multiple subscriptions per client:

```python

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
from starlette.websockets import WebSocket
from concurrent.futures import ThreadPoolExecutor
import asyncio
from contextlib import asynccontextmanager
import json
import logging
from s3 import listen_bucket_notification, S3Error  # Assuming you have an s3 module
from typing import List, Dict

logger = logging.getLogger(__name__)

class WebsocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, List[str]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = []

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]

    async def broadcast(self, message: dict):
        for conn, prefixes in self.subscriptions.items():
            for prefix in prefixes:
                if message['object']['key'].startswith(prefix):
                    await conn.send_text(json.dumps(message))
                    break  # No need to check other prefixes if one matches

    def subscribe(self, websocket: WebSocket, prefix: str):
        if websocket in self.subscriptions:
            self.subscriptions[websocket].append(prefix)

ws_manager = WebsocketManager()
executor = ThreadPoolExecutor(max_workers=1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    executor.submit(listen_to_s3_events, loop)
    yield
    executor.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if "subscribe" in message:
                ws_manager.subscribe(websocket, message["subscribe"])
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

app.include_router(router)

def listen_to_s3_events(loop: asyncio.AbstractEventLoop):
    async def publish_event(message: dict):
        await ws_manager.broadcast(message)

    try:
        with listen_bucket_notification("images", events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]) as events:
            for event in events:
                if event["EventName"].startswith("ObjectCreated"):
                    logger.debug(event)
                    asyncio.run_coroutine_threadsafe(publish_event(event), loop=loop)
    except S3Error as err:
        logger.error(f"S3 Error: {err}")
```
Client-Side Code

Update the client-side code to send multiple subscription messages if needed:

```javascript

const websocket = new WebSocket("ws://yourserveraddress/ws");

websocket.onopen = function(event) {
    console.log("Connected to the WebSocket server.");
    // Send subscription messages with the prefixes
    websocket.send(JSON.stringify({ subscribe: "38104499-c25e-4e30-8e24-fa6c6620aeb5" }));
    websocket.send(JSON.stringify({ subscribe: "another-prefix" }));
};

websocket.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log("Received a message from the server:", message);
    // Process the received S3 event message
};

websocket.onclose = function(event) {
    console.log("Disconnected from the WebSocket server.");
};

websocket.onerror = function(event) {
    console.error("WebSocket error observed:", event);
};
```
Explanation

    Server-Side Code:
        WebsocketManager:
            subscriptions: A dictionary mapping each WebSocket connection to a list of prefixes.
            broadcast: Checks if any prefix in the list matches the event's object.key.
            subscribe: Adds a prefix to the list of prefixes for the specified WebSocket connection.
        WebSocket Endpoint:
            Allows clients to send multiple subscription messages, each adding a prefix to their subscription list.

    Client-Side Code:
        Sends multiple subscription messages after establishing the WebSocket connection, subscribing to multiple prefixes.

This setup allows each client to subscribe to multiple prefixes and receive messages for any of the specified prefixes.


# Next steps
- replace image upload endpoint with presigned url from s3 storage
  - return
    - project_id
    - pre-signed url
- the client calls websocket endpoint to subscribe to the events about the project_id
- client uses pre-signed url for the file upload
- websocket endpoint informs about project status



---
To achieve the scenario where a Celery worker notifies a web client via a WebSocket event after completing a task, 
you need to set up a message queue (e.g., Redis) for communication between the Celery worker and the FastAPI server. 
Below is a basic code example illustrating how this can be done:

    Setup FastAPI with WebSockets
    Configure Celery
    Use Redis for message passing

1. Setup FastAPI with WebSockets

First, set up FastAPI to handle WebSocket connections:

```python

# app/main.py
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from celery.result import AsyncResult
import redis

app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, db=0)
websockets = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    websockets[client_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        del websockets[client_id]

@app.get("/status/{task_id}/{client_id}")
async def get_status(task_id: str, client_id: str):
    result = AsyncResult(task_id)
    if result.state == 'SUCCESS':
        if client_id in websockets:
            await websockets[client_id].send_text(f"Task {task_id} finished")
    return {"task_id": task_id, "state": result.state}
```
2. Configure Celery

Next, configure Celery to use Redis as the message broker:

```python

# app/celery_app.py
from celery import Celery

celery_app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

@celery_app.task
def long_running_task(data):
    # Simulate a long-running task
    import time
    time.sleep(10)
    return {"result": "Task completed", "data": data}
```

3. Notify via Redis and WebSocket

Modify the Celery worker to notify FastAPI via Redis once the task is complete:  

```python

# app/tasks.py
import redis
from .celery_app import celery_app

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@celery_app.task
def long_running_task(data, client_id):
    import time
    time.sleep(10)  # Simulate a long-running task
    redis_client.publish('task_notifications', client_id)
    return {"result": "Task completed", "data": data}
```
4. Subscribe to Redis Channel in FastAPI

Finally, subscribe to the Redis channel in FastAPI to forward messages to the WebSocket:

```python

# app/main.py (continued)
import threading

def redis_listener():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('task_notifications')
    for message in pubsub.listen():
        if message['type'] == 'message':
            client_id = message['data'].decode('utf-8')
            if client_id in websockets:
                loop = asyncio.get_event_loop()
                loop.create_task(websockets[client_id].send_text("Task completed"))

threading.Thread(target=redis_listener, daemon=True).start()
```
Running the Application

To run the application:

    Start the FastAPI server:

```bash

uvicorn app.main:app --reload
```
Start the Celery worker:

```bash

    celery -A app.celery_app worker --loglevel=info
```
This setup allows Celery to notify the FastAPI server via Redis when a task is complete, and FastAPI will then send a WebSocket message to the client.
i want to use rabbitmq instead as message brocker and keep redis as result backend

---

To use RabbitMQ as the message broker and Redis as the result backend, 
you need to configure Celery accordingly and set up FastAPI to communicate with RabbitMQ for notifications.


Here’s a step-by-step guide on how to achieve this:
1. Setup FastAPI with WebSockets

First, set up FastAPI to handle WebSocket connections:

```python

# app/main.py
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from celery.result import AsyncResult
import redis

app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, db=0)
websockets = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    websockets[client_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        del websockets[client_id]

@app.get("/status/{task_id}/{client_id}")
async def get_status(task_id: str, client_id: str):
    result = AsyncResult(task_id)
    if result.state == 'SUCCESS':
        if client_id in websockets:
            await websockets[client_id].send_text(f"Task {task_id} finished")
    return {"task_id": task_id, "state": result.state}
```
2. Configure Celery with RabbitMQ and Redis

Configure Celery to use RabbitMQ as the message broker and Redis as the result backend:

```python

# app/celery_app.py
from celery import Celery

celery_app = Celery(
    'tasks',
    broker='amqp://guest:guest@localhost//',  # RabbitMQ broker URL
    backend='redis://localhost:6379/0'        # Redis result backend
)

@celery_app.task
def long_running_task(data):
    import time
    time.sleep(10)
    return {"result": "Task completed", "data": data}
```
3. Notify via RabbitMQ and WebSocket

Set up a RabbitMQ listener to forward messages to the WebSocket:

```python

# app/tasks.py
import pika
import json
from .celery_app import celery_app

# Establish RabbitMQ connection and channel once
rabbitmq_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
rabbitmq_channel = rabbitmq_connection.channel()
rabbitmq_channel.queue_declare(queue='task_notifications')

def notify_client(client_id):
    message = json.dumps({'client_id': client_id})
    rabbitmq_channel.basic_publish(exchange='',
                                   routing_key='task_notifications',
                                   body=message)

@celery_app.task
def long_running_task(data, client_id):
    import time
    time.sleep(10)  # Simulate a long-running task
    notify_client(client_id)
    return {"result": "Task completed", "data": data}
```
4. Subscribe to RabbitMQ in FastAPI

Subscribe to the RabbitMQ queue in FastAPI to forward messages to the WebSocket:

```python

# app/main.py (continued)
import threading
import pika
import json

# Establish RabbitMQ connection and channel once
rabbitmq_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
rabbitmq_channel = rabbitmq_connection.channel()
rabbitmq_channel.queue_declare(queue='task_notifications')

def rabbitmq_listener():
    def callback(ch, method, properties, body):
        message = json.loads(body)
        client_id = message['client_id']
        if client_id in websockets:
            loop = asyncio.get_event_loop()
            loop.create_task(websockets[client_id].send_text("Task completed"))

    rabbitmq_channel.basic_consume(queue='task_notifications', on_message_callback=callback, auto_ack=True)
    rabbitmq_channel.start_consuming()

threading.Thread(target=rabbitmq_listener, daemon=True).start()
```
Running the Application

To run the application:

    Start the RabbitMQ server:

```    bash

sudo rabbitmq-server
```
Start the FastAPI server:

```bash

uvicorn app.main:app --reload
```
Start the Celery worker:

```bash

    celery -A app.celery_app worker --loglevel=info
```
This setup allows Celery to use RabbitMQ as the message broker and Redis as the result backend. 
When a task is complete, Celery sends a notification to RabbitMQ, and FastAPI listens to RabbitMQ to forward the message to the appropriate WebSocket client.