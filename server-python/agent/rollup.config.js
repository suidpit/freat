import replace from "@rollup/plugin-replace";
import typescript from "@rollup/plugin-typescript";
import fs from "fs";
import path from "path";
import { nodeResolve } from "@rollup/plugin-node-resolve";
import commonjs from "@rollup/plugin-commonjs";
import terser from "@rollup/plugin-terser";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const cScannerPath = path.resolve(__dirname, "native/scanner.c");
const cFreezerPath = path.resolve(__dirname, "native/freezer.c");
const outputAgentPath = path.resolve(
  __dirname,
  "../src/freat_server/_agent.js",
);

export default {
  input: "agent/index.ts",

  output: {
    file: outputAgentPath,
    format: "iife",
  },
  plugins: [
    replace({
      preventAssignment: true,
      delimiters: ['"', '"'],
      values: {
        __SCANNER_C_MODULE_PLACEHOLDER__: JSON.stringify(
          fs.readFileSync(cScannerPath, "utf8"),
        ),
        __FREEZER_C_MODULE_PLACEHOLDER__: JSON.stringify(
          fs.readFileSync(cFreezerPath, "utf8"),
        ),
      },
    }),
    nodeResolve({
      preferBuiltins: false,
    }),
    commonjs(),
    typescript(),
    terser({
      output: { comments: false },
      compress: {
        drop_console: false,
        passes: 2,
      },
    }),
  ],
};
