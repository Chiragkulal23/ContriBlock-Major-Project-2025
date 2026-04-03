import json
import os
from web3 import Web3
from solcx import compile_standard, install_solc
from dotenv import load_dotenv

# Solidity version compatible with Ganache
SOLIDITY_VERSION = "0.8.17"

def load_source() -> str:
    return """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract ContriToken {
    string public name = "ContriToken";
    string public symbol = "CON";
    uint8 public decimals = 18;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    event Transfer(address indexed from, address indexed to, uint256 value);

    // Store submitted IPFS hashes for simple on-chain reference
    event HashSaved(address indexed submitter, string ipfsHash);
    event ContributionSaved(string ipfsHash, uint256 userId);
    mapping(address => string[]) private _savedHashesByUser;
    string[] private _allHashes;

    constructor(uint256 initialSupply) {
        totalSupply = initialSupply;
        balanceOf[msg.sender] = initialSupply;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    // Saves an IPFS hash (CID) on-chain and emits an event for indexing
    function saveHash(string calldata ipfsHash) external {
        _savedHashesByUser[msg.sender].push(ipfsHash);
        _allHashes.push(ipfsHash);
        emit HashSaved(msg.sender, ipfsHash);
    }

    // Saves an IPFS hash with user ID reference on-chain
    function saveHashWithUser(string calldata ipfsHash, uint256 userId) external {
        _savedHashesByUser[msg.sender].push(ipfsHash);
        _allHashes.push(ipfsHash);
        emit ContributionSaved(ipfsHash, userId);
    }

    function getUserHashes(address user) external view returns (string[] memory) {
        return _savedHashesByUser[user];
    }

    function getAllHashes() external view returns (string[] memory) {
        return _allHashes;
    }
}
"""

def main():
    # Load .env from backend root
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(dotenv_path)

    install_solc(SOLIDITY_VERSION)

    source = load_source()
    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {"ContriToken.sol": {"content": source}},
            "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}},
        },
        solc_version=SOLIDITY_VERSION,
    )

    abi = compiled["contracts"]["ContriToken.sol"]["ContriToken"]["abi"]
    bytecode = compiled["contracts"]["ContriToken.sol"]["ContriToken"]["evm"]["bytecode"]["object"]

    rpc = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
    pk = os.getenv("DEPLOYER_PRIVATE_KEY")
    if not pk:
        raise SystemExit("❌ DEPLOYER_PRIVATE_KEY missing in .env")

    w3 = Web3(Web3.HTTPProvider(rpc))
    acct = w3.eth.account.from_key(pk)
    nonce = w3.eth.get_transaction_count(acct.address)

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    initial_supply = 1_000_000 * 10**18

    tx = contract.constructor(initial_supply).build_transaction({
        "from": acct.address,
        "nonce": nonce,
        "gas": 6_000_000,
        "maxFeePerGas": w3.to_wei("2", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
        "chainId": w3.eth.chain_id,
    })

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # Save ABI + deployed address
    build_dir = os.path.join(os.path.dirname(__file__), "build")
    os.makedirs(build_dir, exist_ok=True)
    with open(os.path.join(build_dir, "contract.json"), "w") as f:
        json.dump({"address": receipt.contractAddress, "abi": abi}, f, indent=4)

    print("✅ Contract deployed at:", receipt.contractAddress)
    print("📄 ABI saved in build/contract.json")
    print("🔗 You can now update your .env CONTRACT_ADDRESS with this value")

if __name__ == "__main__":
    main()
