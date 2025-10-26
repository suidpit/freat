import { log } from "./logger.js";
import { ScanSize, ScanType, scan, setupScanTest } from "./scan.js";

rpc.exports = {
  hello: (): string => {
    log("hello() was called!");
    return "hello from the agent!";
  },
  scan: (value: number, scanSize: ScanSize, scanType: ScanType): number => {
    return scan(value, scanSize, scanType);
  },
  setupScanTest: (secret: string): NativePointer => {
    return setupScanTest(secret);
  },
};
