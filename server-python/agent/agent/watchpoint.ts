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

    const pcModule = Process.findModuleByAddress(pc);
    const pcLabel = pcModule
      ? `${pcModule.name}+0x${pc.sub(pcModule.base).toString(16)}`
      : pc.toString();

    let bt = Thread.backtrace(details.context, Backtracer.ACCURATE);
    if (bt.length === 0) {
      bt = Thread.backtrace(details.context, Backtracer.FUZZY);
    }
    const backtrace = bt.map((frame) => {
      const sym = DebugSymbol.fromAddress(frame);
      const hasRealName = sym.name && !sym.name.startsWith("0x");
      if (hasRealName) {
        return `${frame}  ${sym.moduleName}!${sym.name}+0x${frame.sub(sym.address).toString(16)}`;
      }
      const mod = sym.moduleName
        ? Process.findModuleByName(sym.moduleName)
        : Process.findModuleByAddress(frame);
      if (mod) {
        return `${frame}  ${mod.name}+0x${frame.sub(mod.base).toString(16)}`;
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
      pc: pcLabel,
      operation: condition === "r" ? "read" : "write",
      backtrace: backtrace,
      disassembly: disassembly,
    });

    return true;
  });

  const mainThread = Process.enumerateThreads()[0];
  try {
    mainThread.setHardwareWatchpoint(0, target, size, condition);
  } catch (e) {
    log(`Failed to set watchpoint on main thread ${mainThread.id}: ${e}`);
    return;
  }

  watchedThreadId = mainThread.id;
  watchpointActive = true;
  log(`Watchpoint set on main thread (tid=${mainThread.id})`);
}

let watchedThreadId: number | null = null;

function clearWatchpointOnThreads(): void {
  if (watchedThreadId === null) return;
  const threads = Process.enumerateThreads();
  for (const thread of threads) {
    if (thread.id === watchedThreadId) {
      try {
        thread.unsetHardwareWatchpoint(0);
      } catch {
        // thread may have exited
      }
      break;
    }
  }
  watchedThreadId = null;
}

export function clearWatchpoint(): void {
  if (!watchpointActive) {
    return;
  }
  clearWatchpointOnThreads();
  watchpointActive = false;
  log("Watchpoint cleared");
}
