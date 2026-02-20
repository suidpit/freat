import { DataType, dataTypeByteSize } from "./types.js";

// FreezeEntry = { address(8), value(8), last_written(8), size(4), mode(4), data_type(4), pad(4) }
const FREEZE_ENTRY_SIZE = 48;
const MAX_FREEZE_ENTRIES = 64;

const freezeEntries = Memory.alloc(FREEZE_ENTRY_SIZE * MAX_FREEZE_ENTRIES);
const freezeEntryCount = Memory.alloc(4);
const freezeRunning = Memory.alloc(4);
const freezeThread = Memory.alloc(Process.pointerSize);
const freezeMutex = Memory.alloc(16);
freezeEntryCount.writeInt(0);
freezeRunning.writeInt(0);
freezeThread.writePointer(ptr(0));
freezeMutex.writePointer(ptr(0));

const cFreezerCode: string = "__FREEZER_C_MODULE_PLACEHOLDER__";
(globalThis as any).freezerCm = new CModule(cFreezerCode, {
  entries: freezeEntries,
  entry_count: freezeEntryCount,
  running: freezeRunning,
  freeze_thread: freezeThread,
  freeze_mutex: freezeMutex,
});
const freezerCm = (globalThis as any).freezerCm;

const native_freeze_start = new NativeFunction(
  freezerCm.freeze_start,
  "void",
  [],
);
const native_freeze_stop = new NativeFunction(
  freezerCm.freeze_stop,
  "void",
  [],
);
const native_freeze_add = new NativeFunction(freezerCm.freeze_add, "void", [
  "pointer", // address
  "pointer", // value_ptr
  "uint32", // size
  "uint32", // mode
  "uint32", // data_type
]);
const native_freeze_remove = new NativeFunction(
  freezerCm.freeze_remove,
  "void",
  [
    "pointer", // address
  ],
);
const native_freeze_clear = new NativeFunction(
  freezerCm.freeze_clear,
  "void",
  [],
);

const freezeValueBuf = Memory.alloc(8);
let freezeThreadStarted = false;

export function addFreeze(
  address: string,
  value: any,
  dataType: DataType,
  mode: number = 0,
): void {
  if (!freezeThreadStarted) {
    native_freeze_start();
    freezeThreadStarted = true;
  }
  const p = ptr(address);
  const size = dataTypeByteSize(dataType);
  writeValue(freezeValueBuf, value, dataType);
  native_freeze_add(p, freezeValueBuf, size, mode, dataType);
}

export function removeFreeze(address: string): void {
  native_freeze_remove(ptr(address));
}

export function clearFreezeList(): void {
  native_freeze_clear();
}

export function writeValue(
  address: NativePointer,
  value: number | UInt64,
  dataType: DataType,
): void {
  switch (dataType) {
    case DataType.U8:
      address.writeU8(value);
      break;
    case DataType.U16:
      address.writeU16(value);
      break;
    case DataType.U32:
      address.writeU32(value);
      break;
    case DataType.U64:
      address.writeU64(value);
      break;
    case DataType.FLOAT:
      if (typeof value !== "number") throw new Error("Invalid value type");
      address.writeFloat(value);
      break;
    case DataType.DOUBLE:
      if (typeof value !== "number") throw new Error("Invalid value type");
      address.writeDouble(value);
      break;
  }
}

export function readValue(
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

export function readBatch(addresses: [string, DataType][]): {
  [key: string]: any;
} {
  const results: { [key: string]: any } = {};
  for (const [address, dataType] of addresses) {
    try {
      results[address] = readValue(ptr(address), dataType);
    } catch (error) {
      console.error(`Error reading address ${address}: ${error}`);
    }
  }
  return results;
}

export function writeBatch(writes: [string, any, DataType][]): void {
  for (const [address, value, dataType] of writes) {
    try {
      writeValue(ptr(address), value, dataType);
    } catch (error) {
      console.error(`Error writing to address ${address}: ${error}`);
    }
  }
}
