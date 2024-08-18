from typing import Any, Dict

from src.schemas.web_responses.common import COMMON_RESPONSES


GET_CATEGORIES_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    200: {
        "content": {
            "application/json": {
                "example": {
                    "error": "null",
                    "data": {
                        "category_groups": [
                            {
                                "group": "Currency",
                                "members": [
                                    {"name": "Currency", "internal_name": "Currency"},
                                    {"name": "Fragments", "internal_name": "Fragment"},
                                ],
                            }
                        ]
                    },
                }
            }
        }
    },
    **COMMON_RESPONSES,
}

GET_ITEMS_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    200: {
        "content": {
            "application/json": {
                "example": {
                    "error": None,
                    "pagination": {"page": 1, "per_page": 1, "total_items": 27431, "total_pages": 27431},
                    "data": {
                        "items": [
                            {
                                "poe_ninja_id": 81,
                                "id_type": "pay",
                                "name": "Mirror Shard",
                                "price": {
                                    "price": "4",
                                    "currency": "chaos",
                                    "price_history": {
                                        "2024-06-16T14:33:41.439096Z": "3",
                                        "2024-06-17T14:33:41.439099Z": "3",
                                        "2024-06-18T14:33:41.439101Z": "3",
                                        "2024-06-19T14:33:41.439104Z": "4",
                                        "2024-06-20T14:33:41.439106Z": "4",
                                        "2024-06-21T14:33:41.439108Z": "4",
                                        "2024-06-22T14:33:41.439110Z": "4",
                                    },
                                    "price_history_currency": "chaos",
                                    "price_prediction": {
                                        "2024-06-23T14:33:41.438877Z": "5365.58",
                                        "2024-06-24T14:33:41.438877Z": "5402.02",
                                        "2024-06-25T14:33:41.438877Z": "5435.12",
                                        "2024-06-26T14:33:41.438877Z": "5464.90",
                                    },
                                    "price_prediction_currency": "chaos",
                                },
                                "type_": None,
                                "variant": None,
                                "icon_url": "https://web.poecdn.com/6604b7aa32/MirrorShard.png",
                                "enabled": True,
                            }
                        ]
                    },
                }
            }
        }
    },
    422: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {
                        "type": "validation_error",
                        "message": "Input failed validation.",
                        "fields": [
                            {"error_type": "greater_than", "field": "page"},
                            {"error_type": "expected_int", "field": "page"},
                            {"error_type": "greater_than", "field": "per_page"},
                            {"error_type": "less_than_equal", "field": "per_page"},
                            {"error_type": "expected_int", "field": "per_page"},
                            {"error_type": "list_type", "field": "filter"},
                            {"error_type": "list_type", "field": "sort"},
                        ],
                    },
                }
            }
        },
        "data": None,
    },
    **COMMON_RESPONSES,
}
