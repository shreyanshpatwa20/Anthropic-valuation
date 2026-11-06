# Regulated equity token (ERC-3643 pattern)

This is a permissioned security token for issuing, transferring and administering tokenized equity under UAE-style rules (FSRA / DFSA). It also includes employee grants with vesting.

| Contract | Role |
|---|---|
| `IdentityRegistry.sol` | Wallet → verified investor (KYC hash only, country, category, KYC expiry) |
| `Compliance.sol` | Rule engine run before every transfer. Returns ERC-1404 restriction codes with plain-language messages |
| `RegulatedEquityToken.sol` | ERC-20 interface + ERC-3643 agent functions: mint, burn, forced transfer, freeze, pause, lost-wallet recovery. NAV published with a source hash, two-key rule for moves >20%, ERC-1643-style document hashes |
| `EmployeeGrantManager.sol` | New-hire grants with cliff + linear vesting inside a board-approved pool cap. Revocation cancels unvested tokens only |

**Transfer rules:** token not paused · wallets not frozen · both parties verified with current KYC · both jurisdictions permitted · sender not in lock-up (employees locked until IPO + 180 days) · employees receive equity only through grants · unfrozen balance covers the amount · holder-of-record cap (2,000) · 25% concentration limit.

**Ethics guardrails:** every privileged action requires a written reason and emits an event · vested equity is never clawed back · the dilution pool is a hard on-chain ceiling · no personal data on-chain · recovery only moves a position to a wallet of the same verified investor.

```bash
cd token && npm install && npm test   # compiles with bundled solc-js 0.8.28, runs 10 tests on an in-process ganache EVM
```

`console.html` is an animated, self-contained simulation of the same rules: a register map with token flows, a step-by-step compliance gate, employee onboarding, vesting time travel and NAV publication. Its reference prices are the per-token values from `../output/model_values.json`. The demo issuer, Meridian Frontier Labs, is fictional and not affiliated with Anthropic.

Not audited. Not for production. Before mainnet you need: an external audit; a legal opinion on the FSRA / DFSA perimeter; issuer consent; a multisig owner; and an upgrade to the audited reference implementation (T-REX / ONCHAINID).
