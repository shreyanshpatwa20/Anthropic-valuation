// Compiles contracts/*.sol with the bundled solc-js (no network download) into build/artifacts.json
const fs = require("fs");
const path = require("path");
const solc = require("solc");

const dir = path.join(__dirname, "..", "contracts");
const sources = {};
for (const f of fs.readdirSync(dir).filter((f) => f.endsWith(".sol"))) {
  sources[f] = { content: fs.readFileSync(path.join(dir, f), "utf8") };
}
const input = {
  language: "Solidity",
  sources,
  settings: {
    optimizer: { enabled: true, runs: 200 },
    viaIR: true,
    evmVersion: "shanghai",
    outputSelection: { "*": { "*": ["abi", "evm.bytecode.object"] } },
  },
};
const out = JSON.parse(solc.compile(JSON.stringify(input), { import: (p) => ({ contents: fs.readFileSync(path.join(dir, p), "utf8") }) }));
const errs = (out.errors || []).filter((e) => e.severity === "error");
for (const e of out.errors || []) console.error(e.formattedMessage);
if (errs.length) process.exit(1);
const artifacts = {};
for (const file of Object.keys(out.contracts)) {
  for (const [name, c] of Object.entries(out.contracts[file])) {
    if (!c.evm.bytecode.object) continue;
    artifacts[name] = { abi: c.abi, bytecode: "0x" + c.evm.bytecode.object };
  }
}
fs.mkdirSync(path.join(__dirname, "..", "build"), { recursive: true });
fs.writeFileSync(path.join(__dirname, "..", "build", "artifacts.json"), JSON.stringify(artifacts));
console.log("Compiled:", Object.keys(artifacts).join(", "), "| solc", solc.version());
