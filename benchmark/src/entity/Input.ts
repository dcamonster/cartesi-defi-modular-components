import { Entity, PrimaryGeneratedColumn, Column } from "typeorm";

@Entity("inputs")
export class Input {
  @PrimaryGeneratedColumn()
  index: number;

  @Column("bytea")
  msg_sender: Buffer;

  @Column("bytea")
  tx_hash: Buffer;

  @Column("bigint")
  block_number: number;

  @Column("timestamp")
  timestamp: Date;

  @Column("bytea")
  payload: Buffer;

  @Column("bigint", { nullable: true })
  time?: number;
}
