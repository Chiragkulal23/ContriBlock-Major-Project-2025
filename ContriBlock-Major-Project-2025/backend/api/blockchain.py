from flask import jsonify
from flask_jwt_extended import jwt_required
from backend.api import api_bp
import json
from backend.config import Config
from web3 import Web3


@api_bp.get("/blockchain/status")
@jwt_required(optional=True)
def bc_status():
    """Check if Ganache is running and accessible"""
    try:
        w3 = Web3(Web3.HTTPProvider(Config.GANACHE_URL))
        # Try to get latest block to verify connection
        latest_block = w3.eth.get_block('latest')
        return jsonify({
            "connected": True,
            "url": Config.GANACHE_URL,
            "latestBlock": latest_block.number if latest_block else None,
            "chainId": w3.eth.chain_id if hasattr(w3.eth, 'chain_id') else None
        })
    except Exception as e:
        return jsonify({
            "connected": False,
            "url": Config.GANACHE_URL,
            "error": str(e),
            "message": "Ganache is not running. Please start Ganache to enable blockchain transactions."
        }), 503


@api_bp.get("/contract-info")
@jwt_required(optional=True)
def contract_info():
    """Get contract ABI and address for frontend"""
    try:
        with open(Config.CONTRACT_ABI_PATH, "r") as f:
            data = json.load(f)
        
        return jsonify({
            "address": Config.CONTRACT_ADDRESS or data.get("address"),
            "abi": data["abi"],
            "rpcUrl": Config.GANACHE_URL
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


