// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./Roles.sol";

/// @title IdentityRegistry
/// @notice ERC-3643-style registry: maps wallets to off-chain-verified investors.
///         Only a hash of the investor's KYC file sits on-chain, never personal data.
contract IdentityRegistry is Roles {
    enum Category { None, Professional, Qualified, Employee, Custodian }

    struct Identity {
        bytes32 kycHash;     // hash of KYC dossier held by the licensed agent (no PII on-chain)
        uint16 country;      // ISO 3166-1 numeric, e.g. 784 = UAE
        Category category;
        uint64 kycExpiry;    // unix seconds; transfers fail after this
        bool exists;
    }

    mapping(address => Identity) private _ids;
    uint256 public verifiedCount;

    event IdentityRegistered(address indexed wallet, uint16 country, Category category, uint64 kycExpiry);
    event IdentityUpdated(address indexed wallet, uint16 country, Category category, uint64 kycExpiry);
    event IdentityRemoved(address indexed wallet);

    error AlreadyRegistered();
    error NotRegistered();
    error InvalidCategory();

    function registerIdentity(address wallet, bytes32 kycHash, uint16 country_, Category category_, uint64 kycExpiry)
        external
        onlyAgent
    {
        if (wallet == address(0)) revert ZeroAddress();
        if (_ids[wallet].exists) revert AlreadyRegistered();
        if (category_ == Category.None) revert InvalidCategory();
        _ids[wallet] = Identity(kycHash, country_, category_, kycExpiry, true);
        verifiedCount++;
        emit IdentityRegistered(wallet, country_, category_, kycExpiry);
    }

    function updateIdentity(address wallet, bytes32 kycHash, uint16 country_, Category category_, uint64 kycExpiry)
        external
        onlyAgent
    {
        if (!_ids[wallet].exists) revert NotRegistered();
        if (category_ == Category.None) revert InvalidCategory();
        _ids[wallet] = Identity(kycHash, country_, category_, kycExpiry, true);
        emit IdentityUpdated(wallet, country_, category_, kycExpiry);
    }

    function removeIdentity(address wallet) external onlyAgent {
        if (!_ids[wallet].exists) revert NotRegistered();
        delete _ids[wallet];
        verifiedCount--;
        emit IdentityRemoved(wallet);
    }

    function contains(address wallet) external view returns (bool) {
        return _ids[wallet].exists;
    }

    function isVerified(address wallet) public view returns (bool) {
        Identity storage id = _ids[wallet];
        return id.exists && id.kycExpiry >= block.timestamp;
    }

    function identity(address wallet) external view returns (Identity memory) {
        return _ids[wallet];
    }

    function category(address wallet) external view returns (Category) {
        return _ids[wallet].category;
    }

    function country(address wallet) external view returns (uint16) {
        return _ids[wallet].country;
    }
}
