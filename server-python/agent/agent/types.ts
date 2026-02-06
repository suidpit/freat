export enum DataType {
  U8 = 0,
  U16 = 1,
  U32 = 2,
  U64 = 3,
  FLOAT = 4,
  DOUBLE = 5,
  STRING = 6
}

export enum ScanType {
  EXACT,
  LESS_THAN,
  GREATER_THAN,
  INCREASED,
  DECREASED,
  UNKNOWN,
}
