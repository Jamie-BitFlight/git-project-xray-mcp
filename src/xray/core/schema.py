"""SQLite database schema and initialization for XRAY."""

import sqlite3
import os
from pathlib import Path
from typing import Optional


class DatabaseManager:
    """Manages the SQLite database for XRAY code intelligence."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize database manager.
        
        Args:
            repo_path: Path to the repository root (where .xray/ will be created)
        """
        self.repo_path = Path(repo_path).resolve()
        self.xray_dir = self.repo_path / ".xray"
        self.db_path = self.xray_dir / "xray.db"
        
    def ensure_xray_directory(self) -> None:
        """Ensure .xray directory exists and is properly configured."""
        self.xray_dir.mkdir(exist_ok=True)
        
        # Add .xray to .gitignore if it exists
        gitignore_path = self.repo_path / ".gitignore"
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
            if ".xray/" not in gitignore_content:
                with gitignore_path.open("a") as f:
                    f.write("\n# XRAY code intelligence database\n.xray/\n")
        else:
            gitignore_path.write_text("# XRAY code intelligence database\n.xray/\n")
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration."""
        self.ensure_xray_directory()
        
        conn = sqlite3.Connection(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        conn.execute("PRAGMA journal_mode = WAL")  # Use WAL mode for better performance
        
        return conn
    
    def initialize_database_if_needed(self) -> None:
        """Initialize database only if it doesn't exist or is empty."""
        self.ensure_xray_directory()
        
        # Check if the database file exists and has the symbols table
        if self.db_path.exists():
            try:
                with self.get_connection() as conn:
                    # If this query succeeds, the table exists.
                    conn.execute("SELECT 1 FROM symbols LIMIT 1")
                return  # Database already initialized
            except sqlite3.OperationalError:
                # Table doesn't exist, so we proceed with initialization
                pass

        self.initialize_database()

    def initialize_database(self) -> None:
        """Initialize database with schema and indexes."""
        with self.get_connection() as conn:
            # Create symbols table with canonical ID support
            conn.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_id TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    file TEXT NOT NULL,
                    line INTEGER NOT NULL,
                    column INTEGER DEFAULT 0,
                    end_line INTEGER DEFAULT 0,
                    signature TEXT,
                    parent_id INTEGER,
                    FOREIGN KEY(parent_id) REFERENCES symbols(id)
                )
            """)
            
            # Create symbol aliases table for multi-name resolution
            conn.execute("""
                CREATE TABLE IF NOT EXISTS symbol_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol_id INTEGER NOT NULL,
                    alias_type TEXT NOT NULL,
                    alias_name TEXT NOT NULL,
                    context_file TEXT,
                    FOREIGN KEY(symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
                )
            """)
            
            # Create edges table for dependency graph with provenance
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    from_id INTEGER NOT NULL,
                    to_id INTEGER NOT NULL,
                    edge_type TEXT NOT NULL,
                    provenance TEXT,
                    PRIMARY KEY (from_id, to_id, edge_type),
                    FOREIGN KEY(from_id) REFERENCES symbols(id) ON DELETE CASCADE,
                    FOREIGN KEY(to_id) REFERENCES symbols(id) ON DELETE CASCADE
                )
            """)
            
            # Commit table creation before creating indexes
            conn.commit()
            
            # Create essential indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_canonical_id ON symbols(canonical_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_location ON symbols(file, line)")
            
            # Indexes for symbol aliases
            conn.execute("CREATE INDEX IF NOT EXISTS idx_aliases_symbol_id ON symbol_aliases(symbol_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_aliases_name ON symbol_aliases(alias_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_aliases_type ON symbol_aliases(alias_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_aliases_context ON symbol_aliases(context_file)")
            
            # Indexes for edges with new schema
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type)")
            
            conn.commit()
    
    def clear_database(self) -> None:
        """Clear all data from the database (full rebuild)."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM edges")
            conn.execute("DELETE FROM symbol_aliases")
            conn.execute("DELETE FROM symbols")
            conn.commit()
    
    def get_database_stats(self) -> dict:
        """Get database statistics."""
        with self.get_connection() as conn:
            symbols_count = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
            edges_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            aliases_count = conn.execute("SELECT COUNT(*) FROM symbol_aliases").fetchone()[0]
            
            # Get database file size
            db_size_bytes = 0
            if self.db_path.exists():
                db_size_bytes = self.db_path.stat().st_size
            
            return {
                "symbols_count": symbols_count,
                "edges_count": edges_count,
                "aliases_count": aliases_count,
                "database_size_kb": round(db_size_bytes / 1024, 2),
                "database_path": str(self.db_path)
            }
    
    def insert_symbols_bulk(self, symbols: list[dict]) -> list[int]:
        """Insert multiple symbols in a single transaction.
        
        Args:
            symbols: List of symbol dictionaries with keys:
                - canonical_id, name, kind, file, line, column, end_line, signature, parent_id
        
        Returns:
            List of inserted symbol IDs
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            inserted_ids = []
            for symbol in symbols:
                cursor.execute("""
                    INSERT INTO symbols (canonical_id, name, kind, file, line, column, end_line, signature, parent_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol["canonical_id"],
                    symbol["name"],
                    symbol["kind"],
                    symbol["file"],
                    symbol["line"],
                    symbol.get("column", 0),
                    symbol.get("end_line", 0),
                    symbol.get("signature"),
                    symbol.get("parent_id")
                ))
                inserted_ids.append(cursor.lastrowid)
            
            conn.commit()
            return inserted_ids
    
    def insert_edges_bulk(self, edges: list[tuple]) -> None:
        """Insert multiple edges in a single transaction.
        
        Args:
            edges: List of (from_id, to_id, edge_type, provenance) tuples
        """
        with self.get_connection() as conn:
            conn.executemany("INSERT OR IGNORE INTO edges (from_id, to_id, edge_type, provenance) VALUES (?, ?, ?, ?)", edges)
            conn.commit()
    
    def insert_aliases_bulk(self, aliases: list[dict]) -> None:
        """Insert multiple symbol aliases in a single transaction.
        
        Args:
            aliases: List of alias dictionaries with keys:
                - symbol_id, alias_type, alias_name, context_file
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for alias in aliases:
                cursor.execute("""
                    INSERT OR IGNORE INTO symbol_aliases (symbol_id, alias_type, alias_name, context_file)
                    VALUES (?, ?, ?, ?)
                """, (
                    alias["symbol_id"],
                    alias["alias_type"],
                    alias["alias_name"],
                    alias.get("context_file")
                ))
            
            conn.commit()
    
    def find_symbols_by_alias(self, query: str, limit: int = 50, context_file: str = None) -> list[dict]:
        """Find symbols by searching through all aliases.
        
        Args:
            query: Search query (case-insensitive substring)
            limit: Maximum number of results
            context_file: Optional file context for import resolution
            
        Returns:
            List of symbol dictionaries with match information
        """
        with self.get_connection() as conn:
            # Build query conditions
            conditions = ["a.alias_name LIKE ? COLLATE NOCASE"]
            params = [f"%{query}%"]
            
            if context_file:
                conditions.append("(a.context_file IS NULL OR a.context_file = ?)")
                params.append(context_file)
            
            cursor = conn.execute(f"""
                SELECT DISTINCT s.id, s.canonical_id, s.name, s.kind, s.file, s.line, s.column, 
                       s.end_line, s.signature, s.parent_id,
                       a.alias_name as matched_alias, a.alias_type as match_type
                FROM symbols s
                JOIN symbol_aliases a ON s.id = a.symbol_id
                WHERE {' AND '.join(conditions)}
                ORDER BY 
                    CASE 
                        WHEN a.alias_name = ? THEN 0          -- Exact match
                        WHEN a.alias_name LIKE ? THEN 1       -- Prefix match  
                        ELSE 2                                -- Substring match
                    END, 
                    a.alias_type,  -- Prioritize canonical, then qualified, then simple
                    s.name
                LIMIT ?
            """, params + [query, f"{query}%", limit])
            
            return [dict(row) for row in cursor.fetchall()]
    
    def find_symbol_by_canonical_id(self, canonical_id: str) -> Optional[dict]:
        """Find symbol by exact canonical ID match.
        
        Args:
            canonical_id: Exact canonical ID
            
        Returns:
            Symbol dictionary if found, None otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, canonical_id, name, kind, file, line, column, end_line, signature, parent_id
                FROM symbols
                WHERE canonical_id = ?
                LIMIT 1
            """, (canonical_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def find_symbols_by_name(self, query: str, limit: int = 50) -> list[dict]:
        """Find symbols by name with smart ranking.
        
        Args:
            query: Search query (case-insensitive substring)
            limit: Maximum number of results
            
        Returns:
            List of symbol dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, canonical_id, name, kind, file, line, column, end_line, signature, parent_id
                FROM symbols
                WHERE name LIKE ? COLLATE NOCASE
                ORDER BY 
                    CASE 
                        WHEN name = ? THEN 0          -- Exact match
                        WHEN name LIKE ? THEN 1       -- Prefix match  
                        ELSE 2                        -- Substring match
                    END, name
                LIMIT ?
            """, (f"%{query}%", query, f"{query}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def find_symbol_at_location(self, file: str, line: int) -> Optional[dict]:
        """Find symbol at specific file location.
        
        Args:
            file: File path
            line: Line number
            
        Returns:
            Symbol dictionary if found, None otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, canonical_id, name, kind, file, line, column, end_line, signature, parent_id
                FROM symbols
                WHERE file = ? AND line <= ? AND (end_line = 0 OR end_line >= ?)
                ORDER BY line DESC, column DESC
                LIMIT 1
            """, (file, line, line))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_symbol_dependencies(self, symbol_id: int) -> list[dict]:
        """Get direct dependencies of a symbol.
        
        Args:
            symbol_id: Symbol ID
            
        Returns:
            List of symbol dictionaries this symbol depends on
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT s.id, s.canonical_id, s.name, s.kind, s.file, s.line, s.column, s.signature,
                       e.edge_type, e.provenance
                FROM edges e
                JOIN symbols s ON s.id = e.to_id
                WHERE e.from_id = ?
                ORDER BY s.file, s.line
            """, (symbol_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_symbol_dependents(self, symbol_id: int) -> list[dict]:
        """Get direct dependents of a symbol.
        
        Args:
            symbol_id: Symbol ID
            
        Returns:
            List of symbol dictionaries that depend on this symbol
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT s.id, s.canonical_id, s.name, s.kind, s.file, s.line, s.column, s.signature,
                       e.edge_type, e.provenance
                FROM edges e
                JOIN symbols s ON s.id = e.from_id
                WHERE e.to_id = ?
                ORDER BY s.file, s.line
            """, (symbol_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def find_symbol_by_name_exact(self, name: str) -> Optional[dict]:
        """Find symbol by exact name match.
        
        Args:
            name: Exact symbol name
            
        Returns:
            First matching symbol dictionary if found, None otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, canonical_id, name, kind, file, line, column, end_line, signature, parent_id
                FROM symbols
                WHERE name = ?
                LIMIT 1
            """, (name,))
            
            row = cursor.fetchone()
            return dict(row) if row else None