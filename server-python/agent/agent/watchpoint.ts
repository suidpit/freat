import { log } from "./logger.js";
import { DataType, dataTypeByteSize } from "./types.js";

let watchpointActive = false;

export function setWatchpoint(
  address: string,
  dataType: DataType,
  condition: "r" | "w",
): void {
  const size = dataTypeByteSize(dataType);
  if (watchpointActive) {
    clearWatchpoint();
  }

  const target = ptr(address);
  log(`Setting ${condition} watchpoint on ${target} (size=${size})`);

  Process.setExceptionHandler((details) => {
    if (!watchpointActive) {
      return false;
    }

    const pc = details.context.pc;

    clearWatchpointOnThreads();
    watchpointActive = false;

    const bt = Thread.backtrace(details.context, Backtracer.ACCURATE);
    const backtrace = bt.map((frame) => {
      const sym = DebugSymbol.fromAddress(frame);
      const hasRealName = sym.name && !sym.name.startsWith("0x");
      if (hasRealName) {
        return `${frame}  ${sym.moduleName}!${sym.name}+0x${frame.sub(sym.address).toString(16)}`;
      } else if (sym.moduleName) {
        const mod = Process.findModuleByName(sym.moduleName);
        if (mod) {
          return `${frame}  ${sym.moduleName}+0x${frame.sub(mod.base).toString(16)}`;
        }
        return `${frame}  ${sym.moduleName}`;
      }
      return frame.toString();
    });

    const disassembly: { address: string; mnemonic: string; opStr: string }[] =
      [];
    let cursor = pc;
    for (let i = 0; i < 10; i++) {
      try {
        const insn = Instruction.parse(cursor);
        disassembly.push({
          address: cursor.toString(),
          mnemonic: insn.mnemonic,
          opStr: insn.opStr,
        });
        cursor = insn.next;
      } catch {
        break;
      }
    }

    send({
      type: "watchpoint-hit",
      address: address,
      pc: pc.toString(),
      operation: condition === "r" ? "read" : "write",
      backtrace: backtrace,
      disassembly: disassembly,
    });

    return true;
  });

  const threads = Process.enumerateThreads();
  for (const thread of threads) {
    try {
      thread.setHardwareWatchpoint(0, target, size, condition);
    } catch (e) {
      log(`Failed to set watchpoint on thread ${thread.id}: ${e}`);
    }
  }

  watchpointActive = true;
  log(`Watchpoint set on ${threads.length} threads`);
}

function clearWatchpointOnThreads(): void {
  const threads = Process.enumerateThreads();
  for (const thread of threads) {
    try {
      thread.unsetHardwareWatchpoint(0);
    } catch {
      // Thread may have exited or watchpoint wasn't set
    }
  }
}

export function clearWatchpoint(): void {
  if (!watchpointActive) {
    return;
  }
  clearWatchpointOnThreads();
  watchpointActive = false;
  log("Watchpoint cleared");
}
