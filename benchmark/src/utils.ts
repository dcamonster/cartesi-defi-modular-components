import { ZeroAddress, ethers, parseUnits } from "ethers";

import {
  ICartesiDApp__factory,
  IERC20Portal__factory,
  IInputBox__factory,
} from "@cartesi/rollups";
import { erc20MintableABI, erc20MintableByteCode } from "./erc20Mintable";

import ERC20Portal from "../../deployments/localhost/ERC20Portal.json";
import Dapp from "../../deployments/localhost/dapp.json";
import InputBox from "../../deployments/localhost/InputBox.json";
import { Connection, MoreThan } from "typeorm";
import { Input } from "./entity/Input";
import { Notice } from "./entity/Notice";
import { Report } from "./entity/Report";
import { token } from "@cartesi/rollups/dist/src/types/@openzeppelin/contracts";

const hexlify = (text: string) =>
  ethers.hexlify(ethers.toUtf8Bytes(text)) as `0x${string}`;

export const getUnrawpBody = (token: string, amount: bigint): `0x${string}` =>
  hexlify(
    JSON.stringify({
      method: "unwrap",
      args: { token, amount: amount.toString() },
    })
  );

export const getSwapBody = (
  amountIn: bigint,
  amountOutMin: bigint,
  path: [string, string],
  duration: number,
  start: number,
  to: string
): `0x${string}` =>
  hexlify(
    JSON.stringify({
      method: "swap",
      args: {
        amount_in: amountIn.toString(),
        amount_out_min: amountOutMin.toString(),
        path,
        duration,
        start,
        to,
      },
    })
  );

export const getStreamBody = (
  token: string,
  receiver: string,
  amount: bigint,
  duration: number,
  start: number
): `0x${string}` =>
  hexlify(
    JSON.stringify({
      method: "stream",
      args: {
        token,
        receiver: receiver,
        amount: amount.toString(),
        duration,
        start,
      },
    })
  );

export const getStreamTestBody = (
  token: string,
  receiver: string,
  amount: bigint,
  duration: number,
  start: number,
  split_number: number
): `0x${string}` =>
  hexlify(
    JSON.stringify({
      method: "stream_test",
      args: {
        token,
        receiver: receiver,
        amount: amount.toString(),
        duration,
        start,
        split_number,
      },
    })
  );

export const getAddLiquidityBody = (
  token_a: string,
  token_b: string,
  token_a_desired: bigint,
  token_b_desired: bigint,
  token_a_min: bigint,
  token_b_min: bigint,
  to: string
): `0x${string}` =>
  hexlify(
    JSON.stringify({
      method: "add_liquidity",
      args: {
        token_a,
        token_b,
        token_a_desired: token_a_desired.toString(),
        token_b_desired: token_b_desired.toString(),
        token_a_min: token_a_min.toString(),
        token_b_min: token_b_min.toString(),
        to,
      },
    })
  );

export const getRemoveLiquidityBody = (
  token_a: string,
  token_b: string,
  liquidity: bigint,
  amount_a_min: bigint,
  amount_b_min: bigint,
  to: string
): `0x${string}` =>
  hexlify(
    JSON.stringify({
      method: "remove_liquidity",
      args: {
        token_a,
        token_b,
        liquidity: liquidity.toString(),
        amount_a_min: amount_a_min.toString(),
        amount_b_min: amount_b_min.toString(),
        to,
      },
    })
  );

export const getCancelBody = (
  token: string,
  parent_id?: string,
  stream_id?: string
): `0x${string}` =>
  hexlify(
    JSON.stringify({
      method: "cancel_stream",
      args: {
        token,
        parent_id,
        stream_id,
      },
    })
  );

export const deployErc20 = async (
  name: string,
  symbol: string
): Promise<string> => {
  const provider = new ethers.JsonRpcProvider("http://localhost:8545");

  // Replace with your local node's first account private key for deploying the contract
  const privateKey =
    "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
  const wallet = new ethers.Wallet(privateKey, provider);

  const contractFactory = new ethers.ContractFactory(
    erc20MintableABI,
    erc20MintableByteCode,
    wallet
  );

  // If your ERC20 constructor needs arguments, pass them in the deploy function
  const contract = await contractFactory.deploy(name, symbol);

  await contract.waitForDeployment();
  const address = await contract.getAddress();
  console.log("Contract deployed to address:", address);

  return address;
};

export const mintErc20 = async (
  tokenAddress: string,
  amount: string
): Promise<void> => {
  const provider = new ethers.JsonRpcProvider("http://localhost:8545");

  // Replace with your local node's first account private key for deploying the contract
  const privateKey =
    "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
  const wallet = new ethers.Wallet(privateKey, provider);

  const contract = new ethers.Contract(tokenAddress, erc20MintableABI, wallet);

  const tx = await contract.mint(wallet.address, amount);
  await tx.wait();
  console.log("Minted", amount, "tokens to", wallet.address);
};

