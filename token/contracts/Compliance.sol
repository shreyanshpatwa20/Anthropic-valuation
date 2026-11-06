// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./Roles.sol";
import "./IdentityRegistry.sol";

interface ITokenView {
    function balanceOf(address) external view returns (uint256);
    function totalSupply() external view returns (uint256);
    function holderCount() external view returns (uint256);
    function paused() external view returns (bool);
    function isFrozen(address) external view returns (bool);
    function frozenTokens(address) external view returns (uint256);
}

/// @title Compliance
/// @notice Rule engine checked before every transfer. Returns ERC-1404-style restriction codes so a
///         wallet, exchange or investor can see *why* a transfer is blocked, not just that it failed.
contract Compliance is Roles {
    // ---- restriction codes (ERC-1404 detectTransferRestriction) ----
    uint8 public constant OK = 0;
    uint8 public constant TOKEN_PAUSED = 1;
    uint8 public constant SENDER_FROZEN = 2;
    uint8 public constant RECIPIENT_FROZEN = 3;
    uint8 public constant SENDER_NOT_VERIFIED = 4;
    uint8 public constant RECIPIENT_NOT_VERIFIED = 5;
    uint8 public constant JURISDICTION_BLOCKED = 6;
    uint8 public constant SENDER_IN_LOCKUP = 7;
    uint8 public constant INSUFFICIENT_UNFROZEN_BALANCE = 8;
    uint8 public constant HOLDER_CAP_REACHED = 9;
    uint8 public constant CONCENTRATION_LIMIT = 10;
    uint8 public constant EMPLOYEE_SECONDARY_BUY = 11;

    IdentityRegistry public immutable registry;
    ITokenView public token;

    mapping(uint16 => bool) public allowedCountry;
    mapping(address => uint64) public lockupUntil;      // per-wallet lock-up (e.g. post-IPO 180 days)
    mapping(address => bool) public exemptFromCaps;     // SPV treasury, grant manager, custodian
    uint64 public employeeLockupUntil;                  // employees cannot sell before this
    uint256 public maxHolders;                          // e.g. 2,000 holder-of-record ceiling
    uint16 public maxHolderBps;                         // max % of supply per non-exempt wallet

    event TokenBound(address token);
    event CountrySet(uint16 country, bool allowed);
    event LockupSet(address indexed wallet, uint64 until);
    event EmployeeLockupSet(uint64 until);
    event CapsSet(uint256 maxHolders, uint16 maxHolderBps);
    event ExemptionSet(address indexed wallet, bool exempt);

    error TokenAlreadyBound();
    error BadBps();

    constructor(IdentityRegistry registry_, uint256 maxHolders_, uint16 maxHolderBps_) {
        if (maxHolderBps_ > 10_000) revert BadBps();
        registry = registry_;
        maxHolders = maxHolders_;
        maxHolderBps = maxHolderBps_;
    }

    function bindToken(ITokenView token_) external onlyOwner {
        if (address(token) != address(0)) revert TokenAlreadyBound();
        token = token_;
        exemptFromCaps[address(token_)] = true;
        emit TokenBound(address(token_));
    }

    function setCountry(uint16 c, bool allowed) external onlyOwner {
        allowedCountry[c] = allowed;
        emit CountrySet(c, allowed);
    }

    function setLockup(address wallet, uint64 until) external onlyAgent {
        lockupUntil[wallet] = until;
        emit LockupSet(wallet, until);
    }

    function setEmployeeLockup(uint64 until) external onlyOwner {
        employeeLockupUntil = until;
        emit EmployeeLockupSet(until);
    }

    function setCaps(uint256 maxHolders_, uint16 maxHolderBps_) external onlyOwner {
        if (maxHolderBps_ > 10_000) revert BadBps();
        maxHolders = maxHolders_;
        maxHolderBps = maxHolderBps_;
        emit CapsSet(maxHolders_, maxHolderBps_);
    }

    function setExempt(address wallet, bool exempt) external onlyOwner {
        exemptFromCaps[wallet] = exempt;
        emit ExemptionSet(wallet, exempt);
    }

    /// @notice Restriction code for a peer-to-peer transfer. 0 means allowed.
    function check(address from, address to, uint256 amount) public view returns (uint8) {
        if (token.paused()) return TOKEN_PAUSED;
        if (token.isFrozen(from)) return SENDER_FROZEN;
        if (token.isFrozen(to)) return RECIPIENT_FROZEN;
        if (!registry.isVerified(from)) return SENDER_NOT_VERIFIED;
        if (!registry.isVerified(to)) return RECIPIENT_NOT_VERIFIED;
        if (!allowedCountry[registry.country(from)] || !allowedCountry[registry.country(to)]) {
            return JURISDICTION_BLOCKED;
        }
        if (lockupUntil[from] > block.timestamp) return SENDER_IN_LOCKUP;
        if (registry.category(from) == IdentityRegistry.Category.Employee && employeeLockupUntil > block.timestamp) {
            return SENDER_IN_LOCKUP;
        }
        // Employees receive equity through grants, not by buying on the secondary market.
        if (registry.category(to) == IdentityRegistry.Category.Employee && !exemptFromCaps[from]) {
            return EMPLOYEE_SECONDARY_BUY;
        }
        if (token.balanceOf(from) - token.frozenTokens(from) < amount) return INSUFFICIENT_UNFROZEN_BALANCE;
        return _capCheck(to, amount, false);
    }

    /// @notice Restriction code for a new issuance (mint) to `to`.
    function checkMint(address to, uint256 amount) public view returns (uint8) {
        if (token.isFrozen(to)) return RECIPIENT_FROZEN;
        if (!registry.isVerified(to)) return RECIPIENT_NOT_VERIFIED;
        if (!allowedCountry[registry.country(to)]) return JURISDICTION_BLOCKED;
        return _capCheck(to, amount, true);
    }

    function _capCheck(address to, uint256 amount, bool isMint) internal view returns (uint8) {
        uint256 toBal = token.balanceOf(to);
        if (toBal == 0 && !exemptFromCaps[to] && token.holderCount() >= maxHolders) return HOLDER_CAP_REACHED;
        if (!exemptFromCaps[to]) {
            // Supply grows only on a mint; a peer transfer leaves it unchanged.
            uint256 supplyAfter = token.totalSupply() + (isMint ? amount : 0);
            if ((toBal + amount) * 10_000 > uint256(maxHolderBps) * supplyAfter) {
                return CONCENTRATION_LIMIT;
            }
        }
        return OK;
    }

    function message(uint8 code) public pure returns (string memory) {
        if (code == OK) return "Transfer allowed";
        if (code == TOKEN_PAUSED) return "Token is paused by the issuer";
        if (code == SENDER_FROZEN) return "Sender wallet is frozen";
        if (code == RECIPIENT_FROZEN) return "Recipient wallet is frozen";
        if (code == SENDER_NOT_VERIFIED) return "Sender is not a verified investor (or KYC expired)";
        if (code == RECIPIENT_NOT_VERIFIED) return "Recipient is not a verified investor (or KYC expired)";
        if (code == JURISDICTION_BLOCKED) return "Jurisdiction not permitted for this offering";
        if (code == SENDER_IN_LOCKUP) return "Sender tokens are in lock-up";
        if (code == INSUFFICIENT_UNFROZEN_BALANCE) return "Insufficient unfrozen balance";
        if (code == HOLDER_CAP_REACHED) return "Holder-of-record cap reached";
        if (code == CONCENTRATION_LIMIT) return "Recipient would exceed the concentration limit";
        if (code == EMPLOYEE_SECONDARY_BUY) return "Employees receive equity via grants only";
        return "Unknown restriction";
    }
}
