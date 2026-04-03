import os
import sys

# Ensure project root is on sys.path so 'backend.*' imports work
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import click
from backend.app import app, db
from backend.models.user import User
from backend.models.contribution import Contribution
from backend.models.purchase import Purchase
from sqlalchemy import text, inspect, func


@click.group()
def cli():
    pass


@cli.command()
def seed():
    with app.app_context():
        if not User.query.filter_by(email="admin@example.com").first():
            u = User(name="Admin", email="admin@example.com", role="admin")
            u.set_password("admin123")
            db.session.add(u)
            db.session.commit()
            click.echo("Seeded admin user: admin@example.com / admin123")
        else:
            click.echo("Admin already exists")


@cli.command()
def migrate_kyc():
    """Add missing verified_email column to kyc_documents table"""
    with app.app_context():
        try:
            engine = db.engine
            inspector = inspect(engine)
            
            # Check if kyc_documents table exists
            if "kyc_documents" not in inspector.get_table_names():
                click.echo("kyc_documents table does not exist. Creating tables...")
                db.create_all()
                click.echo("Tables created successfully.")
                return
            
            # Check existing columns
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(kyc_documents)"))
                kyc_cols = {row[1] for row in result}
                
                if "verified_email" not in kyc_cols:
                    click.echo("Adding verified_email column to kyc_documents table...")
                    conn.execute(text("ALTER TABLE kyc_documents ADD COLUMN verified_email VARCHAR(255)"))
                    conn.commit()
                    click.echo("✓ Successfully added verified_email column!")
                else:
                    click.echo("✓ verified_email column already exists in kyc_documents table.")
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            return


@cli.command()
def update_citations():
    """Update all contribution citations based on existing purchases"""
    with app.app_context():
        try:
            click.echo("Updating citations for all contributions based on purchases...")
            
            # Ensure citations column exists
            engine = db.engine
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(contributions)"))
                contrib_cols = {row[1] for row in result}
                
                if "citations" not in contrib_cols:
                    click.echo("Adding citations column to contributions table...")
                    conn.execute(text("ALTER TABLE contributions ADD COLUMN citations INTEGER DEFAULT 0"))
                    conn.commit()
                    click.echo("✓ Added citations column")
            
            # Now use db.session for the rest
            
            # Count purchases per contribution and update citations
            # Using SQL to count purchases per contribution
            # Get purchase counts per contribution
            purchase_counts = db.session.execute(text("""
                SELECT contribution_id, COUNT(*) as purchase_count
                FROM purchases
                GROUP BY contribution_id
            """)).fetchall()
            
            click.echo(f"Found {len(purchase_counts)} contributions with purchases")
            
            updated_count = 0
            for row in purchase_counts:
                try:
                    contrib_id = row[0]
                    purchase_count = row[1]
                    
                    # Update citations for this contribution
                    db.session.execute(
                        text("UPDATE contributions SET citations = :count WHERE id = :contrib_id"),
                        {"count": purchase_count, "contrib_id": contrib_id}
                    )
                    
                    # Get contribution to find author
                    contrib = Contribution.query.get(contrib_id)
                    if contrib and contrib.author:
                        # Calculate how much the contributor should have received
                        # (100 CTRI per purchase)
                        expected_reward = purchase_count * 100.0
                        
                        # Get current balance
                        current_balance = float(contrib.author.cnri_balance) if contrib.author.cnri_balance is not None else 0.0
                        
                        # Check if contributor already received rewards
                        # We'll add the difference if they haven't received full rewards
                        # For now, we'll just log it - you may want to manually verify
                        click.echo(f"  Contribution {contrib_id} ({contrib.title[:30]}...): {purchase_count} purchases -> {purchase_count} citations")
                        click.echo(f"    Contributor {contrib.author.email} should have received {expected_reward} CTRI total")
                    
                    updated_count += 1
                except Exception as e:
                    click.echo(f"  Error updating contribution {contrib_id}: {e}", err=True)
                    db.session.rollback()
            
            # Commit all citation updates
            db.session.commit()
            
            # Also update contributions with 0 purchases to have 0 citations
            db.session.execute(text("""
                UPDATE contributions 
                SET citations = 0 
                WHERE id NOT IN (SELECT DISTINCT contribution_id FROM purchases)
                AND (citations IS NULL OR citations != 0)
            """))
            db.session.commit()
            
            click.echo(f"\n✓ Successfully updated citations for {updated_count} contributions")
            click.echo("✓ Set citations to 0 for contributions with no purchases")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            import traceback
            click.echo(traceback.format_exc(), err=True)
            return



@cli.command()
def update_contributor_rewards():
    """Update contributor balances based on existing purchases (100 CTRI per purchase)"""
    with app.app_context():
        try:
            click.echo("Updating contributor rewards based on purchases...")
            
            # Get purchase counts per contribution with author info
            purchase_data = db.session.execute(text("""
                SELECT 
                    c.id as contribution_id,
                    c.author_id,
                    COUNT(p.id) as purchase_count
                FROM contributions c
                INNER JOIN purchases p ON c.id = p.contribution_id
                GROUP BY c.id, c.author_id
            """)).fetchall()
            
            click.echo(f"Found {len(purchase_data)} contributions with purchases")
            
            updated_contributors = {}
            for row in purchase_data:
                contrib_id = row[0]
                author_id = row[1]
                purchase_count = row[2]
                
                try:
                    # Calculate reward (100 CTRI per purchase)
                    reward_amount = purchase_count * 100.0
                    
                    # Get contributor
                    contributor = User.query.get(author_id)
                    if contributor:
                        # Get current balance
                        current_balance = float(contributor.cnri_balance) if contributor.cnri_balance is not None else 0.0
                        
                        # Add reward to balance
                        new_balance = current_balance + reward_amount
                        contributor.cnri_balance = new_balance
                        db.session.add(contributor)
                        
                        if author_id not in updated_contributors:
                            updated_contributors[author_id] = {
                                'email': contributor.email,
                                'total_reward': 0.0,
                                'purchases': 0
                            }
                        
                        updated_contributors[author_id]['total_reward'] += reward_amount
                        updated_contributors[author_id]['purchases'] += purchase_count
                        
                        click.echo(f"  Contribution {contrib_id}: {purchase_count} purchases -> {reward_amount} CTRI to {contributor.email}")
                    
                except Exception as e:
                    click.echo(f"  Error updating contributor for contribution {contrib_id}: {e}", err=True)
                    db.session.rollback()
            
            # Commit all contributor balance updates
            db.session.commit()
            
            click.echo(f"\n✓ Updated rewards for {len(updated_contributors)} contributors:")
            for author_id, data in updated_contributors.items():
                click.echo(f"  {data['email']}: {data['purchases']} total purchases -> {data['total_reward']} CTRI")
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            import traceback
            click.echo(traceback.format_exc(), err=True)
            db.session.rollback()
            return


if __name__ == "__main__":
    cli()


