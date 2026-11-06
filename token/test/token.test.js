// End-to-end tests on an in-process ganache EVM. Run: npm test
const { test, before } = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const ganache = require("ganache");
const { ethers } = require("ethers");
const A = require(path.join(__dirname, "..", "build", "artifacts.json"));

const UAE = 784, US = 840, KP = 408;
const CAT = { Professional: 1, Qualified: 2, Employee: 3, Custodian: 4 };
const E = (n) => ethers.parseUnits(String(n), 18);
const YEAR = 365 * 24 * 3600;

let provider, rawRequest, s, reg, comp, tok, grants;
const IFACES = Object.values(A).map((a) => new ethers.Interface(a.abi));
let issuer, agent, valuer, spv, alice, bob, carol, emp, mallory, aliceNew;

async function deploy(name, signer, ...args) {
  const f = new ethers.ContractFactory(A[name].abi, A[name].bytecode, signer);
  const c = await f.deploy(...args);
  await c.waitForDeployment();
  return c;
}
async function now() { return (await provider.getBlock("latest")).timestamp; }
async function warp(sec) { await provider.send("evm_increaseTime", [sec]); await provider.send("evm_mine", []); }
async function code(from, to, amt) { return Number(await tok.detectTransferRestriction(from, to, amt)); }
// Replays the call with raw eth_call and decodes the custom error against every contract ABI.
async function reverts(contract, fn, args, name) {
  const data = contract.interface.encodeFunctionData(fn, args);
  const from = await contract.runner.getAddress();
  let revertData;
  try {
    await rawRequest({ method: "eth_call", params: [{ from, to: await contract.getAddress(), data }, "latest"] });
  } catch (e) { revertData = e.data; }
  assert.ok(revertData, `${fn} was expected to revert with ${name} but succeeded`);
  const decoded = IFACES.map((i) => { try { return i.parseError(revertData); } catch { return null; } }).find(Boolean);
  assert.equal(decoded && decoded.name, name, `${fn} reverted with ${decoded && decoded.name}`);
}

before(async () => {
  const gp = ganache.provider({ logging: { quiet: true }, wallet: { totalAccounts: 12 },
    chain: { allowUnlimitedContractSize: true, vmErrorsOnRPCResponse: true } });
  // Re-shape ganache revert errors into the EIP-1474 form ethers decodes (code 3 + data), so custom errors surface.
  const eip1193 = { request: async (args) => {
    try { return await gp.request(args); } catch (e) {
      if (typeof e.data === "string" && e.data.startsWith("0x")) {
        const err = new Error("execution reverted"); err.code = 3; err.data = e.data; throw err;
      }
      throw e;
    }
  } };
  provider = new ethers.BrowserProvider(eip1193);
  rawRequest = (args) => gp.request(args);
  s = await Promise.all([...Array(12).keys()].map((i) => provider.getSigner(i)));
  [issuer, agent, valuer, spv, alice, bob, carol, emp, mallory, aliceNew] = s;

  reg = await deploy("IdentityRegistry", issuer);
  comp = await deploy("Compliance", issuer, await reg.getAddress(), 2000, 2500); // 2,000 holders, 25% cap
  tok = await deploy("RegulatedEquityToken", issuer, "Frontier AI Exposure Token", "FAIX",
    await reg.getAddress(), await comp.getAddress(), 2000); // 20% max NAV move per update
  await comp.bindToken(await tok.getAddress());
  grants = await deploy("EmployeeGrantManager", issuer, await tok.getAddress(), await reg.getAddress(), E(1_000_000));

  for (const c of [reg, comp, tok]) await c.addAgent(await agent.getAddress());
  await tok.addAgent(await grants.getAddress());
  await grants.addAgent(await agent.getAddress());
  await comp.setCountry(UAE, true);
  await tok.setValuationAgent(await valuer.getAddress());

  const exp = (await now()) + 5 * YEAR;
  const r = reg.connect(agent);
  const h = (x) => ethers.id("kyc:" + x);
  await r.registerIdentity(await spv.getAddress(), h("spv"), UAE, CAT.Custodian, exp);
  await r.registerIdentity(await grants.getAddress(), h("grant-escrow"), UAE, CAT.Custodian, exp);
  await r.registerIdentity(await alice.getAddress(), h("alice"), UAE, CAT.Professional, exp);
  await r.registerIdentity(await aliceNew.getAddress(), h("alice"), UAE, CAT.Professional, exp);
  await r.registerIdentity(await bob.getAddress(), h("bob"), UAE, CAT.Qualified, exp);
  await r.registerIdentity(await carol.getAddress(), h("carol"), US, CAT.Professional, exp);
  await r.registerIdentity(await emp.getAddress(), h("emp"), UAE, CAT.Employee, exp);
  await comp.setExempt(await spv.getAddress(), true);
  await comp.setExempt(await grants.getAddress(), true);
});

