from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.extensions import db
from backend.api import api_bp
from backend.models.user import User
from backend.models.contribution import Contribution
from backend.models.purchase import Purchase
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from collections import defaultdict


@api_bp.get("/dashboard/stats")
@jwt_required()
def get_dashboard_stats():
    """Get user-specific dashboard statistics"""
    try:
        uid_str = get_jwt_identity()
        if not uid_str:
            return jsonify({"error": "User not authenticated"}), 401
        
        uid = int(uid_str)
        user = User.query.get(uid)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        print(f"[Dashboard] Fetching stats for user ID: {uid}, Email: {user.email}")
        
        # Get all user contributions ordered by most recent first
        contributions = Contribution.query.filter_by(author_id=uid).order_by(Contribution.created_at.desc()).all()
        
        print(f"[Dashboard] Found {len(contributions)} contributions for user {uid}")
        
        # Calculate metrics
        total_contributions = len(contributions)
        
        # Calculate impact score: citations * 10 + rewards * 5 + accepted contributions * 20
        total_citations = sum(c.citations or 0 for c in contributions)
        total_rewards = sum(c.reward_amount or 0.0 for c in contributions)
        accepted_count = len([c for c in contributions if c.status == "Accepted"])
        impact_score = int(total_citations * 10 + total_rewards * 5 + accepted_count * 20)
        
        # Tokens earned (from user balance)
        tokens_earned = user.cnri_balance or 0.0
        
        # Active projects (contributions with status Accepted or Pending)
        active_projects = len([c for c in contributions if c.status in ["Accepted", "Pending"]])
        
        # Get contribution status breakdown
        status_breakdown = defaultdict(int)
        for c in contributions:
            status_breakdown[c.status or "Pending"] += 1
        
        # Get monthly contribution data for chart (last 6 months)
        six_months_ago = datetime.now() - timedelta(days=180)
        monthly_data = defaultdict(int)
        
        for c in contributions:
            if c.created_at and c.created_at >= six_months_ago:
                month_key = c.created_at.strftime("%b")
                # Calculate impact for this month: citations + rewards
                month_impact = (c.citations or 0) * 10 + (c.reward_amount or 0.0) * 5
                monthly_data[month_key] += month_impact
        
        # Generate chart data for last 6 months
        months = []
        current_date = datetime.now()
        for i in range(5, -1, -1):  # Last 6 months
            month_date = current_date - timedelta(days=30 * i)
            month_key = month_date.strftime("%b")
            months.append({
                "month": month_key,
                "impact": monthly_data.get(month_key, 0)
            })
        
        # Get recent activity (last 10 contributions)
        recent_contributions = Contribution.query.filter_by(author_id=uid)\
            .order_by(Contribution.created_at.desc()).limit(10).all()
        
        recent_activity = []
        for c in recent_contributions:
            # Determine activity type based on status
            if c.status == "Accepted":
                action = "Contribution approved"
            elif c.status == "Pending":
                action = "Contribution submitted"
            elif c.status == "Rejected":
                action = "Contribution rejected"
            elif c.status == "Duplicate":
                action = "Duplicate contribution detected"
            else:
                action = "Contribution updated"
            
            # Calculate time ago
            if c.created_at:
                time_diff = datetime.now() - c.created_at
                if time_diff.days > 0:
                    time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
                elif time_diff.seconds >= 3600:
                    hours = time_diff.seconds // 3600
                    time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
                else:
                    minutes = time_diff.seconds // 60
                    time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago" if minutes > 0 else "Just now"
            else:
                time_ago = "Unknown"
            
            recent_activity.append({
                "action": action,
                "project": c.title,
                "time": time_ago,
                "contributionId": c.id,
                "status": c.status
            })
        
        # Get top contributions by citations
        top_contributions = sorted(
            [c for c in contributions if c.citations and c.citations > 0],
            key=lambda x: x.citations or 0,
            reverse=True
        )[:5]
        
        top_contributions_data = [c.to_card() for c in top_contributions]
        
        # Get contributions that can claim rewards
        claimable_contributions = [c for c in contributions if c.status == "Accepted" and c.reward_amount and c.reward_amount > 0]
        
        # Get user's latest contributions (already ordered by created_at desc)
        user_contributions_data = [c.to_card() for c in contributions[:10]]
        
        print(f"[Dashboard] Returning stats: {total_contributions} contributions, {impact_score} impact score, {tokens_earned} tokens")
        
        return jsonify({
            "totalContributions": total_contributions,
            "impactScore": impact_score,
            "tokensEarned": tokens_earned,
            "activeProjects": active_projects,
            "totalCitations": total_citations,
            "totalRewards": total_rewards,
            "statusBreakdown": dict(status_breakdown),
            "chartData": months,
            "recentActivity": recent_activity,
            "topContributions": top_contributions_data,
            "claimableCount": len(claimable_contributions),
            "userContributions": user_contributions_data
        })
    except ValueError as e:
        print(f"[Dashboard] Error converting user ID: {e}")
        return jsonify({"error": "Invalid user ID"}), 400
    except Exception as e:
        print(f"[Dashboard] Error fetching dashboard stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

