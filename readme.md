# Python Streamable Token for Cartesi rollups


Made with ❤️ by [DCA.Monster](https://dca.monster) as part of the Cartesi Grant [DCA.Monster: Modular DeFi 2.0 Components for Cartesi](https://governance.cartesi.io/t/dca-monster-modular-defi-2-0-components-for-cartesi/210)
## Introduction

Token streaming represents a significant shift in blockchain technology, enabling the ongoing, real-time transfer of digital assets. This approach diverges from traditional lump-sum transactions by enabling a more fluid and dynamic transfer of tokens. In the DeFi (Decentralized Finance) sector, token streaming is increasingly crucial for use cases requiring regular, continuous payments, such as subscriptions, salary distributions, and rent.

Our Python implementation of Streamable Tokens, particularly optimized for the Cartesi rollup environment, focuses on technical efficiency and flexibility. These tokens are engineered for high composability, allowing for seamless integration across a variety of DApps, including decentralized exchanges (DEXes), money markets, and gaming platforms. This tool is designed to provide developers with a robust framework to explore and implement token streaming functionalities in diverse blockchain applications.

## Core Features

- **Python Standardized Implementation**: Built with Python, focusing on compatibility with the Cartesi rollup platform.
- **Support for Infinite Streams**: Engineered to handle a vast (almost infinite) number of ongoing streams and real-time balance computations.
- **SQLite Database Integration**: Utilizes SQLite database for efficient data management and storage.

-   **Description**: A python standardised implementation of a Cartesi Streamable token based on  [SuperfluidToken](https://github.com/superfluid-finance/protocol-monorepo/blob/dev/packages/ethereum-contracts/contracts/superfluid/SuperfluidToken.sol)  on-steroids that can handle a very high (almost infinite) number of ongoing streams and realtime balances. (See  [realtimeBalanceOf](https://github.com/superfluid-finance/protocol-monorepo/blob/4e0833900fa51d2dd82cc1be55d97e43d64451f7/packages/ethereum-contracts/contracts/superfluid/SuperfluidToken.sol#L72C6-L72C6))
    -   **Features**:
        -   Standardised interface to have high composability with Cartesi DApps
        -   Work seamlessly with Cartesi’s InputBox & Vouchers
        -   Infinite (or extremely high) open streams that working graciously to allow building more sophisticated applications with them.
        -   Utilizes SQLite database for efficient data management and storage.
    -   **Benchmarking**:
        -   Objective: Performance evaluation with high demand this number should support for a DEX operating at peak demand. Support at least 25,000 simultaneous token streams.
    -   **Use Cases**:
        -   Programmable transfers (e.g. send X tokens at specific time during X seconds)
        -   Subscription Services: Manage ongoing subscription payments.
        -   DEX

## Key Components

1.  **StreamableToken Class**: Main class that manages the token streaming logic, including stream creation, balance calculations, and token minting/burning.
2.  **Stream Class**: Represents an individual stream, holding details like start block, duration, amount, and the addresses involved.
3.  **Database Functions**: A set of functions to interact with the SQLite database, managing token, account, and stream data.

## Simulation

We have set up a Notebook to show you how easy it's to use the Streamable tokens and transfer them between accounts.

You just need docker installed and run the following command:

```bash
make notebook
```

And among the output you will see something like:

```bash
[I 2023-11-13 18:22:56.212 ServerApp]     http://127.0.0.1:8888/lab?token=92b7eeb31f49fc54f871597bda570971b96f642476ededdc
```

Just copy the URL and paste it in your browser and you will be able to see the notebook.

Then in the notebook open the file [Simulation.ipynb](./Simulation.ipynb) and follow the instructions.

<img src="./images/notebook.png" alt="Simulation Notebook" style="max-width:1000px; height:auto;">

## Benchmarking

### Setting Up

Ensure you have Python installed and set up the required environment variables, particularly `ROLLUP_HTTP_SERVER_URL` for connecting to the Cartesi rollup server.

### Running the Application

- Use `docker compose up` to start the application in a Docker environment.
- For a more interactive experience, use `docker run -p 8888:8888 ...` to start a Jupyter Notebook and experiment with the code.

### Key Functions

- **Token Streaming**: Create, manage, and cancel token streams.
- **Balance Management**: Calculate and update real-time balances for each account involved in streaming.
- **Database Interactions**: Handle CRUD operations related to tokens, accounts, and streams in the SQLite database.

## Testing

Run unit tests using `python -m unittest discover -s tests`. Continuous testing can be achieved with `find . -name '*.py' | entr -c make test`.

## Development and Contributions

Contributions to the project are welcome. Please adhere to the coding standards and guidelines provided in the documentation. Use the provided Docker environment for a consistent development setup.

## Future Enhancements

Future updates will focus on enhancing scalability, improving integration with other Cartesi DApps, and possibly extending functionality to support new use cases like DeFi protocols and NFT marketplaces.

## Conclusion

This Streamable Token Python implementation for Cartesi is a robust solution for anyone looking to explore or develop applications requiring real-time, continuous token transactions. It stands as a testament to the innovative potential of token streaming in the blockchain space.
