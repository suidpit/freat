export interface MemoryMap {
    name: string;
    base_address: string;
    protection: string;
}

export function getMemoryMaps(): MemoryMap[] {
    var ranges = Process.enumerateRanges("r-x");
    return ranges.filter((range) => {
        if (!range.file) return false;
        return true;
    }).map((range) => ({
        name: range.file!.path,
        base_address: range.base.toString(),
        protection: range.protection.toString(),
    }));
}

