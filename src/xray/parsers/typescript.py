"""TypeScript parser using Tree-sitter for XRAY."""

import tree_sitter
from typing import List, Set
from .base import LanguageParser, Symbol, Edge


class TypeScriptParser(LanguageParser):
    """Parser for TypeScript source code."""
    
    def __init__(self, language: tree_sitter.Language):
        """Initialize TypeScript parser."""
        super().__init__(language)
        
        # Simplified Tree-sitter queries for core TypeScript symbols
        self.symbol_query = tree_sitter.Query(self.language, """
            (function_declaration name: (identifier) @function.name) @function.def
            (class_declaration name: (type_identifier) @class.name) @class.def
            (interface_declaration name: (type_identifier) @interface.name) @interface.def
            (type_alias_declaration name: (type_identifier) @type.name) @type.def
            (enum_declaration name: (identifier) @enum.name) @enum.def
            (variable_declarator name: (identifier) @var.name value: (arrow_function)) @arrow.def
            (import_statement source: (string (string_fragment) @import.source))
            (export_statement declaration: (function_declaration name: (identifier) @export.function))
            (export_statement declaration: (class_declaration name: (type_identifier) @export.class))
            (export_statement declaration: (interface_declaration name: (type_identifier) @export.interface))
        """)
        
        # Simple call query for impact analysis
        self.call_query = tree_sitter.Query(self.language, """
            (call_expression function: (identifier) @call.name)
            (call_expression function: (member_expression property: (property_identifier) @call.method))
        """)
    
    def extract_symbols(self, source_code: bytes, file_path: str) -> List[Symbol]:
        """Extract symbols from TypeScript source code."""
        tree = self.parser.parse(source_code)
        symbols = []
        
        # Extract functions
        matches = self.function_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            # Handle function declarations
            if 'function.name' in captures and 'function.def' in captures:
                name_node = captures['function.name'][0]
                def_node = captures['function.def'][0]
                
                signature = self._extract_function_signature(def_node, source_code)
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='function',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=signature
                )
                symbols.append(symbol)
            
            # Handle arrow functions assigned to variables
            elif 'var.name' in captures and 'var.arrow' in captures:
                name_node = captures['var.name'][0]
                arrow_node = captures['var.arrow'][0]
                
                signature = f"const {name_node.text.decode('utf-8')} = () => {{}}"
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='function',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=arrow_node.end_point[0] + 1,
                    signature=signature
                )
                symbols.append(symbol)
            
            # Handle function expressions assigned to variables
            elif 'var.name' in captures and 'var.func' in captures:
                name_node = captures['var.name'][0]
                func_node = captures['var.func'][0]
                
                signature = f"const {name_node.text.decode('utf-8')} = function() {{}}"
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='function',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=func_node.end_point[0] + 1,
                    signature=signature
                )
                symbols.append(symbol)
        
        # Extract classes (including abstract classes)
        class_symbols = {}  # Track class symbols for method parent assignment
        matches = self.class_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'class.name' in captures:
                name_node = captures['class.name'][0]
                def_node = captures['class.def'][0]
                
                if def_node:
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='class',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        end_line=def_node.end_point[0] + 1,
                        signature=f"class {name_node.text.decode('utf-8')}"
                    )
                    symbols.append(symbol)
                    class_symbols[name_node.text.decode('utf-8')] = len(symbols) - 1
            elif 'class.expr' in captures:
                def_node = captures['class.expr'][0]
                name_node = None
                # Find the type_identifier child of the class_expression
                for child in def_node.children:
                    if child.type == 'type_identifier':
                        name_node = child
                        break
                
                if name_node:
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='class',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        end_line=def_node.end_point[0] + 1,
                        signature=f"class {name_node.text.decode('utf-8')}"
                    )
                    symbols.append(symbol)
                    class_symbols[name_node.text.decode('utf-8')] = len(symbols) - 1
            
            # Abstract classes
            elif 'abstract.class.name' in captures:
                name_node = captures['abstract.class.name'][0]
                def_node = captures['abstract.class'][0]
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='class',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=f"abstract class {name_node.text.decode('utf-8')}"
                )
                symbols.append(symbol)
                class_symbols[name_node.text.decode('utf-8')] = len(symbols) - 1
        
        # Extract interfaces, type aliases, and enums (TypeScript specific)
        matches = self.interface_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            # Interfaces
            if 'interface.name' in captures:
                name_node = captures['interface.name'][0]
                def_node = captures['interface.def'][0]
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='interface',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=f"interface {name_node.text.decode('utf-8')}"
                )
                symbols.append(symbol)
                # Track interfaces for method signatures
                class_symbols[name_node.text.decode('utf-8')] = len(symbols) - 1
            
            # Type aliases
            elif 'type.alias.name' in captures:
                name_node = captures['type.alias.name'][0]
                def_node = captures['type.alias'][0]
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='type',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=f"type {name_node.text.decode('utf-8')}"
                )
                symbols.append(symbol)
            
            # Enums
            elif 'enum.name' in captures:
                name_node = captures['enum.name'][0]
                def_node = captures['enum.def'][0]
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='enum',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=f"enum {name_node.text.decode('utf-8')}"
                )
                symbols.append(symbol)
        
        # Extract methods
        matches = self.method_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'method.name' in captures:
                name_node = captures['method.name'][0]
                def_node = captures.get('method.def', captures.get('method.private', [None]))[0]
                
                if def_node:
                    # Find parent class/interface
                    parent_type = self._find_parent_type_for_method(def_node)
                    parent_id = None
                    if parent_type and parent_type in class_symbols:
                        parent_id = class_symbols[parent_type]
                    
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='method',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        end_line=def_node.end_point[0] + 1,
                        signature=self._extract_method_signature(def_node, source_code),
                        parent_id=parent_id
                    )
                    symbols.append(symbol)
            
            # Abstract method signatures
            elif 'abstract.method.name' in captures:
                name_node = captures['abstract.method.name'][0]
                def_node = captures['abstract.method'][0]
                
                parent_type = self._find_parent_type_for_method(def_node)
                parent_id = None
                if parent_type and parent_type in class_symbols:
                    parent_id = class_symbols[parent_type]
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='method',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=f"abstract {name_node.text.decode('utf-8')}()",
                    parent_id=parent_id
                )
                symbols.append(symbol)
        
        # Extract imports
        matches = self.import_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            # Import source
            if 'import.source' in captures:
                source_node = captures['import.source'][0]
                source_text = source_node.text.decode('utf-8')
                
                # Default imports
                if 'import.default' in captures:
                    name_node = captures['import.default'][0]
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='import',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        signature=f"import {name_node.text.decode('utf-8')} from '{source_text}'"
                    )
                    symbols.append(symbol)
                
                # Named imports
                if 'import.name' in captures:
                    for name_node in captures['import.name']:
                        symbol = Symbol(
                            name=name_node.text.decode('utf-8'),
                            kind='import',
                            file=file_path,
                            line=name_node.start_point[0] + 1,
                            column=name_node.start_point[1],
                            signature=f"import {{ {name_node.text.decode('utf-8')} }} from '{source_text}'"
                        )
                        symbols.append(symbol)
                
                # Namespace imports
                if 'import.namespace' in captures:
                    name_node = captures['import.namespace'][0]
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='import',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        signature=f"import * as {name_node.text.decode('utf-8')} from '{source_text}'"
                    )
                    symbols.append(symbol)
            

        
        return symbols
    
    def extract_edges(self, source_code: bytes, file_path: str, symbols: List[Symbol]) -> List[Edge]:
        """Extract dependency edges from TypeScript source code."""
        tree = self.parser.parse(source_code)
        edges = []
        
        # Create symbol lookup for this file
        symbol_names = {symbol.name for symbol in symbols}
        
        # Helper function to check if a symbol exists globally
        def symbol_exists_globally(name: str) -> bool:
            return bool(name and name != "<module>")
        
        # Extract function calls
        matches = self.call_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            caller = None
            called_function = None
            
            if 'call.name' in captures:
                # Simple function call
                call_node = captures['call.name'][0]
                called_function = call_node.text.decode('utf-8')
                caller = self._find_enclosing_function_or_method(call_node)
                
            elif 'call.method' in captures and 'call.object' in captures:
                # Method call
                method_node = captures['call.method'][0]
                object_node = captures['call.object'][0]
                called_function = method_node.text.decode('utf-8')
                object_name = object_node.text.decode('utf-8')
                caller = self._find_enclosing_function_or_method(method_node)
                
                if caller:
                    # Handle this.method() calls
                    if object_name == 'this':
                        if symbol_exists_globally(called_function):
                            edges.append(Edge(
                                from_symbol=caller,
                                to_symbol=called_function,
                                from_file=file_path,
                                to_file=file_path
                            ))
                    else:
                        # For any method call, create edge to the method
                        if symbol_exists_globally(called_function):
                            edges.append(Edge(
                                from_symbol=caller,
                                to_symbol=called_function,
                                from_file=file_path,
                                to_file=None  # Enable cross-file resolution
                            ))
                        
                        # Also create edge to the object
                        if symbol_exists_globally(object_name):
                            edges.append(Edge(
                                from_symbol=caller,
                                to_symbol=object_name,
                                from_file=file_path,
                                to_file=file_path
                            ))
            
            elif 'new.class' in captures:
                # Constructor call
                class_node = captures['new.class'][0]
                called_function = class_node.text.decode('utf-8')
                caller = self._find_enclosing_function_or_method(class_node)
            
            elif 'new.namespace' in captures and 'new.class_name' in captures:
                # Namespaced constructor call (e.g., new namespace.ClassName())
                class_node = captures['new.class_name'][0]
                namespace_node = captures['new.namespace'][0]
                called_function = class_node.text.decode('utf-8')
                namespace_name = namespace_node.text.decode('utf-8')
                caller = self._find_enclosing_function_or_method(class_node)
                
                if caller:
                    # Create edge to the class
                    if symbol_exists_globally(called_function):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=called_function,
                            from_file=file_path,
                            to_file=None
                        ))
                    # Create edge to the namespace
                    if symbol_exists_globally(namespace_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=namespace_name,
                            from_file=file_path,
                            to_file=None
                        ))
            
            # Create edge if valid
            if caller and called_function and symbol_exists_globally(called_function):
                edges.append(Edge(
                    from_symbol=caller,
                    to_symbol=called_function,
                    from_file=file_path,
                    to_file=None  # Enable cross-file resolution
                ))
        
        # Extract type references (TypeScript specific)
        matches = self.type_reference_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'type.ref' in captures:
                type_node = captures['type.ref'][0]
                type_name = type_node.text.decode('utf-8')
                
                # Skip primitive types
                if type_name not in {'string', 'number', 'boolean', 'void', 'any', 'unknown', 'never', 'object'}:
                    caller = self._find_enclosing_function_or_method(type_node)
                    if caller and symbol_exists_globally(type_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=type_name,
                            from_file=file_path,
                            to_file=None
                        ))
        
        # Extract member access dependencies
        matches = self.member_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'member.object' in captures and 'member.property' in captures:
                object_node = captures['member.object'][0]
                property_node = captures['member.property'][0]
                object_name = object_node.text.decode('utf-8')
                property_name = property_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function_or_method(object_node)
                
                if caller:
                    if symbol_exists_globally(object_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=object_name,
                            from_file=file_path,
                            to_file=file_path
                        ))
                    if symbol_exists_globally(property_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=property_name,
                            from_file=file_path,
                            to_file=None  # Enable cross-file resolution
                        ))
        
        # Extract assignment dependencies
        matches = self.assignment_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'assign.function' in captures:
                # Variable assigned from function call
                function_node = captures['assign.function'][0]
                function_name = function_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function_or_method(function_node)
                if caller and symbol_exists_globally(function_name):
                    edges.append(Edge(
                        from_symbol=caller,
                        to_symbol=function_name,
                        from_file=file_path,
                        to_file=None  # Enable cross-file resolution
                    ))
            
            elif 'assign.class' in captures:
                # Variable assigned from class instantiation
                class_node = captures['assign.class'][0]
                class_name = class_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function_or_method(class_node)
                if caller and symbol_exists_globally(class_name):
                    edges.append(Edge(
                        from_symbol=caller,
                        to_symbol=class_name,
                        from_file=file_path,
                        to_file=None  # Enable cross-file resolution
                    ))
        
        return edges
    
    def _extract_function_signature(self, func_node: tree_sitter.Node, source_code: bytes) -> str:
        """Extract function signature from function node."""
        try:
            # Find the function header (up to the opening brace or semicolon for type signatures)
            start_byte = func_node.start_byte
            end_byte = func_node.start_byte
            
            # Find the opening brace or semicolon
            while end_byte < len(source_code):
                char = source_code[end_byte:end_byte+1]
                if char in [b'{', b';']:
                    break
                end_byte += 1
            
            signature_bytes = source_code[start_byte:end_byte]
            return signature_bytes.decode('utf-8', errors='ignore').strip()
        except:
            return ""
    
    def _extract_method_signature(self, method_node: tree_sitter.Node, source_code: bytes) -> str:
        """Extract method signature from method node."""
        try:
            # For methods, we want the full signature including type annotations
            start_byte = method_node.start_byte
            end_byte = method_node.start_byte
            
            # Find the opening brace or semicolon
            while end_byte < len(source_code):
                char = source_code[end_byte:end_byte+1]
                if char in [b'{', b';']:
                    break
                end_byte += 1
            
            signature_bytes = source_code[start_byte:end_byte]
            return signature_bytes.decode('utf-8', errors='ignore').strip()
        except:
            return ""
    
    def _find_parent_type_for_method(self, method_node: tree_sitter.Node) -> str:
        """Find the parent class/interface name for a method."""
        current = method_node.parent
        
        while current:
            if current.type in ['class_declaration', 'class_expression', 'abstract_class_declaration']:
                # Find the class name
                for child in current.children:
                    if child.type == 'type_identifier':
                        return child.text.decode('utf-8')
            elif current.type == 'interface_declaration':
                # Find the interface name
                for child in current.children:
                    if child.type == 'type_identifier':
                        return child.text.decode('utf-8')
            current = current.parent
        
        return None
    
    def _find_enclosing_function_or_method(self, node: tree_sitter.Node) -> str:
        """Find the name of the function/method that encloses this node."""
        current = node.parent
        class_name = None
        
        while current:
            if current.type in ['function_declaration', 'function_expression']:
                # Find the function name
                for child in current.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                        
                        # If we found a class, prefix the method name
                        if class_name:
                            return f"{class_name}.{func_name}"
                        return func_name
                
                # For anonymous functions, check if assigned to a variable
                parent = current.parent
                if parent and parent.type == 'variable_declarator':
                    for child in parent.children:
                        if child.type == 'identifier':
                            func_name = child.text.decode('utf-8')
                            if class_name:
                                return f"{class_name}.{func_name}"
                            return func_name
                
            elif current.type == 'method_definition':
                # Find the method name
                for child in current.children:
                    if child.type in ['property_identifier', 'private_property_identifier']:
                        method_name = child.text.decode('utf-8')
                        
                        # Find the parent type
                        parent_type = self._find_parent_type_for_method(current)
                        if parent_type:
                            return f"{parent_type}.{method_name}"
                        return method_name
                
            elif current.type in ['class_declaration', 'class_expression', 'abstract_class_declaration', 'interface_declaration'] and not class_name:
                # Remember the type name for method qualification
                for child in current.children:
                    if child.type in ['type_identifier', 'identifier']:
                        class_name = child.text.decode('utf-8')
                        break
            
            current = current.parent
        
        # If no enclosing function found, return module-level indicator
        return "<module>"