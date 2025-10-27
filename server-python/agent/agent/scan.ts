import { log } from "./logger.js";

export enum ScanSize {
  U8,
  U16,
  U32,
  U64,
  FLOAT,
  DOUBLE,
}

export enum ScanType {
  EXACT,
  LESS_THAN,
  GREATER_THAN,
}

const onMessageCallback = new NativeCallback(
  (messagePtr) => {
    const message = messagePtr!.readUtf8String();
    console.log("tinycc_land:", message);
  },
  "void",
  ["pointer"],
);

let currentScanResults: { ptr: NativePointer; count: number }[] = [];
const cScannerCode: string = "__C_MODULE_PLACEHOLDER__";
(globalThis as any).cm = new CModule(cScannerCode, {
  onMessage: onMessageCallback,
});
const cm = (globalThis as any).cm;
const scan_region = new NativeFunction(cm.scan_region, "pointer", [
  "pointer",
  "uint",
  "uint",
  "uint",
  "pointer",
  "pointer",
]);
const filter_scans = new NativeFunction(cm.filter_scans, "pointer", [
  "pointer",
  "uint",
  "uint",
  "uint",
  "pointer",
  "pointer",
]);
const find_address_in_results = new NativeFunction(
  cm.find_address_in_results,
  "bool",
  ["pointer", "uint", "pointer"],
);
const free_results = new NativeFunction(cm.free_results, "void", ["pointer"]);

const outCountPtr = Memory.alloc(Process.pointerSize);
const valuePtr = Memory.alloc(8);

export function getCount(): number {
  return currentScanResults.reduce((acc, { count }) => acc + count, 0);
}

function _writeValue(
  value: number | UInt64,
  scanSize: ScanSize,
): NativePointer {
  switch (scanSize) {
    case ScanSize.U8:
      valuePtr.writeU8(value);
      break;
    case ScanSize.U16:
      valuePtr.writeU16(value);
      break;
    case ScanSize.U32:
      valuePtr.writeU32(value);
      break;
    case ScanSize.U64:
      valuePtr.writeU64(value);
      break;
    case ScanSize.FLOAT:
      if (typeof value !== "number") throw new Error("Invalid value type");
      valuePtr.writeFloat(value);
      break;
    case ScanSize.DOUBLE:
      if (typeof value !== "number") throw new Error("Invalid value type");
      valuePtr.writeDouble(value);
      break;
  }
  return valuePtr;
}

function checkAddrInResults(addr: NativePointer): boolean {
  for (const { ptr, count } of currentScanResults) {
    if (find_address_in_results(ptr, count, addr)) return true;
  }
  return false;
}

export function firstScan(
  value: UInt64 | number,
  scanSize: ScanSize,
  scanType: ScanType,
): number {
  log(`firstScan(${value}, ${scanSize}, ${scanType})`);
  currentScanResults = [];
  const ranges = Process.enumerateRanges("rw-").concat(
    Process.enumerateMallocRanges(),
  );
  _writeValue(value, scanSize);
  log(`value written at ${valuePtr}: ${valuePtr.readU32()}`);
  for (const range of ranges) {
    const resultsPtr = scan_region(
      range.base,
      range.size,
      scanType,
      scanSize,
      valuePtr,
      outCountPtr,
    );

    const count = outCountPtr.readU64().toNumber();

    if (count > 0 && !resultsPtr.isNull()) {
      currentScanResults.push({ ptr: resultsPtr, count });
    } else {
      free_results(resultsPtr);
    }
  }
  return getCount();
}

export function nextScan(
  value: UInt64 | number,
  scanSize: ScanSize,
  scanType: ScanType,
): number {
  log(`nextScan(${value}, ${scanSize}, ${scanType})`);
  if (currentScanResults.length === 0) {
    console.warn("No previous scan results found");
    return 0;
  }
  const newResults = [];
  for (const { ptr, count } of currentScanResults) {
    const newResultsPtr = filter_scans(
      ptr,
      count,
      scanType,
      scanSize,
      _writeValue(value, scanSize),
      outCountPtr,
    );
    const newCount = outCountPtr.readU64().toNumber();
    free_results(ptr);
    if (newCount > 0 && !newResultsPtr.isNull()) {
      newResults.push({ ptr: newResultsPtr, count: newCount });
    } else {
      free_results(newResultsPtr);
    }
  }
  currentScanResults = newResults;
  return getCount();
}

export function runScanTest(): boolean {
  const secret = new UInt64("0xdeadbeefcafebabe");
  const range = Process.enumerateRanges("rw-")[0];
  range.base.writeU64(secret);

  firstScan(0xcafebabe, ScanSize.U32, ScanType.EXACT);
  if (!checkAddrInResults(range.base)) {
    console.error("Scan failed: expected U32 result not found in first scan");
    return false;
  }
  firstScan(secret, ScanSize.U64, ScanType.EXACT);
  if (!checkAddrInResults(range.base)) {
    console.error("Scan failed: expected result not found in first scan");
    return false;
  }
  const newSecret = new UInt64("0xcafebabedeadbeef");
  range.base.writeU64(newSecret);
  range.base.add(8).writeU64(newSecret);
  nextScan(newSecret, ScanSize.U64, ScanType.EXACT);
  if (!checkAddrInResults(range.base)) {
    console.error("Scan failed: previous address not found in next scan");
    return false;
  }
  if (checkAddrInResults(range.base.add(8))) {
    console.error("Scan failed: unexpected address found in next scan");
    return false;
  }
  return true;
}
