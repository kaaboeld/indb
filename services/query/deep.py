"""
Deep Query Module for INDB
Supports nested object access with dot notation
"""

from typing import Any, Dict, List, Optional, Union
import re

def get_nested_value(obj: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Get value from nested object using dot notation
    
    Args:
        obj: Object to query
        path: Dot notation path (e.g., "user.profile.name")
        default: Default value if path not found
    
    Returns:
        Value at path or default
    
    Examples:
        >>> obj = {"user": {"profile": {"name": "John"}}}
        >>> get_nested_value(obj, "user.profile.name")
        'John'
        >>> get_nested_value(obj, "user.age", 0)
        0
    """
    if not path:
        return obj
    
    parts = path.split(".")
    current = obj
    
    for part in parts:
        # Handle array indexing (e.g., "items[0]")
        match = re.match(r'(\w+)\[(\d+)\]', part)
        if match:
            key, index = match.groups()
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
            if not isinstance(current, list) or int(index) >= len(current):
                return default
            current = current[int(index)]
        else:
            # Regular key access
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
    
    return current


def set_nested_value(obj: Dict[str, Any], path: str, value: Any) -> None:
    """
    Set value in nested object using dot notation
    
    Args:
        obj: Object to modify
        path: Dot notation path
        value: Value to set
    
    Examples:
        >>> obj = {}
        >>> set_nested_value(obj, "user.profile.name", "John")
        >>> obj
        {'user': {'profile': {'name': 'John'}}}
    """
    if not path:
        raise ValueError("Path cannot be empty")
    
    parts = path.split(".")
    current = obj
    
    # Navigate to parent
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    
    # Set final value
    current[parts[-1]] = value


def has_nested_path(obj: Dict[str, Any], path: str) -> bool:
    """
    Check if nested path exists in object
    
    Args:
        obj: Object to check
        path: Dot notation path
    
    Returns:
        True if path exists, False otherwise
    """
    sentinel = object()
    return get_nested_value(obj, path, sentinel) is not sentinel


def delete_nested_value(obj: Dict[str, Any], path: str) -> bool:
    """
    Delete value at nested path
    
    Args:
        obj: Object to modify
        path: Dot notation path
    
    Returns:
        True if deleted, False if path didn't exist
    """
    if not path:
        return False
    
    parts = path.split(".")
    current = obj
    
    # Navigate to parent
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    
    # Delete final key
    if isinstance(current, dict) and parts[-1] in current:
        del current[parts[-1]]
        return True
    
    return False


def flatten_object(obj: Dict[str, Any], prefix: str = "", separator: str = ".") -> Dict[str, Any]:
    """
    Flatten nested object to dot notation keys
    
    Args:
        obj: Object to flatten
        prefix: Prefix for keys
        separator: Separator for keys
    
    Returns:
        Flattened dictionary
    
    Examples:
        >>> obj = {"user": {"profile": {"name": "John", "age": 30}}}
        >>> flatten_object(obj)
        {'user.profile.name': 'John', 'user.profile.age': 30}
    """
    result = {}
    
    for key, value in obj.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key
        
        if isinstance(value, dict):
            result.update(flatten_object(value, new_key, separator))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    result.update(flatten_object(item, f"{new_key}[{i}]", separator))
                else:
                    result[f"{new_key}[{i}]"] = item
        else:
            result[new_key] = value
    
    return result


def unflatten_object(flat_obj: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
    """
    Unflatten dot notation keys to nested object
    
    Args:
        flat_obj: Flattened dictionary
        separator: Separator used in keys
    
    Returns:
        Nested dictionary
    
    Examples:
        >>> flat = {'user.profile.name': 'John', 'user.profile.age': 30}
        >>> unflatten_object(flat)
        {'user': {'profile': {'name': 'John', 'age': 30}}}
    """
    result = {}
    
    for key, value in flat_obj.items():
        set_nested_value(result, key.replace(separator, "."), value)
    
    return result


def query_nested(obj: Dict[str, Any], query: str) -> List[Any]:
    """
    Query nested object with wildcard support
    
    Args:
        obj: Object to query
        query: Query with wildcards (e.g., "users.*.name")
    
    Returns:
        List of matching values
    
    Examples:
        >>> obj = {"users": [{"name": "John"}, {"name": "Jane"}]}
        >>> query_nested(obj, "users.*.name")
        ['John', 'Jane']
    """
    if "*" not in query:
        # No wildcard, simple get
        value = get_nested_value(obj, query)
        return [value] if value is not None else []
    
    # Split by wildcard
    parts = query.split(".")
    results = [obj]
    
    for part in parts:
        if part == "*":
            # Expand all keys/indices
            new_results = []
            for item in results:
                if isinstance(item, dict):
                    new_results.extend(item.values())
                elif isinstance(item, list):
                    new_results.extend(item)
            results = new_results
        else:
            # Regular key access
            new_results = []
            for item in results:
                if isinstance(item, dict) and part in item:
                    new_results.append(item[part])
                elif isinstance(item, list):
                    # Try to parse as index
                    try:
                        index = int(part)
                        if 0 <= index < len(item):
                            new_results.append(item[index])
                    except ValueError:
                        pass
            results = new_results
    
    return results


def filter_by_path(
    objects: List[Dict[str, Any]],
    path: str,
    value: Any,
    operator: str = "=="
) -> List[Dict[str, Any]]:
    """
    Filter objects by nested path value
    
    Args:
        objects: List of objects to filter
        path: Dot notation path
        value: Value to match
        operator: Comparison operator (==, !=, >, <, >=, <=, in, contains)
    
    Returns:
        Filtered list of objects
    
    Examples:
        >>> objects = [
        ...     {"user": {"age": 25}},
        ...     {"user": {"age": 30}}
        ... ]
        >>> filter_by_path(objects, "user.age", 25)
        [{'user': {'age': 25}}]
    """
    result = []
    
    for obj in objects:
        obj_value = get_nested_value(obj, path)
        
        if obj_value is None:
            continue
        
        match = False
        
        if operator == "==":
            match = obj_value == value
        elif operator == "!=":
            match = obj_value != value
        elif operator == ">":
            match = obj_value > value
        elif operator == "<":
            match = obj_value < value
        elif operator == ">=":
            match = obj_value >= value
        elif operator == "<=":
            match = obj_value <= value
        elif operator == "in":
            match = obj_value in value
        elif operator == "contains":
            match = value in obj_value
        
        if match:
            result.append(obj)
    
    return result


def merge_nested(obj1: Dict[str, Any], obj2: Dict[str, Any], overwrite: bool = True) -> Dict[str, Any]:
    """
    Deep merge two nested objects
    
    Args:
        obj1: First object
        obj2: Second object
        overwrite: Whether to overwrite existing values
    
    Returns:
        Merged object
    """
    result = obj1.copy()
    
    for key, value in obj2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = merge_nested(result[key], value, overwrite)
        elif key not in result or overwrite:
            result[key] = value
    
    return result
