import { Connection, createConnection } from "typeorm";
import { PostgresConnectionOptions } from "typeorm/driver/postgres/PostgresConnectionOptions";

// Using environment variables
import dotenv from "dotenv";
import { Notice } from "./entity/Notice";
import { Input } from "./entity/Input";
import { Report } from "./entity/Report";
dotenv.config();

export default async (): Promise<Connection> => {
  const connectionOptions: PostgresConnectionOptions = {
    type: "postgres",
    host: "localhost",
    port: 5432,
    username: "postgres",
    password: "password",
    database: "postgres",
    synchronize: true,
    logging: false,
    entities: [Notice, Report, Input],
  };

  const connection = await createConnection(connectionOptions);

  return connection;
};
