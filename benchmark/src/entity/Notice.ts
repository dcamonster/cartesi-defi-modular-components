import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  JoinColumn,
} from "typeorm";
import { Input } from "./Input";

@Entity("notices")
export class Notice {
  @PrimaryGeneratedColumn()
  input_index: number;

  @PrimaryGeneratedColumn()
  index: number;

  @Column("bytea")
  payload: Buffer;

  @Column("bigint", { nullable: true })
  time?: number;
}
