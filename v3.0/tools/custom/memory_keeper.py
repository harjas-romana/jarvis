import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# Define the path where the creator information will be stored
_STORAGE_FILE = Path(__file__).parent / "creator_info.json"


def _load_storage() -> dict:
    if _STORAGE_FILE.exists():
        try:
            with open(_STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def _save_storage(data: dict) -> None:
    _STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class StoreCreatorInfoArgs(BaseModel):
    name: str = Field(..., description="Full name of the creator")
    info: str = Field(..., description="Information to store about the creator")


@tool(args_schema=StoreCreatorInfoArgs)
def store_creator_info(name: str, info: str) -> str:
    """
    Store information about a creator. Overwrites any existing entry with the same name.
    Returns a confirmation message.
    """
    data = _load_storage()
    data[name] = info
    _save_storage(data)
    return f"Information for '{name}' has been stored successfully."


class GetCreatorInfoArgs(BaseModel):
    name: str = Field(..., description="Full name of the creator to retrieve")


@tool(args_schema=GetCreatorInfoArgs)
def get_creator_info(name: str) -> Optional[str]:
    """
    Retrieve stored information about a creator.
    Returns the information string if found, otherwise returns None.
    """
    data = _load_storage()
    return data.get(name)