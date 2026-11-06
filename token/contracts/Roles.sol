// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @title Roles
/// @notice Minimal two-tier access control shared by every contract in the suite.
///         owner  = issuer board / multisig (sets rules, appoints agents)
///         agents = regulated transfer agent, HR grant manager, compliance officer
abstract contract Roles {
    address public owner;
    mapping(address => bool) public isAgent;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event AgentAdded(address indexed agent);
    event AgentRemoved(address indexed agent);

    error NotOwner();
    error NotAgent();
    error ZeroAddress();

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyAgent() {
        if (!isAgent[msg.sender] && msg.sender != owner) revert NotAgent();
        _;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function addAgent(address agent) external onlyOwner {
        if (agent == address(0)) revert ZeroAddress();
        isAgent[agent] = true;
        emit AgentAdded(agent);
    }

    function removeAgent(address agent) external onlyOwner {
        isAgent[agent] = false;
        emit AgentRemoved(agent);
    }
}