test("issuance requires a reason and a verified, permitted recipient", async () => {
  await reverts(tok.connect(agent), "mint", [await spv.getAddress(), E(10_000_000), ""], "ReasonRequired");
  await reverts(tok.connect(agent), "mint", [await mallory.getAddress(), E(1), "x"], "TransferRestricted");
  await tok.connect(agent).mint(await spv.getAddress(), E(10_000_000), "Initial issuance: SPV subscription");
  assert.equal(await tok.totalSupply(), E(10_000_000));
  await reverts(tok.connect(mallory), "mint", [await mallory.getAddress(), E(1), "x"], "NotAgent");
});

test("verified UAE investors can trade; unverified, blocked-country and over-concentrated cannot", async () => {
  await tok.connect(spv).transfer(await alice.getAddress(), E(1_000_000));
  await tok.connect(alice).transfer(await bob.getAddress(), E(250_000));
  assert.equal(await tok.balanceOf(await bob.getAddress()), E(250_000));
  assert.equal(await code(await alice.getAddress(), await mallory.getAddress(), E(1)), 5); // not verified
  assert.equal(await code(await alice.getAddress(), await carol.getAddress(), E(1)), 6);   // US not permitted
  assert.equal(await code(await spv.getAddress(), await bob.getAddress(), E(3_000_000)), 10); // >25% of supply
  await reverts(tok.connect(alice), "transfer", [await carol.getAddress(), E(1)], "TransferRestricted");
  assert.equal(await tok.messageForTransferRestriction(6), "Jurisdiction not permitted for this offering");
});

test("transferFrom respects allowance and compliance", async () => {
  await tok.connect(alice).approve(await bob.getAddress(), E(100));
  await tok.connect(bob).transferFrom(await alice.getAddress(), await bob.getAddress(), E(60));
  await reverts(tok.connect(bob), "transferFrom", [await alice.getAddress(), await bob.getAddress(), E(60)], "InsufficientAllowance");
});

test("expired KYC blocks transfers until renewed", async () => {
  const short = (await now()) + 60;
  await reg.connect(agent).updateIdentity(await bob.getAddress(), ethers.id("kyc:bob"), UAE, CAT.Qualified, short);
  await warp(120);
  assert.equal(await code(await bob.getAddress(), await alice.getAddress(), E(1)), 4);
  await reg.connect(agent).updateIdentity(await bob.getAddress(), ethers.id("kyc:bob"), UAE, CAT.Qualified,
    (await now()) + 5 * YEAR);
  assert.equal(await code(await bob.getAddress(), await alice.getAddress(), E(1)), 0);
});

test("lock-up, freezes and pause each block transfers with a distinct code", async () => {
  const a = await alice.getAddress(), b = await bob.getAddress();
  await comp.connect(agent).setLockup(a, (await now()) + 1000);
  assert.equal(await code(a, b, E(1)), 7);
  await comp.connect(agent).setLockup(a, 0);
  await tok.connect(agent).freezePartialTokens(a, E(749_000), "Margin pledge");
  assert.equal(await code(a, b, E(1_000)), 8);
  await tok.connect(agent).unfreezePartialTokens(a, E(749_000), "Pledge released");
  await tok.connect(agent).setAddressFrozen(b, true, "Sanctions screening hit");
  assert.equal(await code(a, b, E(1)), 3);
  await tok.connect(agent).setAddressFrozen(b, false, "Cleared");
  await tok.setPaused(true, "Corporate action: IPO conversion");
  assert.equal(await code(a, b, E(1)), 1);
  await tok.setPaused(false, "Resumed");
});

