# Python Streamable Token & AMM for Cartesi Rollups

Made with ❤️ by [DCA.Monster](https://dca.monster) as part of the Cartesi Grant [DCA.Monster: Modular DeFi 2.0 Components for Cartesi](https://governance.cartesi.io/t/dca-monster-modular-defi-2-0-components-for-cartesi/210)


## Introduction

The introduction of StreamableTokens and Automated Market Maker (AMM) on Cartesi represents a significant advancement in blockchain technology. While StreamableTokens enable real-time, continuous transfers of digital assets, our AMM model, adapted from Uniswap V2, introduces a novel approach to token exchanges within the Cartesi ecosystem.

Leveraging Cartesi's rollups, we are not only overcoming computational limitations of traditional blockchain applications but also ushering in innovative DeFi functionalities. Our Python-based solutions for StreamableTokens and AMM are engineered for technical efficiency, adaptability, and seamless integration with decentralized applications (DApps), setting new benchmarks in blockchain technology.

## Core Features of Streamable Tokens

- **Python Standardized Implementation**: Built with Python, focusing on compatibility with the Cartesi rollup platform.
- **Support for Infinite Streams**: Engineered to handle a vast (almost infinite) number of ongoing streams and real-time balance computations.
- **SQLite Database Integration**: Utilizes SQLite database for efficient data management and storage.
- **Description**: A python standardised implementation of a Cartesi Streamable token based on [SuperfluidToken](https://github.com/superfluid-finance/protocol-monorepo/blob/dev/packages/ethereum-contracts/contracts/superfluid/SuperfluidToken.sol) on-steroids that can handle a very high (almost infinite) number of ongoing streams and realtime balances. (See [realtimeBalanceOf](https://github.com/superfluid-finance/protocol-monorepo/blob/4e0833900fa51d2dd82cc1be55d97e43d64451f7/packages/ethereum-contracts/contracts/superfluid/SuperfluidToken.sol#L72C6-L72C6))
  - **Features**:
    - Standardised interface to have high composability with Cartesi DApps
    - Work seamlessly with Cartesi’s InputBox & Vouchers
    - Infinite (or extremely high) open streams that working graciously to allow building more sophisticated applications with them.
    - Utilizes SQLite database for efficient data management and storage.
  - **Benchmarking**:
    - Objective: Performance evaluation with high demand this number should support for a DEX operating at peak demand. Support at least 25,000 simultaneous token streams.
  - **Use Cases**:
    - Programmable transfers (e.g. send X tokens at specific time during X seconds)
    - Subscription Services: Manage ongoing subscription payments.
    - DEX

## Core Features of AMM

-   **Uniswap V2 Base Adaptation**: Incorporates the constant product formula and standard token exchange operations of Uniswap V2.
-   **StreamableToken Integration**: Facilitates advanced stream swaps, leveraging the capabilities of StreamableTokens within AMM.
-   **Optimized for Cartesi Rollups**: Tailored to utilize the computational power of Cartesi, enhancing efficiency and scalability.

-   **Description**: An integrated approach to bringing the Uniswap V2 architecture to the Cartesi platform using Python, focusing on traditional transfer operations from  [Constant Function Market Maker (CFMM)  1](https://en.wikipedia.org/wiki/Constant_function_market_maker). Building on this foundational structure, we further optimize for StreamableTokens, introducing advanced stream swaps that leverage the computational capabilities of the Cartesi Dapp.
    
-   **Features**:
    
    -   **Uniswap V2 Base**:
        -   Adheres to the constant product formula inherent in the Uniswap V2 model.
        -   Facilitates standard token exchange operations.
    -   **StreamableToken Enhancement**:
        -   Seamless integration with StreamableTokens, allowing for advanced stream swaps.
        -   Inherits and builds upon the foundational features of the Uniswap V2 port.
-   **Design**:
    
    -   **Uniswap V2 Base**: Meticulous adaptation of the Uniswap V2 system for Cartesi’s environment.
    -   **StreamableToken Enhancement**: Evolves the Uniswap V2 port on Cartesi, honing in specifically for StreamableTokens’ functionalities.
-   **Use Cases**:
    
    -   **Uniswap V2 Base**:
        -   Decentralized token exchanges on the Cartesi platform.
        -   Enables straightforward token swaps.
    -   **StreamableToken Enhancement**:
        -   Progressive decentralized token swaps incorporating streaming capabilities.
        -   Pioneering DeFi operations that utilize token stream benefits like Dollar-Cost Averaging.

## Key Components

1.  [**StreamableToken**](./dapp/streamabletoken.py): Main class that manages the token streaming logic, including stream creation, balance calculations, and token minting/burning.
2.  [**Stream**](./dapp/stream.py): Represents an individual stream, holding details like start block, duration, amount, and the addresses involved.
3.  [**AMM Module**](./dapp/amm.py)**: Implements the AMM logic, enabling token swaps and liquidity provisions in a decentralized environment.
4.  [**Database Functions**](./dapp/db.py): A set of functions to interact with the SQLite database, managing token, account, and stream data.
5.  [**Dapp**](./dapp/core.py): Example DApp that demonstrates the StreamableToken functionality: minting tokens, creating streams, transferring tokens between accounts and withdrawing tokens from the cartesi rollup.

## Usage

If you want to use the StreamableToken in your python, just copy the [streamabletoken.py](./dapp/streamabletoken.py) file into your project and import it.

To use the  [StreamableToken](./dapp/streamabletoken.py) and [AMM](./dapp/amm.py) in your project, copy the respective Python files into your project and import them as shown below.

```python
from streamabletoken import StreamableToken
from amm import AMM
```

Then you can create a new instance of the StreamableToken class:

```python
token = StreamableToken(sqlite_connection, token_address)
amm = AMM(sqlite_connection)
```

And start using it:

```python
# Mint 100 wei tokens
amt = 100
receiver = "0x..."
token.mint(amt, receiver)

token.transfer(
  receiver=receiver,
  amount=amt,
  duration=3600, # 1 hour
  block_start=current_block+25,
  sender=sender,
  current_block=block_number,
)

...

# Add liquidity to the AMM
liquidity = amm.add_liquidity(
    token_a=CTSI_ADDRESS,
    token_b=USDC_ADDRESS,
    token_a_desired=ctsi_lp_amount,
    token_b_desired=usdc_lp_amount,
    token_a_min=ctsi_lp_amount,
    token_b_min=usdc_lp_amount,
    to=ALICE_ADDRESS,
    msg_sender=ALICE_ADDRESS,
    current_timestamp=current_timestamp
)

...

# Stream swap in the AMM
amm.swap_exact_tokens_for_tokens(
            amount_in=bob_swap_amt,
            amount_out_min=0,
            path=[USDC_ADDRESS,CTSI_ADDRESS],
            start=swap_start_trader,
            duration=swap_duration,
            to=BOB_ADDRESS,
            msg_sender=BOB_ADDRESS,
            current_timestamp=current_timestamp,
        )

```

## Simulation

A Notebook is set up to demonstrate the usage of Streamable Tokens and AMM. Follow the instructions in the `Simulation.ipynb` file after running the notebook server using Docker.

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

We have established a benchmarking script to evaluate the performance of the Streamable Token implementation. This script is configured to generate a pre-defined number of streams and is tasked with calculating the time required to integrate a new stream. Adding this new stream necessitates iterating over all active streams to verify the available balance prior to the addition of the new stream and this is what the benchmarking script measures.

To facilitate this, a new column has been introduced in the Input, Report, and Notice tables within the rollup PostgreSQL database. This addition aims to precisely time each new data insertion. See the docker-compose specific section of the [docker-compose.yml](https://github.com/dcamonster/cartesi-defi-modular-components/blob/master/docker-compose.yml#L251) file for more details.

Subsequently, the duration of a specific operation within the rollup is determined by comparing the timestamps of the most recent input and report.

Further details about the benchmarking script are available in the [benchmark folder](./benchmark)

To execute the benchmarking script, the following commands are required:

```bash
cd benchmark
yarn install
yarn start --streamNumber 25000 # or any other number of streams
```

By default, the benchmark tests 25,000 simultaneous streams, aligning with the intended benchmarking objective. However, this number can be modified by passing the `--streamNumber` flag.

Results running the Dapp in production mode:

| Test Run | Number of Simulateneous Streams | Time to Integrate New Stream (s) | Notes                                  |
| -------- | ------------------------------- | -------------------------------- | -------------------------------------- |
| 1        | 25,000                          | 3005 ms                          | 25k simultaneous streams goal achieved |
| 2        | 100,000                         | 3005 ms                          |                                        |
| 3        | 500,000                         | 3004 ms                          |                                        |
| 4        | 1,000,000                       | 3005 ms                          |                                        |
| 5        | 5,000,000                       | 3004 ms                          |                                        |
| 6        | 10,000,000                      | 3006 ms                          |                                        |

The benchmarking results indicate a consistent and robust performance of the Streamable Token implementation, as seen in the time taken to integrate new streams in a complex system with varying numbers of simultaneous streams. Notably, the time to integrate a new stream remains constant at approximately 3005 milliseconds, regardless of the number of streams, ranging from 25,000 to 10,000,000. This consistency suggests excellent scalability and efficiency in handling large-scale operations within the system. The implementation effectively maintains its performance even as the scale of operations increases significantly.

### Setting Up

Ensure you have Docker and Docker Compose installed on your machine. Check the Cartesi requirements documentation for more details [here](https://docs.cartesi.io/cartesi-rollups/build-dapps/requirements/).

### Running the Application

You can build the application in host mode for development purposes using the following command:

#### Host Mode

In one terminal run the cartesi rollup stack:

```bash
make host
```

In another terminal run the actual dapp:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
make host-python-debug
```

#### Production Mode

You can also run the application in production mode using the following command.

First build the cartesi machine with:

```bash
make build
```

Then run the cartesi rollup stack:

```bash
make dev
```

**Building for RISC-V Architecture on Linux**

To build Docker images for the RISC-V architecture (`linux/riscv64`) on Linux, you need to prepare your environment for cross-platform builds. Start by running:

`docker run --rm --privileged multiarch/qemu-user-static --reset -p yes` 

This command sets up QEMU user-mode emulation, enabling Docker to emulate the RISC-V architecture, which is crucial for building and running containers across different platforms.

If you face build issues or wish to optimize Docker, consider running `docker builder prune -a` periodically:

This clears unused build cache, solving potential issues from outdated or corrupt layers and freeing disk space. Note that this action will remove all cached layers and may increase subsequent build times, as Docker recreates these layers.

## Testing

Run unit tests using `python -m unittest discover -s tests`. Continuous testing can be achieved with `find . -name '*.py' | entr -c make test`.

## Development and Contributions

Contributions to the project are welcome. Please adhere to the coding standards and guidelines provided in the documentation. Use the provided Docker environment for a consistent development setup.