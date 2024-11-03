from enum import Enum

class RoomCategory(Enum):
    LIVING_ROOM = "living_room"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    DINING_ROOM = "dining_room"

class ComponentType(Enum):
    FURNITURE = "furniture"
    APPLIANCE = "appliance"
    FIXTURE = "fixture"
    DECOR = "decor"

# Valid component types for each room category
ROOM_COMPONENT_MAPPINGS = {
    RoomCategory.LIVING_ROOM: [
        ComponentType.FURNITURE,
        ComponentType.DECOR
    ],
    RoomCategory.KITCHEN: [
        ComponentType.FURNITURE,
        ComponentType.APPLIANCE,
        ComponentType.FIXTURE
    ],
    RoomCategory.BEDROOM: [
        ComponentType.FURNITURE,
        ComponentType.DECOR,
        ComponentType.FIXTURE
    ],
    RoomCategory.BATHROOM: [
        ComponentType.FIXTURE,
        ComponentType.FURNITURE
    ],
    RoomCategory.DINING_ROOM: [
        ComponentType.FURNITURE,
        ComponentType.DECOR,
        ComponentType.FIXTURE
    ]
    # Add other room types...
}

def validate_component_category(room_category: str, component_type: str) -> tuple[bool, str]:
    """Validate if component type is valid for room category"""
    try:
        room = RoomCategory(room_category)
        comp_type = ComponentType(component_type)
        
        valid_types = ROOM_COMPONENT_MAPPINGS.get(room, [])
        if comp_type in valid_types:
            return True, f"Valid component type for {room_category}"
            
        valid_types_str = ", ".join([t.value for t in valid_types])
        return False, f"Component type '{component_type}' not valid for {room_category}. Valid types: {valid_types_str}"
    except ValueError:
        return False, "Invalid room category or component type"
    
def validate_confidence_score(score: float, threshold: float = 0.5) -> tuple[bool, str]:
    """Validate if a confidence score meets the minimum threshold"""
    is_valid = score >= threshold
    message = (
        f"Confidence score {score:.2f} meets threshold"
        if is_valid
        else f"Confidence score {score:.2f} below minimum threshold of {threshold:.2f}"
    )
    return is_valid, message

def suggest_component_type(confidence_scores: dict[str, float]) -> tuple[str, float]:
    """Suggest component type based on highest confidence score"""
    if not confidence_scores:
        return None, 0.0
        
    suggested_type = max(confidence_scores.items(), key=lambda x: x[1])
    return suggested_type[0], suggested_type[1]

def get_alternative_types(room_category: str, current_type: str) -> list[str]:
    """Get alternative valid component types for a room category"""
    try:
        room = RoomCategory(room_category)
        valid_types = ROOM_COMPONENT_MAPPINGS.get(room, [])
        alternatives = [t.value for t in valid_types if t.value != current_type]
        return alternatives
    except ValueError:
        return []

class ValidationResult:
    """Class to hold component validation results"""
    def __init__(self, 
                 is_valid: bool, 
                 message: str, 
                 category_valid: bool = False,
                 confidence_valid: bool = False,
                 suggested_type: str = None,
                 alternatives: list[str] = None):
        self.is_valid = is_valid
        self.message = message
        self.category_valid = category_valid
        self.confidence_valid = confidence_valid
        self.suggested_type = suggested_type
        self.alternatives = alternatives or []

    def to_dict(self) -> dict:
        return {
            'valid': self.is_valid,
            'message': self.message,
            'category_valid': self.category_valid,
            'confidence_valid': self.confidence_valid,
            'suggested_type': self.suggested_type,
            'alternatives': self.alternatives
        }