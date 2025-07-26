"""Impact analysis engine for XRAY - THE KILLER FEATURE."""

from collections import deque
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from .schema import DatabaseManager


@dataclass
class ImpactNode:
    """Represents a node in the impact analysis graph."""
    id: int
    name: str
    kind: str
    file: str
    line: int
    depth: int
    signature: Optional[str] = None


@dataclass
class ImpactAnalysisResult:
    """Result of impact analysis."""
    symbol_name: str
    total_impacts: int
    max_depth: int
    impacts_by_depth: Dict[int, List[ImpactNode]]
    impacts_by_file: Dict[str, List[ImpactNode]]
    reasoning: List[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol_name": self.symbol_name,
            "total_impacts": self.total_impacts,
            "max_depth": self.max_depth,
            "impacts_by_depth": {
                str(depth): [
                    {
                        "name": node.name,
                        "kind": node.kind,
                        "file": node.file,
                        "line": node.line,
                        "signature": node.signature
                    }
                    for node in nodes
                ]
                for depth, nodes in self.impacts_by_depth.items()
            },
            "impacts_by_file": {
                file: [
                    {
                        "name": node.name,
                        "kind": node.kind,
                        "line": node.line,
                        "depth": node.depth,
                        "signature": node.signature
                    }
                    for node in nodes
                ]
                for file, nodes in self.impacts_by_file.items()
            },
            "reasoning": self.reasoning
        }


@dataclass
class DependencyAnalysisResult:
    """Result of dependency analysis."""
    symbol_name: str
    direct_dependencies: List[Dict]
    dependency_files: Set[str]
    reasoning: List[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol_name": self.symbol_name,
            "total_dependencies": len(self.direct_dependencies),
            "dependencies": self.direct_dependencies,
            "dependency_files": sorted(list(self.dependency_files)),
            "reasoning": self.reasoning
        }


