import { ZeroAddress, ethers } from "ethers";
import database from "./db";
import {
  deployErc20,
  erc20PortalDeposit,
  executeStreamTests,
  measureExecutionTime,
  mintErc20,
  stream
} from "./utils";

async function main() {
  const connection = await database();

  const args = process.argv;
  const streamNumberIndex = args.findIndex((arg) => arg === "--streamNumber");
  let streamNumber = 0;
  if (streamNumberIndex === -1) {
    streamNumber = 25_000;
  } else {
    streamNumber = parseInt(args[streamNumberIndex + 1]);
  }
  console.log("Test with", streamNumber, "consecutive streams")

  console.log("Running benchmark tests on", connection.name);

  let tokenAddress: string = "";
  if (!tokenAddress) {
    tokenAddress = await deployErc20("test", "test");

    await mintErc20(tokenAddress, ethers.parseEther("100").toString());

    // Deposit 100 tokens to the portal
    const depositDuration = await measureExecutionTime(connection, () =>
      erc20PortalDeposit(tokenAddress, ethers.parseEther("100").toString())
    );
    console.log("Deposit duration:", depositDuration);
  }

  // Stream test
  const addTestStreamsDuration = await executeStreamTests(connection, tokenAddress, streamNumber, ethers.parseEther("1"));

  console.log(
    "Added ",
    streamNumber,
    "streams in",
    addTestStreamsDuration,
    "ms"
  );

  const streamDuration = await measureExecutionTime(connection, () =>
    stream(tokenAddress, ZeroAddress, ethers.parseEther("1"), 3600, 0)
  );
  console.log(
    "Adding a new stream takes: ",
    streamDuration,
    "ms with ",
    streamNumber,
    "on-going streams"
  );

  await connection.destroy();
}

main().catch((error) => console.log(error));
