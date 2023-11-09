import { ZeroAddress, ethers } from "ethers";
import database from "./db";
import {
  deployErc20,
  erc20PortalDeposit,
  measureExecutionTime,
  mintErc20,
  stream,
  streamTest,
} from "./utils";

// Sample function to show ethers working with TypeScript
function showEthersVersion() {
  console.log("Using ethers version:", ethers.version);
}

showEthersVersion();

async function main() {
  const connection = await database();

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
  let streamCount = 0;
  for (let i = 0; i < 100; i++) {
    const step = 1000;
    const streamTestDuration = await measureExecutionTime(connection, () =>
      streamTest(
        tokenAddress,
        ZeroAddress,
        ethers.parseEther("1"),
        3600,
        0,
        step
      )
    );
    streamCount += step;

    const streamDuration = await measureExecutionTime(connection, () =>
      stream(tokenAddress, ZeroAddress, ethers.parseEther("1"), 3600, 0)
    );
    console.log(
      "Adding a new stream takes: ",
      streamDuration,
      "ms with ",
      streamCount,
      "on-going streams"
    );
  }

  await connection.destroy();
}

main().catch((error) => console.log(error));
