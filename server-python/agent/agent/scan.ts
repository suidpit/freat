import { log } from "./logger.js";
import { readValue, writeValue } from "./memory.js";
import { DataType } from "./types.js";

export enum ScanType {
  EXACT,
  LESS_THAN,
  GREATER_THAN,
  INCREASED,
  DECREASED,
}

// C code expects integer enums for ScanSize, so we convert DataType strings to integers
const onMessageCallback = new NativeCallback(
  (messagePtr) => {
    const message = messagePtr!.readUtf8String();
    console.log("tinycc_land:", message);
  },
  "void",
  ["pointer"],
);

let currentScanResults: {
  ptr: NativePointer;
  count: number;
  valuesPtr: NativePointer;
}[] = [];
let currentDataType: DataType = DataType.U32;
const cScannerCode: string = "__C_MODULE_PLACEHOLDER__";
(globalThis as any).cm = new CModule(cScannerCode, {
  onMessage: onMessageCallback,
});
const cm = (globalThis as any).cm;
const scan_region = new NativeFunction(cm.scan_region, "pointer", [
  "pointer", // base_addr
  "uint", // region_size
  "uint", // scan_type
  "uint", // scan_size
  "pointer", // value_ptr
  "pointer", // out_count
  "pointer", // out_values_ptr
]);
const filter_scans = new NativeFunction(cm.filter_scans, "pointer", [
  "pointer", // prev_results
  "uint", // prev_count
  "uint", // scan_type
  "uint", // scan_size
  "pointer", // value_ptr
  "pointer", // prev_values
  "pointer", // out_count
  "pointer", // out_values_ptr
]);
const find_address_in_results = new NativeFunction(
  cm.find_address_in_results,
  "bool",
  ["pointer", "uint", "pointer"],
);
const free_results = new NativeFunction(cm.free_results, "void", ["pointer"]);

const outCountPtr = Memory.alloc(Process.pointerSize);
const outValuesPtrPtr = Memory.alloc(Process.pointerSize);
const valuePtr = Memory.alloc(8);

function dataTypeByteSize(dt: DataType): number {
  switch (dt) {
    case DataType.U8:
      return 1;
    case DataType.U16:
      return 2;
    case DataType.U32:
      return 4;
    case DataType.U64:
      return 8;
    case DataType.FLOAT:
      return 4;
    case DataType.DOUBLE:
      return 8;
    default:
      return 4;
  }
}

export function getCount(): number {
  return currentScanResults.reduce((acc, { count }) => acc + count, 0);
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
  const totalRegions = ranges.length;
  writeValue(valuePtr, value, dataType);
  log(`value written at ${valuePtr}: ${valuePtr.readU32()}`);
  for (let i = 0; i < ranges.length; i++) {
    const range = ranges[i];
    try {
      const resultsPtr = scan_region(
        range.base,
        range.size,
        scanType,
        dataType,
        valuePtr,
        outCountPtr,
        outValuesPtrPtr,
      );

      const count = outCountPtr.readU64().toNumber();
      const valuesPtr = outValuesPtrPtr.readPointer();

      if (count > 0 && !resultsPtr.isNull()) {
        currentScanResults.push({ ptr: resultsPtr, count, valuesPtr });
      } else {
        free_results(resultsPtr);
        free_results(valuesPtr);
      }
    } catch (error) {
      console.error(
        `Error scanning range ${range.base} - ${range.base.add(range.size)}: ${error}`,
      );
    }
    send({ type: "scan-progress", current: i + 1, total: totalRegions });
  }
  return getCount();
}

