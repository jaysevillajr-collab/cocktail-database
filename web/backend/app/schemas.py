from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class CountsResponse(BaseModel):
    alcohol_inventory: int
    cocktail_notes: int


class RowPayload(BaseModel):
    data: Dict[str, Any]


class TwistRequest(BaseModel):
    cocktail_name: str
    ingredients: str = ""
    constraints: str = ""
    prompt: str = ""
    provider: str = "local"


class TwistSuggestion(BaseModel):
    name: str
    flavor_goal: str
    substitutions: List[str]
    method: List[str]
    garnish_and_glass: str
    why_it_works: str
    difficulty: str
    risk_note: str = ""
    wild_card: str = ""


class TwistResponse(BaseModel):
    provider: str
    suggestions: List[TwistSuggestion]
    note: str = ""


class TastingLogCreateRequest(BaseModel):
    date: str
    cocktail_name: str
    rating: str = ""
    notes: str = ""
    mood: str = ""
    occasion: str = ""
    location: str = ""
    would_make_again: str = ""
    change_next_time: str = ""
    sweetness: str = ""
    sourness: str = ""
    bitterness: str = ""
    booziness: str = ""
    body: str = ""
    aroma: str = ""
    balance: str = ""
    finish: str = ""


class TastingLogItem(BaseModel):
    id: str
    date: str
    cocktail_name: str
    rating: str = ""
    notes: str = ""
    mood: str = ""
    occasion: str = ""
    location: str = ""
    would_make_again: str = ""
    change_next_time: str = ""
    sweetness: str = ""
    sourness: str = ""
    bitterness: str = ""
    booziness: str = ""
    body: str = ""
    aroma: str = ""
    balance: str = ""
    finish: str = ""
    created_at: str


class TastingLogListResponse(BaseModel):
    items: List[TastingLogItem]


class AlcoholWriteRequest(BaseModel):
    Brand: str = ""
    Base_Liquor: str = ""
    Type: str = ""
    ABV: str = ""
    Country: str = ""
    Price_NZD_700ml: str = ""
    Taste: str = ""
    Substitute: str = ""
    Availability: str = ""
    image_path: str = ""


class CocktailWriteRequest(BaseModel):
    Cocktail_Name: str = ""
    Ingredients: str = ""
    Rating_Jason: str = ""
    Rating_Jaime: str = ""
    Rating_overall: str = ""
    Base_spirit_1: str = ""
    Type1: str = ""
    Brand1: str = ""
    Base_spirit_2: str = ""
    Type2: str = ""
    Brand2: str = ""
    Citrus: str = ""
    Garnish: str = ""
    Notes: str = ""
    DatetimeAdded: str = ""
    Prep_Time: str = ""
    Difficulty: str = ""
    image_path: str = ""


class SavedViewCreateRequest(BaseModel):
    name: str
    payload: Dict[str, Any]


class SavedViewItem(BaseModel):
    id: str
    name: str
    payload: Dict[str, Any]
    created_at: str


class SavedViewListResponse(BaseModel):
    items: List[SavedViewItem]


class TagCreateRequest(BaseModel):
    entity_type: str
    entity_rowid: int
    tag: str


class TagItem(BaseModel):
    id: str
    entity_type: str
    entity_rowid: int
    tag: str
    created_at: str


class TagListResponse(BaseModel):
    items: List[TagItem]