test("new employee: grant with cliff + vesting, inside the pool cap, locked until IPO lock-up ends", async () => {
  const e = await emp.getAddress();
  await comp.setEmployeeLockup((await now()) + 2 * YEAR);
  const start = await now();
  await grants.connect(agent).createGrant(e, E(48_000), start, YEAR, 4 * YEAR, true, "Research Engineer");
  assert.equal(await tok.balanceOf(await grants.getAddress()), E(48_000));
  await reverts(grants.connect(emp), "release", [0], "NothingToRelease"); // before cliff
  await warp(YEAR + 10);
  await grants.connect(emp).release(0);
  const bal = await tok.balanceOf(e);
  assert.ok(bal >= E(12_000) && bal < E(12_010), `vested at cliff ~25%, got ${ethers.formatUnits(bal)}`);
  // employee cannot sell while in lock-up, and cannot buy on the secondary market
  assert.equal(await code(e, await alice.getAddress(), E(1)), 7);
  assert.equal(await code(await alice.getAddress(), e, E(1)), 11);
  // pool cap is a hard dilution ceiling
  await reverts(grants.connect(agent), "createGrant", [e, E(1_000_000), start, 0, YEAR, true, "Too big"], "PoolExhausted");
  // non-employee identity cannot receive a grant
  await reverts(grants.connect(agent), "createGrant", [await bob.getAddress(), E(1), start, 0, YEAR, true, "x"], "NotEmployee");
});

test("leaver: only the unvested part is cancelled; vested tokens stay claimable", async () => {
  await warp(YEAR); // ~2 years in => ~50% vested, 25% already released
  const before = await grants.poolIssued();
  await grants.connect(agent).revoke(0);
  const g = await grants.grants(0);
  assert.ok(g.total >= E(24_000) && g.total < E(24_100));
  assert.ok((await grants.poolIssued()) < before);
  await grants.connect(emp).release(0);
  const bal = await tok.balanceOf(await emp.getAddress());
  assert.equal(bal, g.total, "employee receives every vested token after revocation");
  await reverts(grants.connect(agent), "revoke", [0], "NotRevocable");
});

test("NAV publication: source-hashed, and large moves need the owner (two-key rule)", async () => {
  const hash = ethers.id("Anthropic_Valuation_Model.xlsx@v1");
  await tok.connect(valuer).publishNav(5_880_000n, hash); // $5.88 base-case token price from the model
  await tok.connect(valuer).publishNav(6_400_000n, hash); // +8.8%: allowed
  await reverts(tok.connect(valuer), "publishNav", [9_180_000n, hash], "NavMoveTooLarge"); // +43%: blocked
  await tok.connect(issuer).publishNav(9_180_000n, hash);  // owner sign-off
  assert.equal(await tok.navSourceHash(), hash);
  await reverts(tok.connect(mallory), "publishNav", [1n, hash], "NotValuationAgent");
  const v = await tok.positionValue(await bob.getAddress());
  assert.equal(v, (await tok.balanceOf(await bob.getAddress())) * 9_180_000n / E(1));
});

test("forced transfer and lost-wallet recovery are logged and identity-bound", async () => {
  const a = await alice.getAddress(), an = await aliceNew.getAddress(), b = await bob.getAddress();
  await reverts(tok.connect(agent), "recoverWallet", [a, b], "TransferRestricted"); // different investor
  const bal = await tok.balanceOf(a);
  await tok.connect(agent).recoverWallet(a, an);
  assert.equal(await tok.balanceOf(an), bal);
  assert.equal(await tok.isFrozen(a), true);
  await reverts(tok.connect(agent), "forcedTransfer", [an, await mallory.getAddress(), E(1), "court order"], "TransferRestricted");
  await tok.connect(agent).forcedTransfer(an, b, E(1), "DIFC court order #123");
});

test("holder-of-record cap is enforced", async () => {
  await comp.setCaps(await tok.holderCount(), 2500);
  const r = reg.connect(agent);
  const w = s[10];
  await r.registerIdentity(await w.getAddress(), ethers.id("kyc:w"), UAE, CAT.Professional, (await now()) + YEAR);
  assert.equal(await code(await bob.getAddress(), await w.getAddress(), E(1)), 9);
  await comp.setCaps(2000, 2500);
});
