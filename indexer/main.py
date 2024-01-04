import graphene
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