export function nextScan(value: UInt64 | number, scanType: ScanType): number {
  log(`nextScan(${value}, ${currentDataType}, ${scanType})`);
  if (currentScanResults.length === 0) {
    console.warn("No previous scan results found");
    return 0;
  }
  const newResults: { ptr: NativePointer; count: number; valuesPtr: NativePointer }[] = [];
  const totalResultSets = currentScanResults.length;
  for (let i = 0; i < currentScanResults.length; i++) {
    const { ptr, count, valuesPtr } = currentScanResults[i];
    try {
      writeValue(valuePtr, value, currentDataType);
      const newResultsPtr = filter_scans(
        ptr,
        count,
        scanType,
        currentDataType,
        valuePtr,
        valuesPtr,
        outCountPtr,
        outValuesPtrPtr,
      );
      const newCount = outCountPtr.readU64().toNumber();
      const newValuesPtr = outValuesPtrPtr.readPointer();
      free_results(ptr);
      free_results(valuesPtr);
      if (newCount > 0 && !newResultsPtr.isNull()) {
        newResults.push({ ptr: newResultsPtr, count: newCount, valuesPtr: newValuesPtr });
      } else {
        free_results(newResultsPtr);
        free_results(newValuesPtr);
      }
    } catch (error) {
      console.error(`Error filtering results in ${ptr} (#${count})`, error);
    }
    send({ type: "scan-progress", current: i + 1, total: totalResultSets });
  }
  currentScanResults = newResults;
  return getCount();
}

export function undoScan() {
  currentScanResults = [];
}

