from flask import request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.api import api_bp
from backend.extensions import db
from backend.models.contribution import Contribution
from backend.models.user import User
from backend.models.purchase import Purchase
from datetime import datetime
from sqlalchemy import text
import os


@api_bp.get("/marketplace")
def marketplace_list():
    """Get all verified (Accepted) contributions for marketplace display."""
    try:
        # Get all accepted contributions that are available for purchase
        contributions = Contribution.query.filter_by(status="Accepted").all()
        
        marketplace_items = []
        for contrib in contributions:
            # Only show contributions that have IPFS content
            if contrib.ipfs_cid:
                item = {
                    "id": str(contrib.id),
                    "title": contrib.title,
                    "description": contrib.description[:200] + "..." if len(contrib.description) > 200 else contrib.description,
                    "contributor": contrib.author.email,
                    "contributorWallet": contrib.author.email,  # Using email as wallet address for now
                    "cid": contrib.ipfs_cid,
                    "citations": contrib.citations or 0,
                    "price": 100,  # Fixed price of 100 CTRI tokens
                    "status": "Available",
                    "createdAt": contrib.created_at.isoformat() if contrib.created_at else None,
                    "fileSize": contrib.ipfs_file_size,
                    "fileUrl": contrib.file_url
                }
                marketplace_items.append(item)
        
        return jsonify(marketplace_items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.get("/marketplace/purchased")
@jwt_required()
def get_purchased_contributions():
    """Get contributions purchased by the current user."""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Get all purchases for this user
        purchases = Purchase.query.filter_by(user_id=user_id).all()
        
        purchased_items = []
        for purchase in purchases:
            contribution = purchase.contribution
            if contribution and contribution.status == "Accepted":
                item = {
                    "id": str(contribution.id),
                    "title": contribution.title,
                    "description": contribution.description[:200] + "..." if len(contribution.description) > 200 else contribution.description,
                    "contributor": contribution.author.email,
                    "contributorWallet": contribution.author.email,
                    "cid": contribution.ipfs_cid,
                    "citations": contribution.citations or 0,
                    "price": purchase.purchase_price,
                    "status": "Purchased",
                    "createdAt": contribution.created_at.isoformat() if contribution.created_at else None,
                    "fileSize": contribution.ipfs_file_size,
                    "fileUrl": contribution.file_url,
                    "purchaseDate": purchase.created_at.isoformat() if purchase.created_at else None
                }
                purchased_items.append(item)
        
        return jsonify(purchased_items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.post("/marketplace/purchase")
@jwt_required()
def marketplace_purchase():
    """Purchase a contribution for 100 CTRI tokens."""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        data = request.get_json() or {}
        contribution_id_str = data.get("contributionId") or data.get("contribution_id")
        
        print(f"[Purchase] Received purchase request from user {user_id} for contribution {contribution_id_str}")
        
        if not contribution_id_str:
            return jsonify({"error": "Contribution ID is required"}), 400
            
        try:
            contribution_id = int(contribution_id_str)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid Contribution ID format"}), 400
            
        # Get the contribution - use get_or_404 to ensure it exists
        contribution = Contribution.query.get(contribution_id)
        
        if not contribution:
            print(f"[Purchase] ERROR: Contribution {contribution_id} not found")
            return jsonify({"error": "Contribution not found"}), 404
            
        if contribution.status != "Accepted":
            print(f"[Purchase] ERROR: Contribution {contribution_id} status is {contribution.status}, not Accepted")
            return jsonify({"error": "Contribution not available for purchase"}), 404

        # Check if user already purchased this contribution
        existing_purchase = Purchase.query.filter_by(user_id=user_id, contribution_id=contribution_id).first()
        if existing_purchase:
            print(f"[Purchase] ERROR: User {user_id} already purchased contribution {contribution_id}")
            return jsonify({"error": "You have already purchased this contribution"}), 400

        # Check user balance (assuming 100 CTRI is the fixed price)
        user_balance = float(user.cnri_balance) if user.cnri_balance is not None else 0.0
        print(f"[Purchase] User {user_id} balance: {user_balance} CTRI")
        if user_balance < 100:
            return jsonify({
                "success": False,
                "error": "Insufficient funds. You need at least 100 CTRI tokens to purchase this contribution."
            }), 400

        # Deduct tokens and create purchase record
        try:
            # Get the original contributor (author) - refresh to ensure we have the latest data
            original_contributor = contribution.author
            if not original_contributor:
                return jsonify({"error": "Contribution author not found"}), 404
            
            # Create purchase record
            new_purchase = Purchase(
                user_id=user_id,
                contribution_id=contribution_id,
                purchase_price=100,
                created_at=datetime.utcnow()
            )
            
            # Deduct 100 CTRI from buyer
            current_balance = float(user.cnri_balance) if user.cnri_balance is not None else 0.0
            user.cnri_balance = current_balance - 100.0
            
            # Get current citations count (handle None case)
            current_citations = int(contribution.citations) if contribution.citations is not None else 0
            new_citations = current_citations + 1
            
            # First, ensure citations column exists (for SQLite compatibility)
            try:
                # Check if column exists by trying to query it
                test_result = db.session.execute(
                    text("SELECT citations FROM contributions WHERE id = :contrib_id LIMIT 1"),
                    {"contrib_id": contribution_id}
                ).fetchone()
                print(f"[Purchase] Current citations from DB: {test_result[0] if test_result else 'None'}")
            except Exception as col_check_error:
                # Column might not exist, try to add it
                print(f"[Purchase] Citations column check failed: {col_check_error}. Attempting to add column...")
                try:
                    db.session.execute(text("ALTER TABLE contributions ADD COLUMN citations INTEGER DEFAULT 0"))
                    db.session.commit()
                    print(f"[Purchase] Successfully added citations column")
                except Exception as add_col_error:
                    print(f"[Purchase] Could not add citations column: {add_col_error}")
            
            # Update citations using direct SQL (most reliable)
            db.session.execute(
                text("UPDATE contributions SET citations = :new_citations WHERE id = :contrib_id"),
                {"new_citations": new_citations, "contrib_id": contribution_id}
            )
            print(f"[Purchase] SQL Update - Incrementing citations for contribution {contribution_id}: {current_citations} -> {new_citations}")
            
            # Also update the ORM object to keep it in sync
            contribution.citations = new_citations
            
            # Reward the original contributor with 100 CTRI tokens
            contributor_balance = float(original_contributor.cnri_balance) if original_contributor.cnri_balance is not None else 0.0
            new_contributor_balance = contributor_balance + 100.0
            original_contributor.cnri_balance = new_contributor_balance
            print(f"[Purchase] Rewarding contributor {original_contributor.id} ({original_contributor.email}): {contributor_balance} -> {new_contributor_balance} CTRI")
            
            # Add all changes to session
            db.session.add(new_purchase)
            db.session.add(user)
            db.session.add(contribution)
            db.session.add(original_contributor)
            
            # Commit all changes in a single transaction
            db.session.commit()
            print(f"[Purchase] Transaction committed successfully")
            
            # Expire all objects to force fresh query
            db.session.expire_all()
            
            # Re-query to verify changes were saved
            updated_contribution = Contribution.query.get(contribution_id)
            updated_contributor = User.query.get(original_contributor.id)
            updated_user = User.query.get(user_id)
            
            # Get final values (with null checks)
            if not updated_contribution:
                print(f"[Purchase] ERROR: Could not re-query contribution {contribution_id}")
                updated_contribution = contribution
            if not updated_contributor:
                print(f"[Purchase] ERROR: Could not re-query contributor {original_contributor.id}")
                updated_contributor = original_contributor
            if not updated_user:
                print(f"[Purchase] ERROR: Could not re-query user {user_id}")
                updated_user = user
            
            final_citations = int(updated_contribution.citations) if updated_contribution and updated_contribution.citations is not None else new_citations
            final_contributor_balance = float(updated_contributor.cnri_balance) if updated_contributor and updated_contributor.cnri_balance is not None else new_contributor_balance
            final_user_balance = float(updated_user.cnri_balance) if updated_user and updated_user.cnri_balance is not None else float(user.cnri_balance)
            
            print(f"[Purchase] Verification - Citations: {final_citations}, Contributor balance: {final_contributor_balance} CTRI, User balance: {final_user_balance} CTRI")
            
            # If citations still didn't update, force update one more time
            if final_citations != new_citations:
                print(f"[Purchase] WARNING: Citations mismatch! Expected {new_citations}, got {final_citations}. Force updating...")
                db.session.execute(
                    text("UPDATE contributions SET citations = :new_citations WHERE id = :contrib_id"),
                    {"new_citations": new_citations, "contrib_id": contribution_id}
                )
                db.session.commit()
                db.session.expire_all()
                updated_contribution = Contribution.query.get(contribution_id)
                final_citations = int(updated_contribution.citations) if updated_contribution.citations is not None else 0
                print(f"[Purchase] Force update complete - Citations now: {final_citations}")
            
            # Return updated balance and citations (use re-queried values)
            return jsonify({
                "success": True, 
                "message": "Purchase successful. Contributor received 100 CTRI tokens.",
                "newBalance": float(updated_user.cnri_balance) if updated_user else float(user.cnri_balance),
                "purchasedContributionId": str(contribution_id),
                "citations": final_citations,
                "contributorReward": 100.0,
                "contributorBalance": final_contributor_balance
            })
        except Exception as db_error:
            db.session.rollback()
            import traceback
            error_details = traceback.format_exc()
            print(f"[Purchase] Database error: {error_details}")
            return jsonify({
                "success": False,
                "error": f"Database error: {str(db_error)}"
            }), 500
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"[Purchase] Purchase error: {error_details}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.get("/marketplace/contribution/<int:contribution_id>")
@jwt_required(optional=True)
def get_marketplace_contribution(contribution_id):
    """Get detailed information about a marketplace contribution."""
    try:
        contribution = Contribution.query.get_or_404(contribution_id)
        
        # Check if user has purchased this contribution (if authenticated)
        is_purchased = False
        is_contributor = False
        user_id = None
        try:
            user_id = get_jwt_identity()
            if user_id:
                user_id = int(user_id)
                # Check if user is the contributor (author) of this contribution
                # Ensure both are integers for proper comparison
                is_contributor = int(contribution.author_id) == int(user_id)
                # If not contributor, check if they purchased it
                if not is_contributor:
                    purchase = Purchase.query.filter_by(
                        user_id=user_id,
                        contribution_id=contribution_id
                    ).first()
                    is_purchased = purchase is not None
        except:
            pass  # User not authenticated or invalid token
        
        # Only require "Accepted" status for non-contributors viewing the contribution
        # Contributors can view their own contributions regardless of status
        if not is_contributor and contribution.status != "Accepted":
            return jsonify({"error": "Contribution is not available"}), 404
            
        return jsonify({
            "id": str(contribution.id),
            "title": contribution.title,
            "description": contribution.description,
            "contributor": contribution.author.email,
            "contributorWallet": contribution.author.email,
            "cid": contribution.ipfs_cid,
            "citations": contribution.citations or 0,
            "price": 100,
            "createdAt": contribution.created_at.isoformat() if contribution.created_at else None,
            "fileSize": contribution.ipfs_file_size,
            "fileUrl": contribution.file_url,
            "status": "Available",
            "is_purchased": is_purchased,
            "is_contributor": is_contributor
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.get("/marketplace/download/<int:contribution_id>")
@jwt_required()
def download_purchased_contribution(contribution_id):
    """Download a purchased contribution file."""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Get the contribution first
        contribution = Contribution.query.get(contribution_id)
        if not contribution:
            return jsonify({"error": "Contribution not found"}), 404
        
        # Check if user is the contributor (author) of this contribution
        # Ensure both are integers for proper comparison
        is_contributor = int(contribution.author_id) == int(user_id)
        
        # If user is the contributor, allow download regardless of status
        if is_contributor:
            # Contributors can always download their own contributions
            pass
        else:
            # For non-contributors, contribution must be Accepted and purchased
            if contribution.status != "Accepted":
                return jsonify({"error": "Contribution is not available"}), 404
            
            purchase = Purchase.query.filter_by(
                user_id=user_id, 
                contribution_id=contribution_id
            ).first()
            
            if not purchase:
                return jsonify({"error": "You have not purchased this contribution"}), 403
            
        # Get the file path
        if not contribution.file_url:
            return jsonify({"error": "File not found for this contribution"}), 404
            
        # Extract filename from the file URL
        # Handle both /api/uploads/filename and just filename
        file_url = contribution.file_url
        if file_url.startswith('/api/uploads/'):
            filename = file_url.replace('/api/uploads/', '')
        elif file_url.startswith('/'):
            filename = file_url.lstrip('/')
        else:
            filename = os.path.basename(file_url)
        
        # Get upload folder - use current_app which should be available in Flask context
        # If not available, fallback to Config
        try:
            upload_folder = current_app.config["UPLOAD_FOLDER"]
        except (RuntimeError, KeyError):
            # Fallback to Config if current_app is not in context
            from backend.config import Config
            upload_folder = Config.UPLOAD_FOLDER
        
        # Construct full file path
        file_path = os.path.join(upload_folder, filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            # Try with just the filename if the path doesn't work
            alt_filename = os.path.basename(filename)
            alt_path = os.path.join(upload_folder, alt_filename)
            if os.path.exists(alt_path):
                file_path = alt_path
                filename = alt_filename
            else:
                return jsonify({
                    "error": "File not found on server",
                    "details": f"Looked for: {file_path} and {alt_path}"
                }), 404
        
        # Serve the file using send_from_directory
        # send_from_directory needs the directory path and filename
        return send_from_directory(upload_folder, os.path.basename(file_path), as_attachment=True)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Download error: {error_details}")
        return jsonify({"error": str(e)}), 500


@api_bp.post("/marketplace/admin/update-citations")
@jwt_required()
def update_all_citations():
    """Admin endpoint to update all citations based on purchases"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or user.role != "admin":
            return jsonify({"error": "Forbidden. Admin access required."}), 403
        
        # Count purchases per contribution and update citations
        purchase_counts = db.session.execute(
            text("""
                SELECT contribution_id, COUNT(*) as purchase_count
                FROM purchases
                GROUP BY contribution_id
            """)
        ).fetchall()
        
        updated_count = 0
        for contrib_id, purchase_count in purchase_counts:
            try:
                db.session.execute(
                    text("UPDATE contributions SET citations = :count WHERE id = :contrib_id"),
                    {"count": purchase_count, "contrib_id": contrib_id}
                )
                updated_count += 1
            except Exception as e:
                print(f"Error updating contribution {contrib_id}: {e}")
        
        # Set citations to 0 for contributions with no purchases
        db.session.execute(text("""
            UPDATE contributions 
            SET citations = 0 
            WHERE id NOT IN (SELECT DISTINCT contribution_id FROM purchases)
            AND (citations IS NULL OR citations != 0)
        """))
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Updated citations for {updated_count} contributions",
            "updated_count": updated_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


