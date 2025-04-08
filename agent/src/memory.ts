interface MemoryFunctions {
    readUnsigned: string;
    writeUnsigned: string;
    readSigned: string;
    writeSigned: string;
}

interface FrozenValue {
    address: string;
    value: number;
    width: number;
    signed: boolean;
}

export const FrozenValues: Map<string, FrozenValue> = new Map();

interface ScanState {
    addresses: string[];
    width: number;
    signed: boolean;
}

export interface ScanResult {
    address: string;
    value: number;
}

let currentScanState: ScanState | null = null;

const widthFunctions: Record<number, MemoryFunctions> = {
    1: { readUnsigned: 'readU8', writeUnsigned: 'writeU8', readSigned: 'readS8', writeSigned: 'writeS8' },
    2: { readUnsigned: 'readU16', writeUnsigned: 'writeU16', readSigned: 'readS16', writeSigned: 'writeS16' },
    4: { readUnsigned: 'readU32', writeUnsigned: 'writeU32', readSigned: 'readS32', writeSigned: 'writeS32' },
    8: { readUnsigned: 'readU64', writeUnsigned: 'writeU64', readSigned: 'readS64', writeSigned: 'writeS64' }
};

const numberToPattern = (num: number, width: number): string => {
    const buffer = new ArrayBuffer(width);
    const view = new DataView(buffer);

    switch (width) {
        case 1: view.setInt8(0, num); break;
        case 2: view.setInt16(0, num, true); break;
        case 4: view.setInt32(0, num, true); break;
        case 8: view.setBigInt64(0, BigInt(num), true); break;
    }

    return Array.from(new Uint8Array(buffer))
        .map(b => b.toString(16).padStart(2, '0'))
        .join(' ');
};

const matchInAddresses = (targetValue: number, addresses: string[], width: number): string[] => {
    const results: string[] = [];
    const readFunction = widthFunctions[width]?.readUnsigned;
    if (!readFunction) {
        throw new Error(`Unsupported width: ${width}`);
    }
    addresses.forEach((addr) => {
        try {
            const value = (ptr(addr) as any)[readFunction]();
            if (value === targetValue) {
                results.push(addr);
            }
        } catch (e) {
            console.log("Error reading address:", e);
        }
    });
    return results;
};

function scanJS(targetValue: number, addresses?: string[], width: number = 4): string[] {
    console.log("Initiated scan")
    const results: string[] = [];
    const readFunction = widthFunctions[width]?.readUnsigned;
    console.log("Scanning with width:", width);

    if (!readFunction) {
        throw new Error(`Unsupported width: ${width}`);
    }
    const pattern = numberToPattern(targetValue, width);

    if (addresses && addresses?.length > 0) {
        return matchInAddresses(targetValue, addresses, width);
    } else {
        Process.enumerateRanges({ protection: "rw-", coalesce: true })
            // TODO: find out more ranges to exclude
            .filter(range => !range.file || !range.file.path.includes('dyld_shared_cache'))
            .forEach((range) => {
                try {
                    const size = range.size;
                    const baseAddress = range.base;
                    const rangeMatches = Memory.scanSync(baseAddress, size, pattern);
                    rangeMatches.forEach(match => {
                        results.push(match.address.toString());
                    });
                } catch (e) {
                    console.log("Error scanning range:", e);
                }
            });
    }
    console.log("Scan complete")
    return results;
}

const matches = Memory.alloc(4);

const cm = new CModule(`
    #include <gum/gummemory.h>
    #include "stdio.h"
    #include "glib.h"
    
    extern GArray *matches;

    void init() {
        matches = g_array_new(FALSE, FALSE, sizeof(GumAddress));
    }

    void finalize() {
        g_array_free(matches, TRUE);
    }

    int onMatch(GumAddress address, gsize size, gpointer user_data) {
        g_array_append_val(matches, address);
        return 0;
    }

    void scan(void *range_start, unsigned long range_size, gchar *pattern_string) {
        GumMemoryRange range = {(GumAddress)range_start, range_size};
        GumMatchPattern *pattern = gum_match_pattern_new_from_string(pattern_string);
        gum_memory_scan(&range, pattern, onMatch, NULL);
    }

    int get_matches_length() {
        return matches->len;
    }

    GumAddress get_match_at(int index) {
        return g_array_index(matches, GumAddress, index);
    }
`, { matches });


function scanC(targetValue: number, addresses?: string[], width: number = 4): string[] {
    if (addresses && addresses?.length > 0) {
        return matchInAddresses(targetValue, addresses, width);
    }
    const scan = new NativeFunction(cm.scan, 'void', ['pointer', 'uint', 'pointer']);
    const getMatchesLength = new NativeFunction(cm.get_matches_length, 'int', []);
    const getMatchAt = new NativeFunction(cm.get_match_at, 'uint64', ['int']);

    const pattern = Memory.allocUtf8String(numberToPattern(targetValue, width));
    const results: string[] = [];

    Process.enumerateRanges('rw-').forEach((range) => {
        try {
            scan(range.base, range.size, pattern);

            const length = getMatchesLength();
            for (let i = 0; i < length; i++) {
                results.push(getMatchAt(i).toString(16));
            }
        } catch (e) {
            console.log('Error scanning range:', e);
        }
    });

    return results;
}

