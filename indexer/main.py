import graphene

# import schedule
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from resolvers import Query
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette_graphene3 import GraphQLApp, make_graphiql_handler

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

schema = graphene.Schema(query=Query)


graphql_app = GraphQLApp(schema=schema)

app = Starlette(middleware=middleware)
# https://github.com/ciscorn/starlette-graphene3#example
schema = graphene.Schema(query=Query)

app.mount("/", GraphQLApp(schema, on_get=make_graphiql_handler()))  # Graphiql IDE


def hex_to_str(hex):
    """Decode a hex string prefixed with "0x" into a UTF-8 string"""
    return bytes.fromhex(hex[2:]).decode("utf-8")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