export const approveErc20 = async (
  tokenAddress: string,
  amount: string,
  spender: string
): Promise<void> => {
  const provider = new ethers.JsonRpcProvider("http://localhost:8545");

  // Replace with your local node's first account private key for deploying the contract
  const privateKey =
    "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
  const wallet = new ethers.Wallet(privateKey, provider);

  const contract = new ethers.Contract(tokenAddress, erc20MintableABI, wallet);

  const tx = await contract.approve(spender, amount);
  await tx.wait();
  console.log("Approved", amount, "tokens to", spender);
};

export const erc20PortalDeposit = async (
  tokenAddress: string,
  amount: string
): Promise<void> => {
  const provider = new ethers.JsonRpcProvider("http://localhost:8545");

  await approveErc20(tokenAddress, amount, ERC20Portal.address);

  // Replace with your local node's first account private key for deploying the contract
  const privateKey =
    "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
  const wallet = new ethers.Wallet(privateKey, provider);

  const contract = new ethers.Contract(
    ERC20Portal.address,
    ERC20Portal.abi,
    wallet
  );

  const tx = await contract.depositERC20Tokens(
    tokenAddress,
    Dapp.address,
    amount,
    "0x00"
  );
  await tx.wait();
  console.log("Deposited", amount, "tokens to", ERC20Portal.address);
};

export const inputBoxAddInput = async (payload: string): Promise<void> => {
  const provider = new ethers.JsonRpcProvider("http://localhost:8545");

  // Replace with your local node's first account private key for deploying the contract
  const privateKey =
    "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
  const wallet = new ethers.Wallet(privateKey, provider);

  const nonce = await provider.getTransactionCount(wallet.address, "pending");

  const contract = new ethers.Contract(InputBox.address, InputBox.abi, wallet);

  const tx = await contract.addInput(Dapp.address, payload, { nonce });
  await tx.wait();
  console.log("Input added to", InputBox.address);
};

export const stream = async (
  token: string,
  receiver: string,
  amount: bigint,
  duration: number,
  start: number
): Promise<void> => {
  inputBoxAddInput(getStreamBody(token, receiver, amount, duration, start));
};

export const streamTest = async (
  token: string,
  receiver: string,
  amount: bigint,
  duration: number,
  start: number,
  split_number: number
): Promise<void> => {
  inputBoxAddInput(
    getStreamTestBody(token, receiver, amount, duration, start, split_number)
  );
};

export const getLastNoticeTimestamp = async (connection: Connection) => {
  const noticesRepo = connection.getRepository(Notice);

  const notices = await noticesRepo.find({
    order: {
      time: "DESC",
    },
    take: 1,
  });

  return notices[0]?.time ?? 0;
};

export const getLastReportTimestamp = async (connection: Connection) => {
  const reportsRepo = connection.getRepository(Report);

  const reports = await reportsRepo.find({
    order: {
      time: "DESC",
    },
    take: 1,
  });

  return reports[0]?.time ?? 0;
};

export const getLastInputTimestamp = async (connection: Connection) => {
  const inputRepo = connection.getRepository(Input);

  const inputs = await inputRepo.find({
    order: {
      time: "DESC",
    },
    take: 1,
  });

  return inputs[0]?.time ?? 0;
};

export const getLastActionDuration = async (connection: Connection) => {
  const lastReportTimestamp = await getLastReportTimestamp(connection);
  const lastInputTimestamp = await getLastInputTimestamp(connection);

  return lastReportTimestamp - lastInputTimestamp;
};

export const waitForNewNotice = async (
  connection: Connection,
  lastNoticeTimestamp: number
) => {
  const noticesRepo = connection.getRepository(Notice);

  let notice = await noticesRepo.findOne({
    where: {
      time: MoreThan(lastNoticeTimestamp),
    },
    order: {
      time: "ASC",
    },
  });

  while (!notice) {
    notice = await noticesRepo.findOne({
      where: {
        time: MoreThan(lastNoticeTimestamp),
      },
      order: {
        time: "ASC",
      },
    });
  }

  return notice;
};

export const waitForNewReport = async (
  connection: Connection,
  lastReportTimestamp: number
) => {
  const reportsRepo = connection.getRepository(Report);

  let report = await reportsRepo.findOne({
    where: {
      time: MoreThan(lastReportTimestamp),
    },
    order: {
      time: "ASC",
    },
  });

  while (!report) {
    report = await reportsRepo.findOne({
      where: {
        time: MoreThan(lastReportTimestamp),
      },
      order: {
        time: "ASC",
      },
    });
  }

  return report;
};

export async function measureExecutionTime(
  connection: Connection,
  fn: () => Promise<void>
): Promise<number> {
  const lastReportTimestamp = await getLastReportTimestamp(connection);
  await fn();
  await waitForNewReport(connection, lastReportTimestamp);
  return await getLastActionDuration(connection);
}
