"""
Utility functions for REALUM API
"""
from bson import ObjectId
from typing import Any, Dict, List, Union


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a MongoDB document for JSON response.
    Removes _id field and converts any ObjectId to string.
    """
    if doc is None:
        return None
    
    result = {}
    for key, value in doc.items():
        if key == "_id":
            continue  # Skip MongoDB's _id field
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        elif isinstance(value, list):
            result[key] = serialize_list(value)
        else:
            result[key] = value
    return result


def serialize_list(items: List[Any]) -> List[Any]:
    """
    Serialize a list of MongoDB documents or values.
    """
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(serialize_doc(item))
        elif isinstance(item, ObjectId):
            result.append(str(item))
        elif isinstance(item, list):
            result.append(serialize_list(item))
        else:
            result.append(item)
    return result


def prepare_response(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Prepare any data for JSON response by handling ObjectId serialization.
    """
    if isinstance(data, dict):
        return serialize_doc(data)
    elif isinstance(data, list):
        return serialize_list(data)
    elif isinstance(data, ObjectId):
        return str(data)
    return data
