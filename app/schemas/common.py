from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

# Decimal in/out; serialised as a JSON number (Pydantic v2 would otherwise emit a string)
Money = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]

T = TypeVar("T")


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, str_strip_whitespace=True, from_attributes=True
    )


class ApiResponse(CamelModel, Generic[T]):
    """Uniform success envelope: {"success": true, "message": "...", "data": ...}"""

    success: bool = True
    message: str = "OK"
    data: T