class XRayImpactAnalyzer:
    """Core impact analysis engine for XRAY."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize the impact analyzer.
        
        Args:
            repo_path: Path to the repository root
        """
        self.db = DatabaseManager(repo_path)
    
    def analyze_impact(self, symbol_name: str, max_depth: int = 5) -> ImpactAnalysisResult:
        """Analyze what breaks if this symbol changes (THE KILLER FEATURE).
        
        This performs a breadth-first search to find all symbols that transitively
        depend on the given symbol, which answers the critical question:
        "What breaks if I change this function/class/method?"
        
        Args:
            symbol_name: Name of the symbol to analyze
            max_depth: Maximum depth for transitive analysis
            
        Returns:
            ImpactAnalysisResult with complete impact analysis
        """
        # Find the symbol using alias-based search for better accuracy
        matches = self.db.find_symbols_by_alias(symbol_name, limit=10)
        if not matches:
            return ImpactAnalysisResult(
                symbol_name=symbol_name,
                total_impacts=0,
                max_depth=0,
                impacts_by_depth={},
                impacts_by_file={},
                reasoning=[f"Symbol '{symbol_name}' not found in codebase"]
            )
        
        # If multiple matches, prioritize by match type (canonical > qualified > simple)
        symbol = matches[0]  # Already sorted by relevance in the database query
        
        if len(matches) > 1:
            # Log that we found multiple matches and are using the first one
            pass
        
        symbol_id = symbol['id']
        
        # BFS traversal to find all dependent symbols
        visited: Set[int] = set()
        queue = deque([(symbol_id, 0)])  # (symbol_id, depth)
        impacts: List[ImpactNode] = []
        reasoning: List[str] = []
        
        while queue:
            current_id, depth = queue.popleft()
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            
            # Find all symbols that depend on this one
            dependents = self.db.get_symbol_dependents(current_id)
            
            for dependent in dependents:
                if dependent['id'] not in visited:
                    impact_node = ImpactNode(
                        id=dependent['id'],
                        name=dependent['name'],
                        kind=dependent['kind'],
                        file=dependent['file'],
                        line=dependent['line'],
                        depth=depth + 1,
                        signature=dependent.get('signature')
                    )
                    impacts.append(impact_node)
                    
                    # Add to queue for further traversal
                    if depth + 1 <= max_depth:
                        queue.append((dependent['id'], depth + 1))
        
        # Organize results
        impacts_by_depth: Dict[int, List[ImpactNode]] = {}
        impacts_by_file: Dict[str, List[ImpactNode]] = {}
        
        for impact in impacts:
            # Group by depth
            if impact.depth not in impacts_by_depth:
                impacts_by_depth[impact.depth] = []
            impacts_by_depth[impact.depth].append(impact)
            
            # Group by file
            if impact.file not in impacts_by_file:
                impacts_by_file[impact.file] = []
            impacts_by_file[impact.file].append(impact)
        
        # Generate reasoning
        reasoning = self._generate_impact_reasoning(symbol_name, impacts, impacts_by_file)
        
        return ImpactAnalysisResult(
            symbol_name=symbol_name,
            total_impacts=len(impacts),
            max_depth=max(impacts_by_depth.keys()) if impacts_by_depth else 0,
            impacts_by_depth=impacts_by_depth,
            impacts_by_file=impacts_by_file,
            reasoning=reasoning
        )
    
    def analyze_dependencies(self, symbol_name: str) -> DependencyAnalysisResult:
        """Analyze what this symbol depends on.
        
        Args:
            symbol_name: Name of the symbol to analyze
            
        Returns:
            DependencyAnalysisResult with dependency information
        """
        # Find the symbol using alias-based search
        matches = self.db.find_symbols_by_alias(symbol_name, limit=10)
        if not matches:
            return DependencyAnalysisResult(
                symbol_name=symbol_name,
                direct_dependencies=[],
                dependency_files=set(),
                reasoning=[f"Symbol '{symbol_name}' not found in codebase"]
            )
        
        # Use the first match (most relevant)
        symbol = matches[0]
        
        # Get direct dependencies
        dependencies = self.db.get_symbol_dependencies(symbol['id'])
        
        # Convert to result format
        dependency_records = []
        dependency_files = set()
        
        for dep in dependencies:
            record = {
                "name": dep['name'],
                "kind": dep['kind'],
                "file": dep['file'],
                "line": dep['line'],
                "signature": dep.get('signature')
            }
            dependency_records.append(record)
            dependency_files.add(dep['file'])
        
        # Generate reasoning
        reasoning = self._generate_dependency_reasoning(symbol_name, dependency_records, dependency_files)
        
        return DependencyAnalysisResult(
            symbol_name=symbol_name,
            direct_dependencies=dependency_records,
            dependency_files=dependency_files,
            reasoning=reasoning
        )
    
    def _generate_impact_reasoning(self, symbol_name: str, impacts: List[ImpactNode], 
                                 impacts_by_file: Dict[str, List[ImpactNode]]) -> List[str]:
        """Generate human-readable reasoning for impact analysis."""
        reasoning = []
        
        if not impacts:
            reasoning.append(f"Safe to modify - no other symbols depend on '{symbol_name}'")
            reasoning.append("This symbol appears to be unused or only used internally")
            return reasoning
        
        total_impacts = len(impacts)
        total_files = len(impacts_by_file)
        
        # Risk assessment
        if total_impacts == 1:
            reasoning.append(f"Low risk - only 1 symbol depends on '{symbol_name}'")
        elif total_impacts <= 5:
            reasoning.append(f"Medium risk - {total_impacts} symbols depend on '{symbol_name}'")
        elif total_impacts <= 20:
            reasoning.append(f"High risk - {total_impacts} symbols depend on '{symbol_name}'")
        else:
            reasoning.append(f"Very high risk - {total_impacts} symbols depend on '{symbol_name}'")
        
        # File distribution
        if total_files == 1:
            reasoning.append(f"Impact contained to 1 file: {list(impacts_by_file.keys())[0]}")
        else:
            reasoning.append(f"Impact spans {total_files} files - changes may have wide effects")
        
        # Depth analysis
        max_depth = max(impact.depth for impact in impacts)
        if max_depth == 1:
            reasoning.append("All impacts are direct dependencies (depth 1)")
        else:
            reasoning.append(f"Has transitive dependencies up to depth {max_depth}")
        
        # Kind analysis
        kinds = {}
        for impact in impacts:
            kinds[impact.kind] = kinds.get(impact.kind, 0) + 1
        
        kind_summary = ", ".join([f"{count} {kind}{'s' if count > 1 else ''}" 
                                 for kind, count in kinds.items()])
        reasoning.append(f"Affects: {kind_summary}")
        
        return reasoning
    
    def _generate_dependency_reasoning(self, symbol_name: str, dependencies: List[Dict],
                                     dependency_files: Set[str]) -> List[str]:
        """Generate human-readable reasoning for dependency analysis."""
        reasoning = []
        
        if not dependencies:
            reasoning.append(f"'{symbol_name}' has no dependencies - it's self-contained")
            return reasoning
        
        total_deps = len(dependencies)
        total_files = len(dependency_files)
        
        reasoning.append(f"'{symbol_name}' depends on {total_deps} symbol{'s' if total_deps > 1 else ''}")
        
        if total_files == 1:
            reasoning.append(f"All dependencies are in 1 file: {list(dependency_files)[0]}")
        else:
            reasoning.append(f"Dependencies span {total_files} files")
        
        # Kind analysis
        kinds = {}
        for dep in dependencies:
            kinds[dep['kind']] = kinds.get(dep['kind'], 0) + 1
        
        kind_summary = ", ".join([f"{count} {kind}{'s' if count > 1 else ''}" 
                                 for kind, count in kinds.items()])
        reasoning.append(f"Depends on: {kind_summary}")
        
        return reasoning
    
    def analyze_multiple_impacts(self, symbol_names: List[str], max_depth: int = 5) -> Dict[str, ImpactAnalysisResult]:
        """Analyze impact for multiple symbols in batch (LLM-optimized).
        
        Args:
            symbol_names: List of symbol names to analyze
            max_depth: Maximum depth for transitive analysis
            
        Returns:
            Dictionary mapping symbol names to their impact analysis results
        """
        results = {}
        for symbol_name in symbol_names:
            results[symbol_name] = self.analyze_impact(symbol_name, max_depth)
        return results
    
    def analyze_project_wide_impact(self, max_symbols: int = 100) -> Dict[str, Dict]:
        """Get project-wide impact analysis for most critical symbols (LLM-optimized).
        
        Args:
            max_symbols: Maximum number of symbols to analyze
            
        Returns:
            Dictionary with comprehensive project impact data
        """
        # Get most connected symbols (functions and classes)
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT s.name, s.kind, s.file, COUNT(e.to_id) as dependency_count
                FROM symbols s
                LEFT JOIN edges e ON s.id = e.to_id
                WHERE s.kind IN ('function', 'method', 'class')
                GROUP BY s.id, s.name, s.kind, s.file
                ORDER BY dependency_count DESC
                LIMIT ?
            """, (max_symbols,))
            
            high_impact_symbols = cursor.fetchall()
        
        # Analyze impact for each high-impact symbol
        impact_results = {}
        summary = {
            "total_symbols_analyzed": len(high_impact_symbols),
            "high_risk_symbols": [],
            "project_coupling_score": 0,
            "most_critical_files": []
        }
        
        for symbol in high_impact_symbols:
            symbol_name = symbol['name']
            result = self.analyze_impact(symbol_name, max_depth=3)  # Shorter depth for batch
            impact_results[symbol_name] = result.to_dict()
            
            # Track high-risk symbols
            if result.total_impacts > 10:
                summary["high_risk_symbols"].append({
                    "name": symbol_name,
                    "file": symbol['file'],
                    "impacts": result.total_impacts
                })
        
        # Calculate project coupling score
        total_impacts = sum(result['total_impacts'] for result in impact_results.values())
        summary["project_coupling_score"] = total_impacts / len(high_impact_symbols) if high_impact_symbols else 0
        
        # Find most critical files
        file_impact_counts = {}
        for result in impact_results.values():
            for file_path in result.get('impacts_by_file', {}):
                file_impact_counts[file_path] = file_impact_counts.get(file_path, 0) + len(result['impacts_by_file'][file_path])
        
        summary["most_critical_files"] = sorted(
            file_impact_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        return {
            "summary": summary,
            "detailed_impacts": impact_results
        }
    
    def get_dependency_graph_for_symbols(self, symbol_names: List[str]) -> Dict[str, Dict]:
        """Get complete dependency graph for multiple symbols (LLM-optimized).
        
        Args:
            symbol_names: List of symbol names
            
        Returns:
            Complete dependency graph with both dependencies and dependents
        """
        results = {}
        
        for symbol_name in symbol_names:
            dependencies = self.analyze_dependencies(symbol_name)
            impacts = self.analyze_impact(symbol_name, max_depth=2)  # Limited depth for performance
            
            results[symbol_name] = {
                "dependencies": dependencies.to_dict(),
                "impacts": impacts.to_dict(),
                "coupling_metrics": {
                    "fan_in": impacts.total_impacts,  # How many depend on this
                    "fan_out": len(dependencies.direct_dependencies),  # How many this depends on
                    "instability": len(dependencies.direct_dependencies) / (impacts.total_impacts + len(dependencies.direct_dependencies)) if (impacts.total_impacts + len(dependencies.direct_dependencies)) > 0 else 0
                }
            }
        
        return results