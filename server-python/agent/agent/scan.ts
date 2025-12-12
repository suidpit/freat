import { log } from "./logger.js";
import { DataType } from "./types.js";

export enum ScanType {
  EXACT,
  LESS_THAN,
  GREATER_THAN,
}

// C code expects integer enums for ScanSize, so we convert DataType strings to integers
enum CScanSize {
  U8 = 0,
  U16 = 1,
  U32 = 2,
  U64 = 3,
  FLOAT = 4,
  DOUBLE = 5,
}

function dataTypeToCScanSize(dataType: DataType): CScanSize {
  switch (dataType) {
    case DataType.U8:
      return CScanSize.U8;
    case DataType.U16:
      return CScanSize.U16;
    case DataType.U32:
      return CScanSize.U32;
    case DataType.U64:
      return CScanSize.U64;
    case DataType.FLOAT:
      return CScanSize.FLOAT;
    case DataType.DOUBLE:
      return CScanSize.DOUBLE;
    default:
      throw new Error(`Unsupported data type for C scan: ${dataType}`);
  }
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
let currentDataType: DataType = DataType.U32;
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
  dataType: DataType,
): NativePointer {
  switch (dataType) {
    case DataType.U8:
      valuePtr.writeU8(value);
      break;
    case DataType.U16:
      valuePtr.writeU16(value);
      break;
    case DataType.U32:
      valuePtr.writeU32(value);
      break;
    case DataType.U64:
      valuePtr.writeU64(value);
      break;
    case DataType.FLOAT:
      if (typeof value !== "number") throw new Error("Invalid value type");
      valuePtr.writeFloat(value);
      break;
    case DataType.DOUBLE:
      if (typeof value !== "number") throw new Error("Invalid value type");
      valuePtr.writeDouble(value);
      break;
  }
  return valuePtr;
}

function _readValue(
  address: NativePointer,
  dataType: DataType,
): number | UInt64 {
  switch (dataType) {
    case DataType.U8:
      return address.readU8();
    case DataType.U16:
      return address.readU16();
    case DataType.U32:
      return address.readU32();
    case DataType.U64:
      return address.readU64();
    case DataType.FLOAT:
      return address.readFloat();
    case DataType.DOUBLE:
      return address.readDouble();
    default:
      throw new Error(`Unsupported data type: ${dataType}`);
  }
}

function checkAddrInResults(addr: NativePointer): boolean {
  for (const { ptr, count } of currentScanResults) {
    if (find_address_in_results(ptr, count, addr)) return true;
  }
  return false;
}

export function firstScan(
  value: UInt64 | number,
  dataType: DataType,
  scanType: ScanType,
): number {
  log(`firstScan(${value}, ${dataType}, ${scanType})`);
  currentScanResults = [];
  currentDataType = dataType;
  const ranges = Process.enumerateRanges("rw-");
  _writeValue(value, dataType);
  log(`value written at ${valuePtr}: ${valuePtr.readU32()}`);
  const cScanSize = dataTypeToCScanSize(dataType);
  for (const range of ranges) {
    try {
      const resultsPtr = scan_region(
        range.base,
        range.size,
        scanType,
        cScanSize,
        valuePtr,
        outCountPtr,
      );

      const count = outCountPtr.readU64().toNumber();

      if (count > 0 && !resultsPtr.isNull()) {
        currentScanResults.push({ ptr: resultsPtr, count });
      } else {
        free_results(resultsPtr);
      }
    } catch (error) {
      console.error(
        `Error scanning range ${range.base} - ${range.base.add(range.size)}: ${error}`,
      );
    }
  }
  return getCount();
}

export function nextScan(value: UInt64 | number, scanType: ScanType): number {
  log(`nextScan(${value}, ${currentDataType}, ${scanType})`);
  if (currentScanResults.length === 0) {
    console.warn("No previous scan results found");
    return 0;
  }
  const cScanSize = dataTypeToCScanSize(currentDataType);
  const newResults = [];
  for (const { ptr, count } of currentScanResults) {
    try {
      const newResultsPtr = filter_scans(
        ptr,
        count,
        scanType,
        cScanSize,
        _writeValue(value, currentDataType),
        outCountPtr,
      );
      const newCount = outCountPtr.readU64().toNumber();
      free_results(ptr);
      if (newCount > 0 && !newResultsPtr.isNull()) {
        newResults.push({ ptr: newResultsPtr, count: newCount });
      } else {
        free_results(newResultsPtr);
      }
    } catch (error) {
      console.error(`Error filtering results in ${ptr} (#${count})`, error);
    }
  }
  currentScanResults = newResults;
  return getCount();
}

export function undoScan() {
  currentScanResults = [];
}

export function getScanResults(maxResults: number = 100): {
  address: number;
  value: number | UInt64;
}[] {
  const results = [];
  let addedResults = 0;
  for (const { ptr, count } of currentScanResults) {
    for (let i = 0; i < count; i++) {
      const address = ptr.add(i * Process.pointerSize).readPointer();
      const value = _readValue(address, currentDataType);
      results.push({
        address: address.toUInt32(),
        value: value,
      });
      addedResults++;
      if (addedResults >= maxResults) {
        return results;
      }
    }
  }
  return results;
}

export function runScanTest(): boolean {
  const secret = new UInt64("0xdeadbeefcafebabe");
  const range = Process.enumerateRanges("rw-")[0];
  range.base.writeU64(secret);

  firstScan(0xcafebabe, DataType.U32, ScanType.EXACT);
  if (!checkAddrInResults(range.base)) {
    console.error("Scan failed: expected U32 result not found in first scan");
    return false;
  }
  firstScan(secret, DataType.U64, ScanType.EXACT);
  if (!checkAddrInResults(range.base)) {
    console.error("Scan failed: expected result not found in first scan");
    return false;
  }
  const newSecret = new UInt64("0xcafebabedeadbeef");
  range.base.writeU64(newSecret);
  range.base.add(8).writeU64(newSecret);
  nextScan(newSecret, ScanType.EXACT);
  if (!checkAddrInResults(range.base)) {
    console.error("Scan failed: previous address not found in next scan");
    return false;
  }
  if (checkAddrInResults(range.base.add(8))) {
    console.error("Scan failed: unexpected address found in next scan");
    return false;
  }
  const scanResults = getScanResults();
  if (range.base.toUInt32() != scanResults[0].address) {
    console.error("Scan failed: expected result not found in scan results");
    return false;
  }
  return true;
}
