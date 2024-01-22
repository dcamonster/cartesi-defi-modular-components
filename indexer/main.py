import requests
import graphene
from db import (
    create_last_cursor_table,
    get_connection,
    get_last_cursor,
    set_last_cursor,
)
import uvicorn
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from resolvers import Query
from starlette.middleware import Middleware
from starlette.applications import Starlette
from starlette_graphene3 import GraphQLApp, make_graphiql_handler

import sys

sys.path.append("../dapp")
from dapp.core import handle_action
from dapp.util import hex_to_str

import schedule
import time
import threading
import json

load_dotenv()


middleware = [
    Middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
]

schema = graphene.Schema(query=Query)
app = Starlette(middleware=middleware)

app.mount("/", GraphQLApp(schema, on_get=make_graphiql_handler()))  # Graphiql IDE


# Initialise the last cursor tables if it doesn't exist
create_last_cursor_table()

GRAPHQL_API = "http://host.docker.internal:4000/graphql"

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
