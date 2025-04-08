import { usedBreakpointSlots, watchpoints, StoppointMode, removeBreakpoint, removeWatchpoint } from "./stoppoint.js";

export let currentContext: CpuContext | null = null;


export function getContext(): CpuContext | null {
    return currentContext;
}


function getMemoryAccessFromInstruction(ctx: CpuContext, instruction: Instruction): { address: NativePointer, operation: string } | null {
    for (const operand of (instruction as any).operands) {
        if (operand.type === 'mem') {
            const memOp = operand.value;
            let address: NativePointer;

            address = ctx[memOp.base as keyof CpuContext].add(memOp.disp);
            console.log(`Memory access at ${address}, operation: ${operand.access}`);

            return {
                address: address,
                operation: operand.access
            };
        }
    }
    return null;
}


export function initExceptionHandler() {
    Process.setExceptionHandler(e => {
        console.log("EHI! Exception:", JSON.stringify(e, null, 2));
        currentContext = e.context;
        const accessedMemory = getMemoryAccessFromInstruction(e.context, Instruction.parse(e.address));

        const thread = Process.enumerateThreads()[0];
        if (Process.getCurrentThreadId() === thread.id && ['breakpoint', 'single-step'].includes(e.type)) {
            const instruction = Instruction.parse(e.address);
            console.log(`Instruction: ${instruction.toString()} at ${e.address}`);
            console.log(`=== Handler got ${e.type} exception at ${e.context.pc} ===`);

            if (usedBreakpointSlots.has(e.address.toString())) {
                console.log(`Breakpoint hit at ${e.address}`);
                const slot = usedBreakpointSlots.get(e.address.toString());
                removeBreakpoint(e.address.toString());
                send({
                    type: 'breakpoint',
                    address: e.address,
                    slot: slot
                });
                console.log(`Sent breakpoint event`);
            } else {
                const memAccess = getMemoryAccessFromInstruction(e.context, instruction);

                if (memAccess) {
                    const info = watchpoints.get(memAccess.address.toString());
                    if (info && (
                        info.mode === memAccess.operation ||
                        info.mode === StoppointMode.ReadWrite ||
                        memAccess.operation === StoppointMode.ReadWrite
                    )) {
                        removeWatchpoint(memAccess.address.toString());
                        send({
                            type: 'watchpoint',
                            address: memAccess.address,
                            operation: memAccess.operation,
                            size: info.size,
                            slot: info.slot,
                            pc: e.context.pc
                        });
                    } else {
                        const currentInstruction = Instruction.parse(e.context.pc);
                        e.context.pc = currentInstruction.next;
                        return true;
                    }
                } else {
                    const currentInstruction = Instruction.parse(e.context.pc);
                    e.context.pc = currentInstruction.next;
                    return true;
                }
            }

            console.log("Waiting for resume message");
            var op = recv('resume', (msg) => {
                console.log(`Received resume message: ${msg}`);
            });
            op.wait();
            console.log("Resume message received");
            currentContext = null;
            return true;
        } else if (e.type === 'access-violation') {
            console.log(`Access violation at ${e.memory!.address} is in frozen address`);
            const currentInstruction = Instruction.parse(e.context.pc);
            e.context.pc = currentInstruction.next;
            return true;
        } else {
            console.error(`Unknown exception type: ${e.type}`);
            // Not our fault, let the system handle it
            return false;
        }
    });
}