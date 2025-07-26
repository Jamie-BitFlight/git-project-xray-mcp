"""Query engine for XRAY-Lite symbol search."""

from typing import Dict, List, Optional
from dataclasses import dataclass

from .schema import DatabaseManager


@dataclass
class SymbolSearchResult:
    """Result of symbol search."""
    query: str
    total_matches: int
    symbols: List[Dict]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "total_matches": self.total_matches,
            "symbols": self.symbols
        }


@dataclass
class LocationQueryResult:
    """Result of location-based query."""
    file: str
    line: int
    symbol: Optional[Dict]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "symbol": self.symbol
        }


class XRayQueryEngine:
    """Query engine for fast symbol search in XRAY-Lite."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize the query engine.
        
        Args:
            repo_path: Path to the repository root
        """
        self.db = DatabaseManager(repo_path)
    
    def find_symbols(self, query: str, limit: int = 50) -> SymbolSearchResult:
        """Find symbols by name with smart ranking.
        
        Uses case-insensitive substring matching with intelligent ranking:
        - Exact matches first
        - Prefix matches second  
        - Substring matches last
        
        Args:
            query: Search query (symbol name or partial name)
            limit: Maximum number of results to return
            
        Returns:
            SymbolSearchResult with matching symbols
        """
        if not query.strip():
            return SymbolSearchResult(
                query=query,
                total_matches=0,
                symbols=[]
            )
        
        # Search for symbols using alias-based search for better accuracy
        matches = self.db.find_symbols_by_alias(query.strip(), limit)
        
        # Convert to result format with additional metadata
        symbols = []
        for match in matches:
            symbol = {
                "id": match["id"],
                "name": match["name"],
                "kind": match["kind"],
                "file": match["file"],
                "line": match["line"],
                "column": match.get("column", 0),
                "signature": match.get("signature", ""),
                "parent_id": match.get("parent_id"),
                "canonical_id": match.get("canonical_id", ""),
                "matched_alias": match.get("matched_alias", match["name"]),
                "match_type": match.get("match_type", "simple")
            }
            
            # Add context information
            if match.get("signature"):
                symbol["display_text"] = match["signature"]
            else:
                symbol["display_text"] = f"{match['kind']} {match['name']}"
            
            # Add location string
            symbol["location"] = f"{match['file']}:{match['line']}"
            
            symbols.append(symbol)
        
        return SymbolSearchResult(
            query=query,
            total_matches=len(symbols),
            symbols=symbols
        )
    
    def get_symbol_at_location(self, file: str, line: int) -> LocationQueryResult:
        """Get symbol at specific file location.
        
        Args:
            file: File path (relative to repo root)
            line: Line number (1-based)
            
        Returns:
            LocationQueryResult with symbol if found
        """
        symbol_data = self.db.find_symbol_at_location(file, line)
        
        symbol = None
        if symbol_data:
            symbol = {
                "id": symbol_data["id"],
                "name": symbol_data["name"],
                "kind": symbol_data["kind"],
                "file": symbol_data["file"],
                "line": symbol_data["line"],
                "column": symbol_data.get("column", 0),
                "end_line": symbol_data.get("end_line", 0),
                "signature": symbol_data.get("signature", ""),
                "parent_id": symbol_data.get("parent_id")
            }
            
            # Add display information
            if symbol_data.get("signature"):
                symbol["display_text"] = symbol_data["signature"]
            else:
                symbol["display_text"] = f"{symbol_data['kind']} {symbol_data['name']}"
            
            symbol["location"] = f"{symbol_data['file']}:{symbol_data['line']}"
        
        return LocationQueryResult(
            file=file,
            line=line,
            symbol=symbol
        )
    
    def search_by_kind(self, kind: str, limit: int = 50) -> List[Dict]:
        """Search symbols by their kind (function, class, method, etc.).
        
        Args:
            kind: Symbol kind to search for
            limit: Maximum number of results
            
        Returns:
            List of matching symbols
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, name, kind, file, line, column, signature, parent_id
                FROM symbols
                WHERE kind = ?
                ORDER BY file, line
                LIMIT ?
            """, (kind, limit))
            
            symbols = []
            for row in cursor.fetchall():
                symbol = dict(row)
                symbol["location"] = f"{symbol['file']}:{symbol['line']}"
                symbol["display_text"] = symbol.get("signature", f"{symbol['kind']} {symbol['name']}")
                symbols.append(symbol)
            
            return symbols
    
    def search_by_file(self, file_pattern: str, limit: int = 50) -> List[Dict]:
        """Search symbols by file path pattern.
        
        Args:
            file_pattern: File path pattern to match
            limit: Maximum number of results
            
        Returns:
            List of matching symbols
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, name, kind, file, line, column, signature, parent_id
                FROM symbols
                WHERE file LIKE ?
                ORDER BY file, line
                LIMIT ?
            """, (f"%{file_pattern}%", limit))
            
            symbols = []
            for row in cursor.fetchall():
                symbol = dict(row)
                symbol["location"] = f"{symbol['file']}:{symbol['line']}"
                symbol["display_text"] = symbol.get("signature", f"{symbol['kind']} {symbol['name']}")
                symbols.append(symbol)
            
            return symbols
    
    def get_symbol_by_id(self, symbol_id: int) -> Optional[Dict]:
        """Get symbol by its database ID.
        
        Args:
            symbol_id: Symbol ID
            
        Returns:
            Symbol dictionary if found, None otherwise
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, name, kind, file, line, column, end_line, signature, parent_id
                FROM symbols
                WHERE id = ?
            """, (symbol_id,))
            
            row = cursor.fetchone()
            if row:
                symbol = dict(row)
                symbol["location"] = f"{symbol['file']}:{symbol['line']}"
                symbol["display_text"] = symbol.get("signature", f"{symbol['kind']} {symbol['name']}")
                return symbol
            
            return None
    
    def get_file_symbols(self, file: str) -> List[Dict]:
        """Get all symbols in a specific file.
        
        Args:
            file: File path (relative to repo root)
            
        Returns:
            List of symbols in the file, ordered by line number
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, name, kind, file, line, column, end_line, signature, parent_id
                FROM symbols
                WHERE file = ?
                ORDER BY line, column
            """, (file,))
            
            symbols = []
            for row in cursor.fetchall():
                symbol = dict(row)
                symbol["location"] = f"{symbol['file']}:{symbol['line']}"
                symbol["display_text"] = symbol.get("signature", f"{symbol['kind']} {symbol['name']}")
                symbols.append(symbol)
            
            return symbols
    
    def get_statistics(self) -> Dict:
        """Get query engine and database statistics.
        
        Returns:
            Dictionary with various statistics
        """
        stats = self.db.get_database_stats()
        
        # Add symbol kind breakdown
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT kind, COUNT(*) as count
                FROM symbols
                GROUP BY kind
                ORDER BY count DESC
            """)
            
            symbol_kinds = {row['kind']: row['count'] for row in cursor.fetchall()}
        
        stats["symbol_kinds"] = symbol_kinds
        return stats