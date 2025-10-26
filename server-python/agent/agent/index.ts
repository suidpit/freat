import { log } from "./logger.js";
import { ScanSize, ScanType, scan, nextScan, runScanTest } from "./scan.js";

rpc.exports = {
  hello: (): string => {
    log("hello() was called!");
    return "hello from the agent!";
  },
  scan: (value: number, scanSize: ScanSize, scanType: ScanType): number => {
    return scan(value, scanSize, scanType);
  },
  nextScan: (value: number, scanSize: ScanSize, scanType: ScanType): number => {
    return nextScan(value, scanSize, scanType);
  },
  runScanTest: (): boolean => {
    return runScanTest();
  },
};
