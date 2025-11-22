"""
Style Squad - Friend Groups for Outfit Rating
Manage squads, share outfits, vote, and chat
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

# Database file path
backend_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(backend_dir) if os.path.exists(os.path.join(os.path.dirname(backend_dir), 'fashion_arena_db.json')) else backend_dir
SQUADS_DB = os.path.join(DATA_DIR, "style_squads_db.json")

def load_squads_db() -> Dict:
    """Load squads database from JSON file"""
    if os.path.exists(SQUADS_DB):
        try:
            with open(SQUADS_DB, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"squads": []}
    return {"squads": []}

def save_squads_db(data: Dict) -> None:
    """Save squads database to JSON file"""
    with open(SQUADS_DB, 'w') as f:
        json.dump(data, f, indent=2)

def generate_invite_code() -> str:
    """Generate a unique 6-character invite code"""
    return str(uuid.uuid4())[:8].upper()

def create_squad(name: str, description: Optional[str], user_id: str, user_name: str, max_members: int = 10) -> Dict:
    """Create a new squad"""
    db = load_squads_db()

    squad = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description or "",
        "createdBy": user_id,
        "createdAt": datetime.utcnow().isoformat(),
        "members": [{
            "id": user_id,
            "name": user_name,
            "joinedAt": datetime.utcnow().isoformat()
        }],
        "outfits": [],
        "inviteCode": generate_invite_code(),
        "maxMembers": max_members
    }

    db["squads"].append(squad)
    save_squads_db(db)

    return squad

def get_squad(squad_id: str) -> Optional[Dict]:
    """Get a squad by ID"""
    db = load_squads_db()
    for squad in db["squads"]:
        if squad["id"] == squad_id:
            return squad
    return None

def get_user_squads(user_id: str) -> List[Dict]:
    """Get all squads a user is member of"""
    db = load_squads_db()
    user_squads = []

    for squad in db["squads"]:
        for member in squad["members"]:
            if member["id"] == user_id:
                user_squads.append(squad)
                break

    return user_squads

def join_squad(invite_code: str, user_id: str, user_name: str) -> Optional[Dict]:
    """Join a squad using invite code"""
    db = load_squads_db()

    for squad in db["squads"]:
        if squad.get("inviteCode") == invite_code:
            # Check if user already member
            for member in squad["members"]:
                if member["id"] == user_id:
                    return squad  # Already a member

            # Check if squad is full
            if len(squad["members"]) >= squad["maxMembers"]:
                raise ValueError("Squad is full")

            # Add member
            squad["members"].append({
                "id": user_id,
                "name": user_name,
                "joinedAt": datetime.utcnow().isoformat()
            })

            save_squads_db(db)
            return squad

    return None

def leave_squad(squad_id: str, user_id: str) -> bool:
    """Leave a squad"""
    db = load_squads_db()

    for squad in db["squads"]:
        if squad["id"] == squad_id:
            squad["members"] = [m for m in squad["members"] if m["id"] != user_id]

            # If no members left, delete squad
            if len(squad["members"]) == 0:
                db["squads"] = [s for s in db["squads"] if s["id"] != squad_id]

            save_squads_db(db)
            return True

    return False

def share_outfit(squad_id: str, user_id: str, user_name: str, photo: str, occasion: str, question: Optional[str] = None) -> Optional[Dict]:
    """Share an outfit to squad for feedback"""
    db = load_squads_db()

    for squad in db["squads"]:
        if squad["id"] == squad_id:
            outfit = {
                "id": str(uuid.uuid4()),
                "squadId": squad_id,
                "userId": user_id,
                "userName": user_name,
                "photo": photo,
                "occasion": occasion,
                "question": question,
                "createdAt": datetime.utcnow().isoformat(),
                "votes": [],
                "chatMessages": []
            }

            squad["outfits"].append(outfit)
            save_squads_db(db)
            return outfit

    return None

def vote_on_outfit(outfit_id: str, user_id: str, user_name: str, vote_type: str, comment: Optional[str] = None) -> bool:
    """Vote on a squad outfit"""
    db = load_squads_db()

    for squad in db["squads"]:
        for outfit in squad["outfits"]:
            if outfit["id"] == outfit_id:
                # Remove existing vote from this user
                outfit["votes"] = [v for v in outfit["votes"] if v["userId"] != user_id]

                # Add new vote
                outfit["votes"].append({
                    "userId": user_id,
                    "userName": user_name,
                    "voteType": vote_type,
                    "votedAt": datetime.utcnow().isoformat(),
                    "comment": comment
                })

                save_squads_db(db)
                return True

    return False

def send_message(outfit_id: str, user_id: str, user_name: str, message: str) -> bool:
    """Send a chat message on an outfit"""
    db = load_squads_db()

    for squad in db["squads"]:
        for outfit in squad["outfits"]:
            if outfit["id"] == outfit_id:
                chat_message = {
                    "id": str(uuid.uuid4()),
                    "userId": user_id,
                    "userName": user_name,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }

                outfit["chatMessages"].append(chat_message)
                save_squads_db(db)
                return True

    return False

def get_squad_outfits(squad_id: str, limit: int = 20) -> List[Dict]:
    """Get recent outfits from a squad"""
    squad = get_squad(squad_id)
    if not squad:
        return []

    # Sort by created_at descending
    outfits = sorted(squad["outfits"], key=lambda x: x["createdAt"], reverse=True)
    return outfits[:limit]

def delete_squad(squad_id: str, user_id: str) -> bool:
    """Delete a squad (only creator can delete)"""
    db = load_squads_db()

    for squad in db["squads"]:
        if squad["id"] == squad_id and squad["createdBy"] == user_id:
            db["squads"] = [s for s in db["squads"] if s["id"] != squad_id]
            save_squads_db(db)
            return True

    return False
