import { log } from "./logger.js";
import { DataType } from "./types.js";
import {
  ScanType,
  firstScan,
  nextScan,
  undoScan,
  getScanResults,
  runScanTest,
} from "./scan.js";
import { readBatch, writeBatch } from "./memory.js";

rpc.exports = {
  hello: (): string => {
    log("hello() was called!");
    return "hello from the agent!";
  },
  firstScan: (
    value: number,
    dataType: DataType,
    scanType: ScanType,
  ): number => {
    return firstScan(value, dataType, scanType);
  },
  nextScan: (value: number, scanType: ScanType): number => {
    return nextScan(value, scanType);
  },
  getScanResults: (
    count: number,
  ): { address: number; value: number | UInt64 }[] => {
    return getScanResults(count);
  },
  undoScan: () => {
    undoScan();
  },
  runScanTest: (): boolean => {
    return runScanTest();
  },
  readBatch: (addresses: [number, DataType][]): { [key: number]: any } => {
    return readBatch(addresses);
  },
  writeBatch: (writes: [number, any, DataType][]): void => {
    return writeBatch(writes);
  },
};
