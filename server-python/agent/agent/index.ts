import { log } from "./logger.js";

rpc.exports = {
  hello: (): string => {
    log("hello() was called!");
    return "hello from the agent!";
  },
};
