"""Core indexing engine for XRAY."""

import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from .schema import DatabaseManager
from ..parsers.base import (
    LanguageRegistry, LanguageDetector, load_tree_sitter_languages,
    Symbol, Edge, CanonicalIdGenerator
)
from ..parsers.python import PythonParser


@dataclass
class IndexingResult:
    """Result of indexing operation."""
    success: bool
    files_indexed: int
    symbols_found: int
    edges_created: int
    duration_seconds: float
    database_size_kb: float
    errors: List[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "files_indexed": self.files_indexed,
            "symbols_found": self.symbols_found,
            "edges_created": self.edges_created,
            "duration_seconds": round(self.duration_seconds, 3),
            "database_size_kb": self.database_size_kb,
            "errors": self.errors
        }


class XRayIndexer:
    """Core indexing engine for XRAY."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize the indexer.
        
        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path).resolve()
        self.db = DatabaseManager(str(self.repo_path))
        self.registry = LanguageRegistry()
        self.errors: List[str] = []
        
        # Initialize database (safe to call multiple times)
        self.db.initialize_database_if_needed()
        
        # Load and register languages
        self._setup_languages()
    
    def _setup_languages(self) -> None:
        """Set up language parsers."""
        languages = load_tree_sitter_languages()
        
        # Register Python parser
        if 'python' in languages:
            self.registry.register_language('python', languages['python'], PythonParser)
        
        # TODO: Add JavaScript/TypeScript and Go parsers when implemented
        # if 'javascript' in languages:
        #     self.registry.register_language('javascript', languages['javascript'], JavaScriptParser)
        # if 'typescript' in languages:
        #     self.registry.register_language('typescript', languages['typescript'], TypeScriptParser)
        # if 'go' in languages:
        #     self.registry.register_language('go', languages['go'], GoParser)
    
    def build_index(self, path: Optional[str] = None, force_rebuild: bool = True) -> IndexingResult:
        """Build the code intelligence index.
        
        Args:
            path: Path to index (defaults to repo root)
            force_rebuild: Whether to clear existing database
            
        Returns:
            IndexingResult with statistics and status
        """
        start_time = time.time()
        self.errors = []
        
        if path is None:
            path = str(self.repo_path)
        
        try:
            # Clear database if force rebuild
            if force_rebuild:
                self.db.clear_database()
            
            # Find all source files
            source_files = LanguageDetector.find_source_files(path)
            
            if not source_files:
                return IndexingResult(
                    success=True,
                    files_indexed=0,
                    symbols_found=0,
                    edges_created=0,
                    duration_seconds=time.time() - start_time,
                    database_size_kb=self.db.get_database_stats()["database_size_kb"],
                    errors=["No supported source files found"]
                )
            
            # Parse files and extract symbols
            all_symbols = []
            all_edges = []
            files_processed = 0
            
            for file_path in source_files:
                try:
                    symbols, edges = self.registry.parse_file(file_path)
                    
                    if symbols:  # Only count files that had symbols
                        all_symbols.extend(symbols)
                        all_edges.extend(edges)
                        files_processed += 1
                
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {str(e)}"
                    self.errors.append(error_msg)
                    continue
            
            # Convert symbols to database format with canonical IDs
            # First pass: insert symbols without parent_id to avoid foreign key issues
            symbol_records = []
            symbol_list_to_db_id = {}  # Map list index to database ID
            all_aliases = []  # Store all aliases to insert later
            
            for i, symbol in enumerate(all_symbols):
                # Find parent symbol for canonical ID generation
                parent_symbol = None
                if symbol.parent_id is not None and symbol.parent_id < len(all_symbols):
                    parent_symbol = all_symbols[symbol.parent_id]
                
                # Generate canonical ID
                canonical_id = CanonicalIdGenerator.generate_canonical_id(
                    symbol, parent_symbol, self.repo_path
                )
                
                record = {
                    "canonical_id": canonical_id,
                    "name": symbol.name,
                    "kind": symbol.kind,
                    "file": str(Path(symbol.file).relative_to(self.repo_path)),
                    "line": symbol.line,
                    "column": symbol.column,
                    "end_line": symbol.end_line,
                    "signature": symbol.signature,
                    "parent_id": None  # Will be updated in second pass
                }
                symbol_records.append(record)
            
            # Insert symbols in bulk
            inserted_ids = self.db.insert_symbols_bulk(symbol_records)
            
            # Create mapping from list index to database ID
            for i, db_id in enumerate(inserted_ids):
                symbol_list_to_db_id[i] = db_id
            
            # Generate aliases for all symbols
            for i, symbol in enumerate(all_symbols):
                parent_symbol = None
                if symbol.parent_id is not None and symbol.parent_id < len(all_symbols):
                    parent_symbol = all_symbols[symbol.parent_id]
                
                # Generate aliases for this symbol
                symbol_aliases = CanonicalIdGenerator.generate_all_aliases(
                    symbol, parent_symbol, self.repo_path, symbol.file
                )
                
                # Add symbol_id to each alias
                for alias in symbol_aliases:
                    alias["symbol_id"] = inserted_ids[i]
                    all_aliases.append(alias)
            
            # Insert all aliases
            if all_aliases:
                self.db.insert_aliases_bulk(all_aliases)
            
            # Second pass: update parent_id relationships
            symbols_to_update = []
            for i, symbol in enumerate(all_symbols):
                if symbol.parent_id is not None and symbol.parent_id in symbol_list_to_db_id:
                    symbols_to_update.append((symbol_list_to_db_id[symbol.parent_id], inserted_ids[i]))
            
            # Update parent_id relationships
            if symbols_to_update:
                with self.db.get_connection() as conn:
                    conn.executemany("UPDATE symbols SET parent_id = ? WHERE id = ?", symbols_to_update)
                    conn.commit()
            
            # Create comprehensive symbol mapping for edge resolution
            symbol_mappings = self._create_symbol_mappings(all_symbols, inserted_ids)
            
            # Resolve and insert edges with improved cross-file resolution
            edge_tuples = []
            for edge in all_edges:
                from_id = self._resolve_symbol_id_by_alias(edge.from_symbol, edge.from_file)
                to_id = self._resolve_symbol_id_by_alias(edge.to_symbol, edge.to_file)
                
                if from_id and to_id and from_id != to_id:
                    # Determine edge type based on edge characteristics
                    edge_type = self._determine_edge_type(edge)
                    provenance = f"{edge.from_symbol} -> {edge.to_symbol}"
                    edge_tuples.append((from_id, to_id, edge_type, provenance))
            
            # Add cross-file import-to-usage edges
            cross_file_edges = self._create_cross_file_edges_new(all_symbols, inserted_ids)
            edge_tuples.extend(cross_file_edges)
            
            # Remove duplicates (based on from_id, to_id, edge_type)
            edge_tuples = list(set(edge_tuples))
            
            # Insert edges in bulk
            if edge_tuples:
                self.db.insert_edges_bulk(edge_tuples)
            
            # Get final statistics
            duration = time.time() - start_time
            db_stats = self.db.get_database_stats()
            
            # Save index timestamp
            self.db.set_metadata("index_timestamp", str(time.time()))
            self.db.set_metadata("indexed_files", str(files_processed))
            self.db.set_metadata("indexed_symbols", str(len(all_symbols)))
            
            return IndexingResult(
                success=True,
                files_indexed=files_processed,
                symbols_found=len(all_symbols),
                edges_created=len(edge_tuples),
                duration_seconds=duration,
                database_size_kb=db_stats["database_size_kb"],
                errors=self.errors.copy()
            )
        
        except Exception as e:
            return IndexingResult(
                success=False,
                files_indexed=0,
                symbols_found=0,
                edges_created=0,
                duration_seconds=time.time() - start_time,
                database_size_kb=0,
                errors=[f"Indexing failed: {str(e)}"]
            )
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported programming languages.
        
        Returns:
            List of supported language names
        """
        return self.registry.get_supported_languages()
    
    def get_database_stats(self) -> dict:
        """Get current database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        return self.db.get_database_stats()
    
    def is_index_available(self) -> bool:
        """Check if index is available and has data.
        
        Returns:
            True if index exists and has symbols, False otherwise
        """
        try:
            stats = self.db.get_database_stats()
            return stats["symbols_count"] > 0
        except:
            return False
    
    def _create_symbol_mappings(self, all_symbols: List[Symbol], inserted_ids: List[int]) -> Dict[str, int]:
        """Create comprehensive symbol mappings for edge resolution.
        
        Args:
            all_symbols: List of all extracted symbols
            inserted_ids: List of database IDs for symbols
            
        Returns:
            Dictionary mapping various symbol keys to database IDs
        """
        mappings = {}
        
        for i, symbol in enumerate(all_symbols):
            db_id = inserted_ids[i]
            rel_file = str(Path(symbol.file).relative_to(self.repo_path))
            
            # File-scoped mapping (highest priority)
            file_key = f"{rel_file}:{symbol.name}"
            mappings[file_key] = db_id
            
            # Global mapping for simple names (lower priority)
            if symbol.name not in mappings:
                mappings[symbol.name] = db_id
            
            # Class-qualified mapping for methods
            if symbol.kind == 'method' and hasattr(symbol, 'parent_id') and symbol.parent_id is not None:
                parent_symbol = all_symbols[symbol.parent_id]
                qualified_name = f"{parent_symbol.name}.{symbol.name}"
                mappings[qualified_name] = db_id
                
                # File-scoped qualified mapping
                file_qualified_key = f"{rel_file}:{qualified_name}"
                mappings[file_qualified_key] = db_id
                
                # Also map by the qualified name that _find_enclosing_function returns
                # (which includes both class and method)
                caller_qualified = f"{parent_symbol.name}.{symbol.name}"
                mappings[caller_qualified] = db_id
        
        return mappings
    
    def _resolve_symbol_id(self, symbol_name: str, context_file: Optional[str], mappings: Dict[str, int]) -> Optional[int]:
        """Resolve a symbol name to its database ID with context-aware lookup.
        
        Args:
            symbol_name: Name of the symbol to resolve
            context_file: File context for resolution (if available)
            mappings: Symbol mappings dictionary
            
        Returns:
            Database ID if found, None otherwise
        """
        if not symbol_name:
            return None
            
        # If we have context file, try file-scoped lookup first
        if context_file:
            rel_file = str(Path(context_file).relative_to(self.repo_path))
            file_key = f"{rel_file}:{symbol_name}"
            if file_key in mappings:
                return mappings[file_key]
        
        # Try global lookup
        if symbol_name in mappings:
            return mappings[symbol_name]
            
        # Handle special cases like <module> level calls
        if symbol_name == "<module>":
            return None
            
        return None
    
    def _create_cross_file_edges(self, all_symbols: List[Symbol], inserted_ids: List[int], mappings: Dict[str, int]) -> List[tuple]:
        """Create cross-file dependency edges based on imports and usage.
        
        Args:
            all_symbols: List of all extracted symbols
            inserted_ids: List of database IDs for symbols
            mappings: Symbol mappings dictionary
            
        Returns:
            List of edge tuples (from_id, to_id) for cross-file dependencies
        """
        cross_file_edges = []
        
        # Group symbols by file
        symbols_by_file = {}
        for i, symbol in enumerate(all_symbols):
            rel_file = str(Path(symbol.file).relative_to(self.repo_path))
            if rel_file not in symbols_by_file:
                symbols_by_file[rel_file] = []
            symbols_by_file[rel_file].append((symbol, inserted_ids[i]))
        
        # For each file, find imports and create edges to their definitions
        for file_path, file_symbols in symbols_by_file.items():
            imports = [(symbol, db_id) for symbol, db_id in file_symbols if symbol.kind == 'import']
            non_imports = [(symbol, db_id) for symbol, db_id in file_symbols if symbol.kind != 'import']
            
            # For each import in this file
            for import_symbol, import_db_id in imports:
                import_name = import_symbol.name
                
                # Find definition of this imported symbol in other files
                for other_file, other_symbols in symbols_by_file.items():
                    if other_file == file_path:
                        continue
                        
                    # Look for class or function definitions with matching name
                    for other_symbol, other_db_id in other_symbols:
                        if (other_symbol.kind in ['class', 'function'] and 
                            other_symbol.name == import_name):
                            # Create edge from import to definition
                            cross_file_edges.append((import_db_id, other_db_id))
                            
                            # Also create edges from any usage of this imported name
                            # to the original definition
                            for user_symbol, user_db_id in non_imports:
                                if (user_symbol.kind in ['function', 'method'] and
                                    import_name in (user_symbol.signature or "")):
                                    cross_file_edges.append((user_db_id, other_db_id))
        
        return cross_file_edges
    
    def _resolve_symbol_id_by_alias(self, symbol_name: str, context_file: Optional[str]) -> Optional[int]:
        """Resolve symbol name to database ID using the alias system.
        
        Args:
            symbol_name: Symbol name to resolve
            context_file: File context for resolution
            
        Returns:
            Database ID if found, None otherwise
        """
        if not symbol_name or symbol_name == "<module>":
            return None
            
        # Use the new alias-aware search
        matches = self.db.find_symbols_by_alias(symbol_name, limit=1, context_file=context_file)
        if matches:
            return matches[0]['id']
            
        return None
    
    def _determine_edge_type(self, edge: Edge) -> str:
        """Determine the type of dependency edge.
        
        Args:
            edge: The edge to classify
            
        Returns:
            Edge type string
        """
        # Basic classification based on common patterns
        if '(' in edge.to_symbol:  # Function call
            return 'call'
        elif 'import' in edge.from_symbol.lower():  # Import relationship
            return 'import'
        elif edge.to_symbol[0].isupper():  # Class reference (capitalized)
            return 'instantiate'
        else:
            return 'access'
    
    def _create_cross_file_edges_new(self, all_symbols: List[Symbol], inserted_ids: List[int]) -> List[tuple]:
        """Create cross-file dependency edges using the new alias system.
        
        Args:
            all_symbols: List of all extracted symbols
            inserted_ids: List of database IDs for symbols
            
        Returns:
            List of edge tuples (from_id, to_id, edge_type, provenance)
        """
        cross_file_edges = []
        
        # Group symbols by file
        symbols_by_file = {}
        for i, symbol in enumerate(all_symbols):
            rel_file = str(Path(symbol.file).relative_to(self.repo_path))
            if rel_file not in symbols_by_file:
                symbols_by_file[rel_file] = []
            symbols_by_file[rel_file].append((symbol, inserted_ids[i]))
        
        # For each file, find imports and create edges to their definitions
        for file_path, file_symbols in symbols_by_file.items():
            imports = [(symbol, db_id) for symbol, db_id in file_symbols if symbol.kind == 'import']
            
            # For each import in this file
            for import_symbol, import_db_id in imports:
                import_name = import_symbol.name
                
                # Find definition of this imported symbol in other files  
                definition_matches = self.db.find_symbols_by_alias(import_name, limit=10)
                for match in definition_matches:
                    if match['kind'] in ['class', 'function'] and match['file'] != file_path:
                        # Create edge from import to definition
                        provenance = f"import {import_name} from {match['file']}"
                        cross_file_edges.append((import_db_id, match['id'], 'import', provenance))
                        break  # Only link to first definition found
        
        return cross_file_edges