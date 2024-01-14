import orjson

from src.schemas.responses import E, T, BaseResponse


def serialize_response(response: BaseResponse[T, E] | bytes):
    """Convenience function that serializes responses if they are `BaseResponse`s, else returns them as-is."""

    if isinstance(response, BaseResponse):
        serialized_response = orjson.dumps(response.model_dump())
    else:
        serialized_response = response

    return serialized_response
