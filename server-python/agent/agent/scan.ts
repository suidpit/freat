import { X509Certificate } from "node:crypto";
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
const free_scan_results = new NativeFunction(cm.free_scan_results, "void", [
  "pointer",
]);

const outCountPtr = Memory.alloc(Process.pointerSize);
const valuePtr = Memory.alloc(8);

export function getCount(): number {
  return currentScanResults.reduce((acc, { count }) => acc + count, 0);
}

function _writeValue(value: number, scanSize: ScanSize): NativePointer {
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
      valuePtr.writeFloat(value);
      break;
    case ScanSize.DOUBLE:
      valuePtr.writeDouble(value);
      break;
  }
  return valuePtr;
}

export function scan(
  value: number,
  scanSize: ScanSize,
  scanType: ScanType,
): number {
  log(`firstScan(${value}, ${scanSize}, ${scanType})`);

  const ranges = Process.enumerateRanges("rw-").concat(
    Process.enumerateMallocRanges(),
  );
  for (const range of ranges) {
    const resultsPtr = scan_region(
      range.base,
      range.size,
      scanType,
      scanSize,
      _writeValue(value, scanSize),
      outCountPtr,
    );

    const count = outCountPtr.readU64().toNumber();

    if (count > 0 && !resultsPtr.isNull()) {
      currentScanResults.push({ ptr: resultsPtr, count });
    } else {
      free_scan_results(resultsPtr);
    }
  }
  return getCount();
}

export function setupScanTest(secretValue: string): NativePointer {
  const range = Process.enumerateRanges("rw-")[0];
  range.base.writeU64(new UInt64(secretValue));
  return range.base;
}
