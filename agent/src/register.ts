import { getContext } from "./exception.js";

export function readRegister(id: string): number | string | number[] {
    const context = getContext();
    if (!context) {
        throw new Error("No context found. Make sure to call getContext() when the process is paused.");
    }
    const val = context[id as keyof typeof context];
    if (typeof val === 'number') {
        return val;
    } else if (val instanceof NativePointer) {
        return val.toString();
    } else if (Array.isArray(val)) {
        return val;
    }
    throw new Error(`Unsupported register type: ${typeof val}`);
}

export function writeRegister(id: string, value: number | string | number[]): void {
    const context = getContext();
    if (!context) {
        throw new Error("No context found. Make sure to call getContext() when the process is paused.");
    }
    if (typeof value === 'number') {
        console.log(`Writing number ${value} to ${id}`);
        (context[id as keyof typeof context] as any) = value;
    } else if (typeof value === 'string') {
        console.log(`Writing NativePointer ${value} to ${id}`);
        context[id as keyof typeof context] = ptr(value);
    } else if (Array.isArray(value)) {
        console.log(`Writing array ${value} to ${id}`);
        (context[id as keyof typeof context] as any) = value;
    }
}