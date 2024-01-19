import requests
import graphene
from db import (
    create_last_cursor_table,
    get_connection,
    get_last_cursor,
    set_last_cursor,
)
from sqlite import initialise_db
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from resolvers import Query
from starlette.middleware import Middleware
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette_graphene3 import GraphQLApp, make_graphiql_handler
from cachetools import TTLCache
from starlette.types import ASGIApp, Receive, Scope, Send, Message

import sys

sys.path.append("../dapp")
from dapp.core import handle_action
from dapp.util import hex_to_str

import schedule
import time
import threading


import asyncio
from starlette.concurrency import run_in_threadpool

import json
import hashlib

load_dotenv()

# Cache setup
cache = TTLCache(maxsize=600, ttl=0)


MAX_CONCURRENT_REQUESTS = 100

# Create a semaphore
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


class ConcurrencyLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        async with semaphore:
            return await call_next(request)


class CacheMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"] == "/graphql"
        ):
            # Read and cache the request body
            body = await self.read_body(receive)
            cache_key = hashlib.md5(body).hexdigest()

            cached_response = cache.get(cache_key)
            if cached_response:
                # Respond with the cached response
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [
                            [b"content-type", b"application/json"],
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": cached_response,
                    }
                )
                return

            # Modify the receive function to return the cached body
            async def custom_receive() -> Message:
                return {"type": "http.request", "body": body, "more_body": False}

            # Cache the response for future requests
            custom_send = self.create_custom_send(send, cache_key)
            await self.app(scope, custom_receive, custom_send)
        else:
            await self.app(scope, receive, send)

    async def read_body(self, receive: Receive) -> bytes:
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
        return body

    def create_custom_send(self, send: Send, cache_key: str):
        async def custom_send(message: Message) -> None:
            if message["type"] == "http.response.body":
                # Cache the response
                cache[cache_key] = message["body"]
            await send(message)

        return custom_send


middleware = [
    Middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    ),
    Middleware(ConcurrencyLimitMiddleware),
    Middleware(CacheMiddleware),
]

schema = graphene.Schema(query=Query)
app = Starlette(middleware=middleware)

app.mount("/", GraphQLApp(schema, on_get=make_graphiql_handler()))  # Graphiql IDE


# Initialise the last cursor tables if it doesn't exist
create_last_cursor_table()

GRAPHQL_API = "http://localhost:4000/graphql"


def run_query():
    last_cursor = get_last_cursor()
    print(f"Running query with cursor: {last_cursor}")

    graphql_query = f"""
        {{
            reports{f'(after:"{last_cursor}")' if last_cursor else ""} {{
                edges{{
                    cursor
                    node{{
                        index
                        payload,
                        input{{
                            msgSender
                            timestamp
                            payload
                            blockNumber
                        }}
                    }}
                }}
            }}
        }}
    """

    response = requests.post(GRAPHQL_API, json={"query": graphql_query})
    data = response.json()

    for edge in data.get("data", {}).get("reports", {}).get("edges", []):
        node = edge.get("node", {})
        try:
            report_payload = hex_to_str(node["payload"])
            report = json.loads(report_payload)
            if report["message"] != "Success":
                continue
            conn = get_connection()
            formatted_data = {
                "payload": node["input"]["payload"],
                "metadata": {
                    "msg_sender": node["input"]["msgSender"],
                    "timestamp": int(node["input"]["timestamp"]),
                    "block_number": int(node["input"]["blockNumber"]),
                },
            }
            handle_action(formatted_data, conn)
            conn.commit()
            conn.close()
        except Exception as e:
            print(e)
            pass
        
        set_last_cursor(edge.get("cursor"))


# Schedule the function to run every 3 seconds
schedule.every(1).seconds.do(run_query)


# # Define the job thread
def job_thread():
    while True:
        schedule.run_pending()
        time.sleep(1)


# # Start the job thread
thread = threading.Thread(target=job_thread)
thread.daemon = True  # Set the thread as a daemon
thread.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
