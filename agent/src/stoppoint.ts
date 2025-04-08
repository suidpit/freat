export const usedBreakpointSlots = new Map<string, number>();

export interface WatchpointInfo {
    mode: StoppointMode;
    size: number;
    slot: number;
}

export const watchpoints = new Map<string, WatchpointInfo>();


export enum StoppointMode {
    Read = 'r',
    Write = 'w',
    ReadWrite = 'rw',
    Execute = 'x'
}

export function addStoppoint(address: string, mode: StoppointMode, size: number = 1): number {
    if (mode === StoppointMode.Execute) {
        return addBreakpoint(address);
    } else {
        return addWatchpoint(address, mode, size);
    }
}

function findFirstAvailableSlot(usedSlots: number[]): number {
    let slot = 0;
    while (usedSlots.includes(slot)) {
        slot++;
    }
    return slot;
}

function addWatchpoint(address: string, mode: StoppointMode, size: number): number {
    console.log(`Adding watchpoint at ${address} with mode ${mode} and size ${size}`);
    const usedSlots = Array.from(watchpoints.values()).map(info => info.slot);
    const slot = findFirstAvailableSlot(usedSlots);

    const thread = Process.enumerateThreads()[0];
    thread.setHardwareWatchpoint(slot, ptr(address), size, mode as HardwareWatchpointConditions);

    watchpoints.set(ptr(address).toString(), {
        mode,
        size,
        slot
    });

    console.log(`Watchpoint added using slot ${slot} and info ${JSON.stringify(watchpoints.get(ptr(address).toString()))}`);
    console.log(`Watchpoints: ${JSON.stringify(Object.fromEntries(watchpoints))}`);

    return slot;
}

function addBreakpoint(address: string): number {
    console.log(`Adding breakpoint at ${address}`);
    const usedSlots = Array.from(usedBreakpointSlots.values());
    const slot = findFirstAvailableSlot(usedSlots);

    const thread = Process.enumerateThreads()[0];
    thread.setHardwareBreakpoint(slot, ptr(address));
    usedBreakpointSlots.set(ptr(address).toString(), slot);
    console.log(`Breakpoint added using register slot ${slot}`);
    return slot;
}

export function removeStoppoint(address: string, mode: StoppointMode) {
    console.log(`Removing stoppoint at ${address}`);
    if (!usedBreakpointSlots.has(ptr(address).toString())) {
        throw new Error(`No breakpoint exists at ${address}`);
    }

    if (mode === StoppointMode.Execute) {
        removeBreakpoint(address);
    } else {
        removeWatchpoint(address);
    }
}

export function removeBreakpoint(address: string) {
    const thread = Process.enumerateThreads()[0];
    for (const [addr, slot] of usedBreakpointSlots.entries()) {
        if (addr == address) {
            console.log(`Removing breakpoint at ${addr} using slot ${slot}`);
            thread.unsetHardwareBreakpoint(slot);
            usedBreakpointSlots.delete(addr);
            break;
        }
    }
    console.log(`Breakpoint removed and slot freed`);
}

export function removeWatchpoint(address: string) {
    const thread = Process.enumerateThreads()[0];
    const info = watchpoints.get(address);
    if (info) {
        thread.unsetHardwareWatchpoint(info.slot);
        watchpoints.delete(address);
    }
    console.log(`Watchpoint removed and slot freed`);
}
