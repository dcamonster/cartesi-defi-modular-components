
# Indexer README

## Overview

The Indexer is designed to index the decentralized application (dApp) state of the Cartesi Machine. It utilizes modern Python technologies, including FastAPI, GraphQL, and SQLite, to efficiently handle and store dApp state changes.

## Features

-   **GraphQL Integration**: Leverages GraphQL for querying data, offering flexibility and efficiency in data retrieval.
-   **Automated Indexing**: Periodically fetches and processes new state updates from the dApp, ensuring the database is always current.
-   **Error Handling**: Includes robust error handling to manage unexpected issues during data processing.

## Installation and Setup

1.  **Environment Setup**: Ensure Python 3 and Docker are installed on your system.
2.  **Clone Repository**: Clone the repository to your local machine.
3.  **Dependency Installation**: Install required Python packages listed in `requirements.txt`.

## Database Initialization

-   Run `make init-db` to initialize the SQLite database, creating or resetting the `indexer.sqlite` file.

## Running the Indexer with Docker

-   **Build the image**: Execute `docker build -t dca-indexer -f Dockerfile-indexer .` from the root directory.
-   **Run the container**: Use `docker run -e NETWORK=sepolia --add-host=host.docker.internal:$(docker network inspect bridge | jq -r '.[0].IPAM.Config[0].Gateway') -d -p 8081:8081 --name dca-indexer dca-indexer`

## Architecture

-   **FastAPI**: Serves as the backend framework, offering a high-performance, easy-to-use interface.
-   **GraphQL**: Used for querying the Cartesi Machine state, providing a flexible and efficient data access layer.
-   **SQLite**: Manages data persistence, storing the indexed state in a reliable and lightweight database.

## Scheduling and Threading

-   The indexer is configured to automatically query for new dApp states every second.
-   A separate daemon thread handles the scheduling and execution of these queries, ensuring non-blocking operation.

## Docker Support

-   Docker is used for setting up and managing the database. Use `docker-compose up db` to start the database service.

## Environment Variables

-   Set appropriate environment variables for network configuration and file paths, as specified in the `Makefile`.

## GraphQL Endpoint

-   The GraphQL API endpoint is accessible at `http://localhost:8081/graphql`.

## GraphiQL IDE

-   The GraphiQL IDE is mounted at the root URL (`/`), providing an interactive interface to test and debug GraphQL queries.