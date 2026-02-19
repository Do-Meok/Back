from pydantic import ConfigDict
from datetime import datetime

from domains.assistant.schemas import DetailRecipeResponse


class SaveRecipeRequest(DetailRecipeResponse):
    pass


class SavedRecipeResponse(DetailRecipeResponse):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
