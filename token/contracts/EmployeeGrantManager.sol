// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./Roles.sol";
import "./IdentityRegistry.sol";
import "./RegulatedEquityToken.sol";

/// @title EmployeeGrantManager
/// @notice Issues new equity to new employees with vesting, inside a hard dilution ceiling.
///         Ethics built in:
///         - pool cap: grants can never exceed the board-approved pool (dilution is bounded and public)
///         - vested tokens can never be clawed back; revocation only cancels the unvested part
///         - every grant is tied to a verified identity in the Employee category
///         - the employee, not the company, decides when to claim vested tokens
contract EmployeeGrantManager is Roles {
    struct Grant {
        address employee;
        uint128 total;
        uint128 released;
        uint64 start;
        uint32 cliff;      // seconds
        uint32 duration;   // seconds, total vesting period
        bool revocable;
        bool revoked;
        uint64 revokedAt;
    }

    RegulatedEquityToken public immutable token;
    IdentityRegistry public immutable registry;
    uint256 public immutable poolCap;     // board-approved maximum ever issued through this manager
    uint256 public poolIssued;            // total minted into grants (net of cancelled unvested)
    Grant[] public grants;

    event GrantCreated(uint256 indexed id, address indexed employee, uint256 amount, uint64 start, uint32 cliff,
        uint32 duration, string role);
    event Released(uint256 indexed id, address indexed employee, uint256 amount);
    event Revoked(uint256 indexed id, uint256 unvestedCancelled, uint256 vestedKept);

    error NotEmployee();
    error PoolExhausted(uint256 requested, uint256 remaining);
    error NothingToRelease();
    error NotRevocable();
    error NotGrantee();
    error BadSchedule();

    constructor(RegulatedEquityToken token_, IdentityRegistry registry_, uint256 poolCap_) {
        token = token_;
        registry = registry_;
        poolCap = poolCap_;
    }

    /// @notice HR / issuer creates a grant for a newly joined, KYC'd employee. Tokens are minted into escrow here.
    function createGrant(address employee, uint128 amount, uint64 start, uint32 cliff, uint32 duration, bool revocable,
        string calldata role) external onlyAgent returns (uint256 id)
    {
        if (!registry.isVerified(employee) || registry.category(employee) != IdentityRegistry.Category.Employee) {
            revert NotEmployee();
        }
        if (duration == 0 || cliff > duration) revert BadSchedule();
        if (poolIssued + amount > poolCap) revert PoolExhausted(amount, poolCap - poolIssued);
        poolIssued += amount;
        token.mint(address(this), amount, string.concat("Employee grant: ", role));
        id = grants.length;
        grants.push(Grant(employee, amount, 0, start, cliff, duration, revocable, false, 0));
        emit GrantCreated(id, employee, amount, start, cliff, duration, role);
    }

    function vestedAmount(uint256 id) public view returns (uint256) {
        Grant storage g = grants[id];
        if (g.revoked) return g.total; // total was cut to the vested amount at revocation
        uint256 t = block.timestamp;
        if (t < g.start + g.cliff) return 0;
        if (t >= g.start + g.duration) return g.total;
        return uint256(g.total) * (t - g.start) / g.duration;
    }

    function releasable(uint256 id) public view returns (uint256) {
        return vestedAmount(id) - grants[id].released;
    }

    /// @notice Employee claims vested tokens. They stay subject to the employee lock-up in Compliance.
    function release(uint256 id) external {
        Grant storage g = grants[id];
        if (msg.sender != g.employee && !isAgent[msg.sender] && msg.sender != owner) revert NotGrantee();
        uint256 amt = releasable(id);
        if (amt == 0) revert NothingToRelease();
        g.released += uint128(amt);
        token.transfer(g.employee, amt);
        emit Released(id, g.employee, amt);
    }

    /// @notice Leaver: cancel the UNVESTED part only. Vested tokens remain claimable by the employee.
    function revoke(uint256 id) external onlyAgent {
        Grant storage g = grants[id];
        if (!g.revocable || g.revoked) revert NotRevocable();
        uint256 vested = vestedAmount(id);
        uint256 unvested = g.total - vested;
        g.revoked = true;
        g.revokedAt = uint64(block.timestamp);
        g.total = uint128(vested);
        poolIssued -= unvested;
        if (unvested > 0) token.burn(address(this), unvested, "Unvested grant cancelled on departure");
        emit Revoked(id, unvested, vested);
    }

    function grantCount() external view returns (uint256) {
        return grants.length;
    }

    function poolRemaining() external view returns (uint256) {
        return poolCap - poolIssued;
    }
}
