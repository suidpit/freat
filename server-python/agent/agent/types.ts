export enum DataType {
  U8 = 0,
  U16 = 1,
  U32 = 2,
  U64 = 3,
  FLOAT = 4,
  DOUBLE = 5,
  STRING = 6
}

export function dataTypeByteSize(dt: DataType): number {
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

export enum ScanType {
  EXACT,
  LESS_THAN,
  GREATER_THAN,
  INCREASED,
  DECREASED,
  UNKNOWN,
  UNCHANGED,
}
