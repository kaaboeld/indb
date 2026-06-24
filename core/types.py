"""
Type System for INDB
Supports: number, bigint, string, struct, location (OSM), null
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import re


class FieldType(Enum):
    """Supported field types"""

    NUMBER = "number"  # float, int
    BIGINT = "bigint"  # Large integers
    STRING = "string"  # Text
    STRUCT = "struct"  # Nested object
    LOCATION = "location"  # OSM coordinates
    NULL = "null"  # Null value


@dataclass
class LocationField:
    """
    OSM (OpenStreetMap) location field

    Attributes:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
        osm_id: Optional OSM node/way/relation ID
    """

    lat: float
    lon: float
    osm_id: Optional[str] = None

    def __post_init__(self):
        """Validate coordinates"""
        if not -90 <= self.lat <= 90:
            raise ValueError(f"Invalid latitude: {self.lat}. Must be between -90 and 90")
        if not -180 <= self.lon <= 180:
            raise ValueError(f"Invalid longitude: {self.lon}. Must be between -180 and 180")

        # Validate OSM ID format if provided
        if self.osm_id:
            if not re.match(r"^(node|way|relation)/\d+$", self.osm_id):
                raise ValueError(
                    f"Invalid OSM ID format: {self.osm_id}. Expected: node/123, way/456, or relation/789"
                )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {"lat": self.lat, "lon": self.lon}
        if self.osm_id:
            result["osm_id"] = self.osm_id
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocationField":
        """Create from dictionary"""
        return cls(lat=data["lat"], lon=data["lon"], osm_id=data.get("osm_id"))

    def distance_to(self, other: "LocationField") -> float:
        """
        Calculate distance to another location in kilometers (Haversine formula)

        Args:
            other: Another LocationField

        Returns:
            Distance in kilometers
        """
        import math

        # Convert to radians
        lat1, lon1 = math.radians(self.lat), math.radians(self.lon)
        lat2, lon2 = math.radians(other.lat), math.radians(other.lon)

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        # Earth radius in kilometers
        r = 6371

        return c * r


class FieldSchema:
    """
    Schema definition for a field

    Attributes:
        name: Field name
        type: Field type (FieldType)
        required: Whether field is required
        nested_schema: Schema for nested fields (if type is STRUCT)
        constraints: Additional constraints (min, max, pattern, etc.)
    """

    def __init__(
        self,
        name: str,
        field_type: FieldType,
        required: bool = False,
        nested_schema: Optional[Dict[str, "FieldSchema"]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.type = field_type
        self.required = required
        self.nested_schema = nested_schema or {}
        self.constraints = constraints or {}

        # Validate nested schema for STRUCT types
        if field_type == FieldType.STRUCT and not nested_schema:
            raise ValueError(f"STRUCT field '{name}' must have nested_schema defined")

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate value against schema

        Args:
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required
        if value is None:
            if self.required:
                return False, f"Field '{self.name}' is required but got None"
            return True, None

        # Check type
        is_valid, error = self._validate_type(value)
        if not is_valid:
            return False, error

        # Check constraints
        is_valid, error = self._validate_constraints(value)
        if not is_valid:
            return False, error

        # Validate nested fields for STRUCT
        if self.type == FieldType.STRUCT:
            return self._validate_nested(value)

        return True, None

    def _validate_type(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate value type"""
        if self.type == FieldType.NULL:
            if value is not None:
                return False, f"Field '{self.name}' must be null"
            return True, None

        if self.type == FieldType.NUMBER:
            if not isinstance(value, (int, float)):
                return False, f"Field '{self.name}' must be number, got {type(value).__name__}"

        elif self.type == FieldType.BIGINT:
            if not isinstance(value, int):
                return False, f"Field '{self.name}' must be integer, got {type(value).__name__}"

        elif self.type == FieldType.STRING:
            if not isinstance(value, str):
                return False, f"Field '{self.name}' must be string, got {type(value).__name__}"

        elif self.type == FieldType.STRUCT:
            if not isinstance(value, dict):
                return False, f"Field '{self.name}' must be object/dict, got {type(value).__name__}"

        elif self.type == FieldType.LOCATION:
            if isinstance(value, dict):
                try:
                    LocationField.from_dict(value)
                except (KeyError, ValueError) as e:
                    return False, f"Field '{self.name}' invalid location: {str(e)}"
            elif not isinstance(value, LocationField):
                return False, f"Field '{self.name}' must be LocationField or dict"

        return True, None

    def _validate_constraints(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate constraints"""
        # Min/max for numbers
        if self.type in (FieldType.NUMBER, FieldType.BIGINT):
            if "min" in self.constraints and value < self.constraints["min"]:
                return False, f"Field '{self.name}' must be >= {self.constraints['min']}"
            if "max" in self.constraints and value > self.constraints["max"]:
                return False, f"Field '{self.name}' must be <= {self.constraints['max']}"

        # Pattern for strings
        if self.type == FieldType.STRING:
            if "pattern" in self.constraints:
                pattern = self.constraints["pattern"]
                if not re.match(pattern, value):
                    return False, f"Field '{self.name}' must match pattern {pattern}"

            if "min_length" in self.constraints and len(value) < self.constraints["min_length"]:
                return (
                    False,
                    f"Field '{self.name}' must be at least {self.constraints['min_length']} characters",
                )

            if "max_length" in self.constraints and len(value) > self.constraints["max_length"]:
                return (
                    False,
                    f"Field '{self.name}' must be at most {self.constraints['max_length']} characters",
                )

        return True, None

    def _validate_nested(self, value: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate nested fields"""
        if not isinstance(value, dict):
            return False, f"Field '{self.name}' must be object/dict for STRUCT type"

        # Check required nested fields
        for field_name, field_schema in self.nested_schema.items():
            field_value = value.get(field_name)
            is_valid, error = field_schema.validate(field_value)
            if not is_valid:
                return False, f"In '{self.name}.{field_name}': {error}"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary"""
        result = {"name": self.name, "type": self.type.value, "required": self.required}

        if self.nested_schema:
            result["nested_schema"] = {
                name: schema.to_dict() for name, schema in self.nested_schema.items()
            }

        if self.constraints:
            result["constraints"] = self.constraints

        return result


def validate_value(value: Any, schema: FieldSchema) -> Tuple[bool, Optional[str]]:
    """
    Validate a value against a schema

    Args:
        value: Value to validate
        schema: FieldSchema to validate against

    Returns:
        Tuple of (is_valid, error_message)
    """
    return schema.validate(value)


def validate_object(obj: Dict[str, Any], schema: Dict[str, FieldSchema]) -> Tuple[bool, List[str]]:
    """
    Validate an entire object against a schema

    Args:
        obj: Object to validate
        schema: Dictionary of field schemas

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    for field_name, field_schema in schema.items():
        value = obj.get(field_name)
        is_valid, error = field_schema.validate(value)
        if not is_valid:
            errors.append(error)

    return len(errors) == 0, errors


def infer_type(value: Any) -> FieldType:
    """
    Infer field type from value

    Args:
        value: Value to infer type from

    Returns:
        Inferred FieldType
    """
    if value is None:
        return FieldType.NULL

    if isinstance(value, bool):
        # Treat bool as number (0/1)
        return FieldType.NUMBER

    if isinstance(value, int):
        # Check if it's a big int (> 2^53)
        if abs(value) > 2**53:
            return FieldType.BIGINT
        return FieldType.NUMBER

    if isinstance(value, float):
        return FieldType.NUMBER

    if isinstance(value, str):
        return FieldType.STRING

    if isinstance(value, dict):
        # Check if it's a location
        if "lat" in value and "lon" in value:
            try:
                LocationField.from_dict(value)
                return FieldType.LOCATION
            except:
                pass
        return FieldType.STRUCT

    # Default to string for unknown types
    return FieldType.STRING