export function scanStrings(targetValue: string, addresses?: string[]): string[] {
    const results: string[] = [];
    if (addresses && addresses?.length > 0) {
        return addresses.filter(addr => {
            try {
                const value = ptr(addr).readUtf8String();
                return value?.includes(targetValue) ?? false;
            } catch (e) {
                console.log("Error reading address:", e);
                return false;
            }
        });
    }
    const pattern = new MatchPattern(`/${targetValue}/`);
    Process.enumerateRanges('rw-').forEach((range) => {
        try {
            const matches = Memory.scanSync(range.base, range.size, pattern);
            matches.forEach(match => {
                results.push(match.address.toString(16));
            });
        } catch (e) {
            console.log('Error scanning range:', e);
        }
    });
    return results;
}

export function firstScan(targetValue: number, width: number = 4, signed: boolean = false): number {
    const results = scanJS(targetValue, [], width);
    
    currentScanState = {
        addresses: results,
        width,
        signed
    };
    
    return results.length;
}

export function nextScan(targetValue: number): number {
    if (!currentScanState) {
        throw new Error("No previous scan found. Call firstScan before nextScan.");
    }
    
    const { addresses, width, signed } = currentScanState;
    
    const results = scanJS(targetValue, addresses, width);
    
    currentScanState.addresses = results;
    
    return results.length;
}

export function getScanResults(page: number = 1, pageSize: number = 100): { 
    results: ScanResult[], 
    total: number, 
    page: number, 
    pageSize: number, 
    totalPages: number 
} {
    if (!currentScanState) {
        throw new Error("No scan results available. Call firstScan or nextScan first.");
    }
    
    const { addresses, width, signed } = currentScanState;
    const total = addresses.length;
    const totalPages = Math.ceil(total / pageSize);
    
    if (page < 1) page = 1;
    if (page > totalPages) page = totalPages;
    
    const startIndex = (page - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, total);
    
    const pageAddresses = addresses.slice(startIndex, endIndex);
    
    const results: ScanResult[] = pageAddresses.map(addr => {
        try {
            const value = read(addr, width, signed);
            return { address: addr, value };
        } catch (e) {
            console.log(`Error reading address ${addr}:`, e);
            return { address: addr, value: 0 };
        }
    });
    
    return {
        results,
        total,
        page,
        pageSize,
        totalPages
    };
}

export function clearScanState(): void {
    currentScanState = null;
}

export function readString(address: string, maxLength: number = 256): string {
    return ptr(address).readUtf8String(maxLength) ?? '';
}

export function writeString(address: string, value: string): void {
    ptr(address).writeUtf8String(value);
}

export function read(address: string, width: number = 4, signed: boolean = false): number {
    const readFunction = signed ? widthFunctions[width]?.readSigned : widthFunctions[width]?.readUnsigned;
    if (!readFunction) {
        throw new Error(`Unsupported width: ${width}`);
    }
    return (ptr(address) as any)[readFunction]();
}

export function readBytes(address: string, length: number): number[] {
    const bytes = ptr(address).readByteArray(length);
    return Array.from(new Uint8Array(bytes!));
}

export function writeBytes(address: string, bytes: number[]): void {
    ptr(address).writeByteArray(bytes);
}

export function write(address: string, value: number, width: number = 4, signed: boolean = false): void {
    const writeFunction = signed ? widthFunctions[width]?.writeSigned : widthFunctions[width]?.writeUnsigned;
    if (!writeFunction) {
        throw new Error(`Unsupported width: ${width}`);
    }
    (ptr(address) as any)[writeFunction](value);
}

export function freeze(address: string): void {
    console.log("Freezing address:", address);
    // TODO: Fix for width
    const currentValue = read(address, 4);
    FrozenValues.set(address, {
        address,
        value: currentValue,
        width: 4,
        signed: false
    });
}

export function unfreeze(address: string): void {
    console.log("Unfreezing address:", address);
    if (!FrozenValues.has(address)) {
        throw new Error(`Address ${address} is not frozen`);
    }
    FrozenValues.delete(address);
}

export function updateFrozenValue(address: string, value: number): void {
    const frozen = FrozenValues.get(address);
    if (!frozen) {
        throw new Error(`Address ${address} is not frozen`);
    }
    frozen.value = value;
}

function startFreezeThread() {
    setInterval(() => {
        FrozenValues.forEach((frozen) => {
            try {
                write(frozen.address, frozen.value, frozen.width, frozen.signed);
            } catch (e) {
                console.log(`Error writing to frozen address ${frozen.address}:`, e);
                FrozenValues.delete(frozen.address);
            }
        });
    }, 50); // Run every 50ms
}

startFreezeThread();
