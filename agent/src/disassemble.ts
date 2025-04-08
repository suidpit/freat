export interface DisassembledInstruction {
    address: string;
    offset: string;
    mnemonic: string;
}

function _getOffset(address: string): string {
    const range = Process.getRangeByAddress(ptr(address));
    return (ptr(address).sub(range.base)).toString();
}

export const disassemble = (address: string, count: number): DisassembledInstruction[] => {
    const instructions: DisassembledInstruction[] = [];

    const instruction = Instruction.parse(ptr(address));

    instructions.push({
        address: instruction.address.toString(),
        offset: _getOffset(instruction.address.toString()),
        mnemonic: instruction.toString(),
    });

    let currentInstruction = instruction;

    for (let i = 1; i < count; i++) {
        const nextInstruction = Instruction.parse(currentInstruction.next);
        instructions.push({
            address: nextInstruction.address.toString(),
            offset: _getOffset(nextInstruction.address.toString()),
            mnemonic: nextInstruction.toString(),
        });
        currentInstruction = nextInstruction;
    }

    return instructions;
}

