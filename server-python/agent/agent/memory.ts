import { DataType } from "./types.js";

export function writeValue(
  address: number,
  value: number | UInt64,
  dataType: DataType,
): void {
  const targetPtr = ptr(address);
  switch (dataType) {
    case DataType.U8:
      targetPtr.writeU8(value);
      break;
    case DataType.U16:
      targetPtr.writeU16(value);
      break;
    case DataType.U32:
      targetPtr.writeU32(value);
      break;
    case DataType.U64:
      targetPtr.writeU64(value);
      break;
    case DataType.FLOAT:
      if (typeof value !== "number") throw new Error("Invalid value type");
      targetPtr.writeFloat(value);
      break;
    case DataType.DOUBLE:
      if (typeof value !== "number") throw new Error("Invalid value type");
      targetPtr.writeDouble(value);
      break;
  }
}

export function readValue(
  address: number,
  dataType: DataType,
): number | UInt64 {
  const targetPtr = ptr(address);
  switch (dataType) {
    case DataType.U8:
      return targetPtr.readU8();
    case DataType.U16:
      return targetPtr.readU16();
    case DataType.U32:
      return targetPtr.readU32();
    case DataType.U64:
      return targetPtr.readU64();
    case DataType.FLOAT:
      return targetPtr.readFloat();
    case DataType.DOUBLE:
      return targetPtr.readDouble();
    default:
      throw new Error(`Unsupported data type: ${dataType}`);
  }
}

export function readBatch(
  addresses: [number, DataType][],
): { [key: number]: any } {
  const results: { [key: number]: any } = {};
  for (const [address, dataType] of addresses) {
    try {
      results[address] = readValue(address, dataType);
    } catch (error) {
      console.error(`Error reading address ${address}: ${error}`);
    }
  }
  return results;
}

export function writeBatch(
  writes: [number, any, DataType][],
): void {
  for (const [address, value, dataType] of writes) {
    try {
      writeValue(address, value, dataType);
    } catch (error) {
      console.error(`Error writing to address ${address}: ${error}`);
    }
  }
}
