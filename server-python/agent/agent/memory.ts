function readAddress(address: number): any {}

export function readBatch(addresses: number[]): { [key: number]: any } {
  return readBatch(addresses);
}

export function writeBatch(writes: { [key: number]: [number, number] }): void {
  return writeBatch(writes);
}
