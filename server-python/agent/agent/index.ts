import { log } from "./logger.js";
import { ScanType, DataType } from "./types.js";
import {
  firstScan,
  nextScan,
  undoScan,
  getScanResults,
  runScanTest,
} from "./scan.js";
import { readBatch, writeBatch, writeValue } from "./memory.js";

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
  ): { address: string; value: number | UInt64; previousValue: number | UInt64 }[] => {
    return getScanResults(count);
  },
  undoScan: () => {
    undoScan();
  },
  runScanTest: (): boolean => {
    return runScanTest();
  },
  readBatch: (addresses: [string, DataType][]): { [key: string]: any } => {
    return readBatch(addresses);
  },
  writeBatch: (writes: [string, any, DataType][]): void => {
    return writeBatch(writes);
  },
  writeValue: (address: string, value: any, dataType: DataType): void => {
    return writeValue(ptr(address), value, dataType);
  },
};
