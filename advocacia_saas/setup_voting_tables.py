#!/usr/bin/env python
"""
Setup voting system tables - creates tables and adds votes_per_period column manually.
Run this when flask db upgrade fails due to migration chain issues.
"""

import os
import sys
from app import create_app, db
from app.models import BillingPlan

def setup_voting_tables():
    """Create voting tables and add votes_per_period column"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create tables by importing the models
            from app.models_roadmap_votes import RoadmapVote, RoadmapVoteQuota
            
            print("[SETUP] Setting up voting system tables...")
            
            # Create all tables
            db.create_all()
            print("[OK] Tables created successfully")
            
            # Add votes_per_period column if it doesn't exist
            try:
                db.session.execute(
                    db.text("ALTER TABLE billing_plans ADD COLUMN votes_per_period INTEGER DEFAULT 0")
                )
                db.session.commit()
                print("[OK] Added votes_per_period column to billing_plans")
            except Exception as e:
                if "already exists" in str(e):
                    print("[INFO] votes_per_period column already exists")
                else:
                    print("[WARN] Could not add votes_per_period: " + str(e))
                db.session.rollback()
            
            # Configure default votes per plan
            plans_config = {
                'Essencial': 2,
                'Profissional': 5,
                'Empresarial': 10
            }
            
            for plan_name, votes in plans_config.items():
                plan = BillingPlan.query.filter_by(name=plan_name).first()
                if plan:
                    plan.votes_per_period = votes
                    db.session.add(plan)
                    print("[OK] Updated " + plan_name + " plan: " + str(votes) + " votes/period")
                else:
                    print("[WARN] Plan '" + plan_name + "' not found")
            
            try:
                db.session.commit()
            except Exception as e:
                print("[WARN] Could not update plans: " + str(e))
                db.session.rollback()
            
            print("\n[OK] Voting system setup complete!")
            print("\nNext steps:")
            print("1. Test API: POST /api/roadmap-votes/vote")
            print("2. Check leaderboard: GET /api/roadmap-votes/leaderboard")
            print("3. Schedule newsletter: Monday 8am")
            
        except Exception as e:
            print("[ERR] Error setting up voting tables: " + str(e))
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False
    
    return True

if __name__ == '__main__':
    success = setup_voting_tables()
    sys.exit(0 if success else 1)
