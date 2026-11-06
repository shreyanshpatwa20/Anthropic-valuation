// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./Roles.sol";
import "./IdentityRegistry.sol";
import "./Compliance.sol";

/// @title RegulatedEquityToken
/// @notice ERC-20-compatible permissioned security token following the ERC-3643 (T-REX) pattern:
///         - every transfer passes Compliance (identity, jurisdiction, lock-up, caps)
///         - ERC-1404 restriction codes explain failures in plain language
///         - ERC-1643-style document registry anchors the prospectus and valuation model by hash
///         - NAV per token is published on-chain with a source hash and a per-update move limit
///         Every privileged action (mint, burn, forced transfer, freeze, recovery) emits a reason.
contract RegulatedEquityToken is Roles {
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    uint256 public totalSupply;
    uint256 public holderCount;
    bool public paused;

    IdentityRegistry public immutable registry;
    Compliance public immutable compliance;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    mapping(address => bool) public isFrozen;
    mapping(address => uint256) public frozenTokens;

    // ---- NAV oracle ----
    address public valuationAgent;
    uint256 public navPerToken;      // USD with 6 decimals ($5.88 = 5_880_000)
    uint64 public navTimestamp;
    bytes32 public navSourceHash;    // hash of the valuation model version that produced the NAV
    uint16 public maxNavMoveBps;     // largest single-update move without owner sign-off

    // ---- documents (ERC-1643 style) ----
    struct Document { string uri; bytes32 hash; uint64 updated; }
    mapping(bytes32 => Document) public documents;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Issued(address indexed to, uint256 amount, string reason);
    event Redeemed(address indexed from, uint256 amount, string reason);
    event ForcedTransfer(address indexed from, address indexed to, uint256 amount, string reason);
    event AddressFrozen(address indexed wallet, bool frozen, string reason);
    event TokensFrozen(address indexed wallet, uint256 amount, string reason);
    event TokensUnfrozen(address indexed wallet, uint256 amount, string reason);
    event WalletRecovered(address indexed lostWallet, address indexed newWallet, uint256 amount);
    event Paused(bool paused, string reason);
    event NavUpdated(uint256 navPerToken, uint64 timestamp, bytes32 sourceHash);
    event DocumentUpdated(bytes32 indexed name, string uri, bytes32 hash);
    event ValuationAgentSet(address agent);

    error TransferRestricted(uint8 code, string reason);
    error InsufficientAllowance();
    error InsufficientBalance();
    error NotValuationAgent();
    error NavMoveTooLarge(uint256 previous, uint256 proposed);
    error ReasonRequired();

    constructor(
        string memory name_,
        string memory symbol_,
        IdentityRegistry registry_,
        Compliance compliance_,
        uint16 maxNavMoveBps_
    ) {
        name = name_;
        symbol = symbol_;
        registry = registry_;
        compliance = compliance_;
        maxNavMoveBps = maxNavMoveBps_;
    }

    // ------------------------------------------------------------------ ERC-20
    function transfer(address to, uint256 amount) external returns (bool) {
        _checkedTransfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 a = allowance[from][msg.sender];
        if (a < amount) revert InsufficientAllowance();
        if (a != type(uint256).max) allowance[from][msg.sender] = a - amount;
        _checkedTransfer(from, to, amount);
        return true;
    }

    // ------------------------------------------------------------------ ERC-1404
    function detectTransferRestriction(address from, address to, uint256 amount) public view returns (uint8) {
        return compliance.check(from, to, amount);
    }

    function messageForTransferRestriction(uint8 code) external view returns (string memory) {
        return compliance.message(code);
    }

    // ------------------------------------------------------------------ issuer / agent actions
    function mint(address to, uint256 amount, string calldata reason) external onlyAgent {
        if (bytes(reason).length == 0) revert ReasonRequired();
        uint8 code = compliance.checkMint(to, amount);
        if (code != 0) revert TransferRestricted(code, compliance.message(code));
        _move(address(0), to, amount);
        emit Issued(to, amount, reason);
    }

    function burn(address from, uint256 amount, string calldata reason) external onlyAgent {
        if (bytes(reason).length == 0) revert ReasonRequired();
        if (balanceOf[from] - frozenTokens[from] < amount) revert InsufficientBalance();
        _move(from, address(0), amount);
        emit Redeemed(from, amount, reason);
    }

    /// @notice Court order / regulator instruction. Recipient must still be a verified investor.
    function forcedTransfer(address from, address to, uint256 amount, string calldata reason) external onlyAgent {
        if (bytes(reason).length == 0) revert ReasonRequired();
        if (!registry.isVerified(to)) revert TransferRestricted(5, compliance.message(5));
        if (balanceOf[from] < amount) revert InsufficientBalance();
        uint256 free = balanceOf[from] - frozenTokens[from];
        if (amount > free) frozenTokens[from] -= (amount - free);
        _move(from, to, amount);
        emit ForcedTransfer(from, to, amount, reason);
    }

    /// @notice Lost-key recovery: moves the whole position to a new wallet of the SAME verified investor.
    function recoverWallet(address lost, address replacement) external onlyAgent {
        IdentityRegistry.Identity memory a = registry.identity(lost);
        IdentityRegistry.Identity memory b = registry.identity(replacement);
        if (!b.exists || a.kycHash != b.kycHash) revert TransferRestricted(5, "Replacement wallet is not the same investor");
        uint256 amt = balanceOf[lost];
        uint256 fr = frozenTokens[lost];
        frozenTokens[lost] = 0;
        _move(lost, replacement, amt);
        frozenTokens[replacement] += fr;
        isFrozen[lost] = true;
        emit WalletRecovered(lost, replacement, amt);
    }

    function setAddressFrozen(address wallet, bool frozen, string calldata reason) external onlyAgent {
        if (bytes(reason).length == 0) revert ReasonRequired();
        isFrozen[wallet] = frozen;
        emit AddressFrozen(wallet, frozen, reason);
    }

    function freezePartialTokens(address wallet, uint256 amount, string calldata reason) external onlyAgent {
        if (balanceOf[wallet] < frozenTokens[wallet] + amount) revert InsufficientBalance();
        frozenTokens[wallet] += amount;
        emit TokensFrozen(wallet, amount, reason);
    }

    function unfreezePartialTokens(address wallet, uint256 amount, string calldata reason) external onlyAgent {
        frozenTokens[wallet] -= amount;
        emit TokensUnfrozen(wallet, amount, reason);
    }

    function setPaused(bool p, string calldata reason) external onlyOwner {
        if (bytes(reason).length == 0) revert ReasonRequired();
        paused = p;
        emit Paused(p, reason);
    }

    // ------------------------------------------------------------------ NAV + documents
    function setValuationAgent(address agent) external onlyOwner {
        valuationAgent = agent;
        emit ValuationAgentSet(agent);
    }

    /// @notice Valuation agent publishes NAV. Moves larger than maxNavMoveBps need the owner (two-key rule).
    function publishNav(uint256 nav, bytes32 sourceHash) external {
        if (msg.sender != valuationAgent && msg.sender != owner) revert NotValuationAgent();
        if (msg.sender != owner && navPerToken != 0) {
            uint256 prev = navPerToken;
            uint256 diff = nav > prev ? nav - prev : prev - nav;
            if (diff * 10_000 > prev * maxNavMoveBps) revert NavMoveTooLarge(prev, nav);
        }
        navPerToken = nav;
        navTimestamp = uint64(block.timestamp);
        navSourceHash = sourceHash;
        emit NavUpdated(nav, navTimestamp, sourceHash);
    }

    function setDocument(bytes32 docName, string calldata uri, bytes32 docHash) external onlyOwner {
        documents[docName] = Document(uri, docHash, uint64(block.timestamp));
        emit DocumentUpdated(docName, uri, docHash);
    }

    /// @notice USD value (6 decimals) of a wallet's position at the published NAV.
    function positionValue(address wallet) external view returns (uint256) {
        return balanceOf[wallet] * navPerToken / 1e18;
    }

    // ------------------------------------------------------------------ internals
    function _checkedTransfer(address from, address to, uint256 amount) internal {
        uint8 code = compliance.check(from, to, amount);
        if (code != 0) revert TransferRestricted(code, compliance.message(code));
        _move(from, to, amount);
    }

    function _move(address from, address to, uint256 amount) internal {
        if (from == address(0)) {
            totalSupply += amount;
        } else {
            uint256 fb = balanceOf[from];
            if (fb < amount) revert InsufficientBalance();
            balanceOf[from] = fb - amount;
            if (fb == amount && amount > 0) holderCount--;
        }
        if (to == address(0)) {
            totalSupply -= amount;
        } else {
            if (balanceOf[to] == 0 && amount > 0) holderCount++;
            balanceOf[to] += amount;
        }
        emit Transfer(from, to, amount);
    }
}
