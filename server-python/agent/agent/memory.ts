import { DataType } from "./types.js";

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

export function readBatch(
  addresses: [string, DataType][],
): { [key: string]: any } {
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

export function writeBatch(
  writes: [string, any, DataType][],
): void {
  for (const [address, value, dataType] of writes) {
    try {
      writeValue(ptr(address), value, dataType);
    } catch (error) {
      console.error(`Error writing to address ${address}: ${error}`);
    }
  }
}