export function getScanResults(maxResults: number = 100): {
  address: string;
  value: number | UInt64;
  previousValue: number | UInt64;
}[] {
  const results: { address: string; value: number | UInt64; previousValue: number | UInt64 }[] = [];
  let addedResults = 0;
  const elemSize = dataTypeByteSize(currentDataType);
  for (const { ptr, count, valuesPtr } of currentScanResults) {
    for (let i = 0; i < count; i++) {
      const address = ptr.add(i * Process.pointerSize).readPointer();
      const value = readValue(address, currentDataType);
      const previousValue = readValue(valuesPtr.add(i * elemSize), currentDataType);
      results.push({
        address: address.toString(),
        value,
        previousValue,
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
  const range = Process.enumerateRanges("rw-")[0];

  // Test 1: EXACT scan with U32
  const secret = new UInt64("0xdeadbeefcafebabe");
  range.base.writeU64(secret);
  firstScan(0xcafebabe, DataType.U32, ScanType.EXACT);
  if (!checkAddrInResults(range.base)) {
    console.error("Test 1 failed: expected U32 result not found in first scan");
    return false;
  }

  // Test 2: EXACT scan with U64
  firstScan(secret, DataType.U64, ScanType.EXACT);
  if (!checkAddrInResults(range.base)) {
    console.error("Test 2 failed: expected result not found in first scan");
    return false;
  }

  // Test 3: EXACT next scan
  const newSecret = new UInt64("0xcafebabedeadbeef");
  range.base.writeU64(newSecret);
  range.base.add(8).writeU64(newSecret);
  nextScan(newSecret, ScanType.EXACT);
  if (!checkAddrInResults(range.base)) {
    console.error("Test 3 failed: previous address not found in next scan");
    return false;
  }
  if (checkAddrInResults(range.base.add(8))) {
    console.error("Test 3 failed: unexpected address found in next scan");
    return false;
  }

  // Test 4: getScanResults returns correct address
  const scanResults = getScanResults();
  if (range.base.toString() != scanResults[0].address) {
    console.error("Test 4 failed: expected result not found in scan results");
    return false;
  }

  // Test 5: LESS_THAN scan
  range.base.writeU32(100);
  range.base.add(4).writeU32(50);
  range.base.add(8).writeU32(200);
  firstScan(150, DataType.U32, ScanType.LESS_THAN);
  if (!checkAddrInResults(range.base)) {
    console.error("Test 5 failed: value 100 should be < 150");
    return false;
  }
  if (!checkAddrInResults(range.base.add(4))) {
    console.error("Test 5 failed: value 50 should be < 150");
    return false;
  }
  if (checkAddrInResults(range.base.add(8))) {
    console.error("Test 5 failed: value 200 should NOT be < 150");
    return false;
  }

  // Test 6: LESS_THAN next scan (edge case: exact boundary)
  nextScan(100, ScanType.LESS_THAN);
  if (!checkAddrInResults(range.base.add(4))) {
    console.error("Test 6 failed: value 50 should be < 100");
    return false;
  }
  if (checkAddrInResults(range.base)) {
    console.error("Test 6 failed: value 100 should NOT be < 100 (boundary)");
    return false;
  }

  // Test 7: GREATER_THAN scan
  range.base.writeU32(100);
  range.base.add(4).writeU32(50);
  range.base.add(8).writeU32(200);
  firstScan(75, DataType.U32, ScanType.GREATER_THAN);
  if (!checkAddrInResults(range.base)) {
    console.error("Test 7 failed: value 100 should be > 75");
    return false;
  }
  if (checkAddrInResults(range.base.add(4))) {
    console.error("Test 7 failed: value 50 should NOT be > 75");
    return false;
  }
  if (!checkAddrInResults(range.base.add(8))) {
    console.error("Test 7 failed: value 200 should be > 75");
    return false;
  }

  // Test 8: GREATER_THAN next scan (edge case: zero)
  range.base.writeU32(0);
  range.base.add(4).writeU32(1);
  firstScan(0, DataType.U32, ScanType.GREATER_THAN);
  if (checkAddrInResults(range.base)) {
    console.error("Test 8 failed: value 0 should NOT be > 0");
    return false;
  }
  if (!checkAddrInResults(range.base.add(4))) {
    console.error("Test 8 failed: value 1 should be > 0");
    return false;
  }

  // Test 9: GREATER_THAN with negative-like values (U32 overflow edge case)
  range.base.writeU32(0xffffffff); // Max U32
  range.base.add(4).writeU32(0xfffffffe);
  firstScan(0xfffffffe, DataType.U32, ScanType.GREATER_THAN);
  if (!checkAddrInResults(range.base)) {
    console.error("Test 9 failed: 0xFFFFFFFF should be > 0xFFFFFFFE");
    return false;
  }
  if (checkAddrInResults(range.base.add(4))) {
    console.error("Test 9 failed: 0xFFFFFFFE should NOT be > 0xFFFFFFFE");
    return false;
  }

  // Test 10: INCREASED scan
  range.base.writeU32(100);
  range.base.add(4).writeU32(200);
  range.base.add(8).writeU32(300);
  firstScan(0, DataType.U32, ScanType.GREATER_THAN); // baseline: captures values 100, 200, 300
  // Now increase some values
  range.base.writeU32(150);       // 100 -> 150 (increased)
  range.base.add(4).writeU32(200); // 200 -> 200 (unchanged)
  range.base.add(8).writeU32(250); // 300 -> 250 (decreased)
  nextScan(0, ScanType.INCREASED);
  if (!checkAddrInResults(range.base)) {
    console.error("Test 10 failed: value 100->150 should be INCREASED");
    return false;
  }
  if (checkAddrInResults(range.base.add(4))) {
    console.error("Test 10 failed: value 200->200 should NOT be INCREASED");
    return false;
  }
  if (checkAddrInResults(range.base.add(8))) {
    console.error("Test 10 failed: value 300->250 should NOT be INCREASED");
    return false;
  }

  // Test 11: DECREASED scan
  range.base.writeU32(100);
  range.base.add(4).writeU32(200);
  range.base.add(8).writeU32(300);
  firstScan(0, DataType.U32, ScanType.GREATER_THAN); // baseline
  range.base.writeU32(50);        // 100 -> 50 (decreased)
  range.base.add(4).writeU32(200); // 200 -> 200 (unchanged)
  range.base.add(8).writeU32(350); // 300 -> 350 (increased)
  nextScan(0, ScanType.DECREASED);
  if (!checkAddrInResults(range.base)) {
    console.error("Test 11 failed: value 100->50 should be DECREASED");
    return false;
  }
  if (checkAddrInResults(range.base.add(4))) {
    console.error("Test 11 failed: value 200->200 should NOT be DECREASED");
    return false;
  }
  if (checkAddrInResults(range.base.add(8))) {
    console.error("Test 11 failed: value 300->350 should NOT be DECREASED");
    return false;
  }

  console.log("All scan tests passed!");
  return true;
}
