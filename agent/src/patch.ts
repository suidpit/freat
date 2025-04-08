const maxInstructionSize: Record<Architecture, number> = {
    "ia32": 15,
    "x64": 15,
    "arm": 4,
    "arm64": 4,
    "mips": 4,
}

const codeWriters: Record<Architecture, any> = {
    "ia32": 'X86Writer',
    "x64": 'X86Writer',
    "arm": 'ArmWriter',
    "arm64": 'Arm64Writer',
    "mips": 'MipsWriter',
}

export interface PatchOperation {
    method: string;
    values: (number | string)[];
}

export function patch(address: string, operations: PatchOperation[]): void {
    const size = maxInstructionSize[process.arch as Architecture] * operations.length;
    Memory.patchCode(ptr(address), size, code => {
        const cw = new codeWriters[process.arch as Architecture]();
        for (const operation of operations) {
            // Not checking if the method exists, we'll get an error if it doesn't
            cw[operation.method](...operation.values);
        }
        cw.flush();
    });
}
