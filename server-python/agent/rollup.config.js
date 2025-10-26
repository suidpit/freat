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
const cModulePath = path.resolve(__dirname, "agent/scanner.c");
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
    nodeResolve({
      preferBuiltins: false,
    }),
    commonjs(),
    typescript(),
    replace({
      preventAssignment: true,
      values: {
        __C_MODULE_PLACEHOLDER__: () => {
          console.log(`Injecting C module from ${cModulePath}...`);
          const cCode = fs.readFileSync(cModulePath, "utf8");
          return JSON.stringify(cCode);
        },
      },
    }),

    terser({
      output: { comments: false },
      compress: {
        drop_console: false,
        passes: 2,
      },
    }),
  ],
};
