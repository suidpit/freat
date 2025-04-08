import { log } from "./logger.js";
import { ping } from "./ping.js"
import { scanStrings, read, readString, write, writeString, readBytes, writeBytes, freeze, unfreeze, firstScan, nextScan, clearScanState, getScanResults, ScanResult} from "./memory.js"
import { addStoppoint, removeStoppoint, StoppointMode } from "./stoppoint.js"
import { DisassembledInstruction, disassemble } from "./disassemble.js"
import { readRegister, writeRegister } from "./register.js"
import { initExceptionHandler } from "./exception.js";
import { intercept, CodeInjection, detachInterception, detachAllInterceptors } from "./intercept.js";
import { patch, PatchOperation } from "./patch.js";
import { getMemoryMaps, MemoryMap } from "./maps.js";

rpc.exports = {
    log: (message: string): void => log(message),
    ping: (): boolean => ping(),
    scanStrings: (targetValue: string, addresses?: string[]): string[] => scanStrings(targetValue, addresses),
    read: (address: string, width: number = 4, signed: boolean = false): number => read(address, width, signed),
    write: (address: string, value: number, width: number = 4, signed: boolean = false): void => write(address, value, width, signed),
    readString: (address: string, maxLength: number = 256): string => readString(address, maxLength),
    writeString: (address: string, value: string): void => writeString(address, value),
    addStoppoint: (address: string, mode: StoppointMode, size: number): number => addStoppoint(address, mode, size),
    removeStoppoint: (address: string, mode: StoppointMode): void => removeStoppoint(address, mode),
    disassemble: (address: string, count: number): DisassembledInstruction[] => disassemble(address, count),
    readBytes: (address: string, length: number): number[] => readBytes(address, length),
    writeBytes: (address: string, bytes: number[]): void => writeBytes(address, bytes),
    readRegister: (id: string): number | string | number[] => readRegister(id),
    writeRegister: (id: string, value: number | string | number[]): void => writeRegister(id, value),
    freeze: (address: string): void => freeze(address),
    unfreeze: (address: string): void => unfreeze(address),
    patch: (address: string, operations: PatchOperation[]): void => patch(address, operations),
    intercept: (address: string, codeInjection: CodeInjection): void => intercept(address, codeInjection),
    detachInterception: (address: string): void => detachInterception(address),
    detachAllInterceptors: (): void => detachAllInterceptors(),
    getMemoryMaps: (): MemoryMap[] => getMemoryMaps(),
    hexdump: (address: string, length: number): string => hexdump(ptr(address), { length: length }),
    firstScan: (targetValue: number, width: number = 4, signed: boolean = false): number => firstScan(targetValue, width, signed),
    nextScan: (targetValue: number): number => nextScan(targetValue),
    clearScanState: (): void => clearScanState(),
    getScanResults: (page: number = 1, pageSize: number = 100): { 
        results: ScanResult[], 
        total: number, 
        page: number, 
        pageSize: number, 
        totalPages: number 
    } => getScanResults(page, pageSize),
};

initExceptionHandler();