#!/usr/bin/env python3
"""Test file for Comby patterns."""

import os
import sys
from typing import List, Dict
from collections import defaultdict

class UserService:
    """Service for managing users."""
    
    def __init__(self, db):
        self.db = db
        self.cache = {}
    
    def get_user(self, user_id: int) -> Dict:
        """Get user by ID."""
        if user_id in self.cache:
            return self.cache[user_id]
        
        user = self.db.fetch_one("SELECT * FROM users WHERE id = ?", user_id)
        if user:
            self.cache[user_id] = user
        return user
    
    def create_user(self, name: str, email: str) -> int:
        """Create a new user."""
        result = self.db.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            name, email
        )
        return result.lastrowid
    
    def update_user(self, user_id: int, **kwargs):
        """Update user attributes."""
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [user_id]
        
        self.db.execute(
            f"UPDATE users SET {set_clause} WHERE id = ?",
            *values
        )
        
        # Clear cache
        if user_id in self.cache:
            del self.cache[user_id]

def process_data(data: List[Dict]) -> Dict:
    """Process a list of data items."""
    result = defaultdict(list)
    
    for item in data:
        category = item.get("category", "unknown")
        result[category].append(item)
    
    return dict(result)

# Test function calls
def main():
    service = UserService(None)
    user = service.get_user(123)
    new_id = service.create_user("Alice", "alice@example.com")
    service.update_user(new_id, name="Alice Smith")
    
    data = [
        {"id": 1, "category": "A"},
        {"id": 2, "category": "B"},
        {"id": 3, "category": "A"},
    ]
    
    processed = process_data(data)
    print(processed)

if __name__ == "__main__":
    main()