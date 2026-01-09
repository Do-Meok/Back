from domains.ingredient.exceptions import (
    IngredientNotFoundException,
    ValueNotFoundException,
)
from domains.ingredient.repository import IngredientRepository
from domains.user.models import User
from domains.ingredient.schemas import (
    AddIngredientRequest,
    AddIngredientResponse,
    SetIngredientRequest,
    StorageType,
    GetIngredientResponse,
    UpdateIngredientRequest,
)
from domains.ingredient.models import Ingredient


class IngredientService:
    def __init__(self, user: User, ingredient_repo: IngredientRepository):
        self.user = user
        self.ingredient_repo = ingredient_repo

    async def add_ingredient(
        self, request: AddIngredientRequest
    ) -> list[AddIngredientResponse]:
        ingredients_to_save = [
            Ingredient(
                user_id=self.user.id,
                ingredient_name=name,
                purchase_date=request.purchase_date,
            )
            for name in request.ingredients
        ]

        saved_ingredients = await self.ingredient_repo.add_ingredients(
            ingredients_to_save
        )

        return [AddIngredientResponse.model_validate(i) for i in saved_ingredients]

    async def set_expiration_and_storage(
        self, ingredient_id: int, request: SetIngredientRequest
    ):
        if not request.expiration_date:
            raise ValueNotFoundException()

        if not request.storage_type:
            raise ValueNotFoundException()

        updated = await self.ingredient_repo.set_ingredient(
            ingredient_id,
            self.user.id,
            request.expiration_date,
            request.storage_type.value,
        )
        if not updated:
            raise IngredientNotFoundException()

        return updated

    async def get_ingredients(
        self, storage: StorageType | None = None, is_unclassified: bool | None = None
    ):
        ingredient_list = await self.ingredient_repo.get_ingredients(
            user_id=self.user.id, storage=storage, is_unclassified=is_unclassified
        )

        return [
            GetIngredientResponse(
                id=ingredient.id,
                ingredient_name=ingredient.ingredient_name,
                purchase_date=ingredient.purchase_date,
                expiration_date=ingredient.expiration_date,
                storage_type=ingredient.storage_type,
            )
            for ingredient in ingredient_list
        ]

    async def get_ingredient(self, ingredient_id: int) -> GetIngredientResponse | None:
        ingredient = await self.ingredient_repo.get_ingredient(
            ingredient_id, self.user.id
        )

        if not ingredient:
            raise IngredientNotFoundException()

        return GetIngredientResponse(
            id=ingredient.id,
            ingredient_name=ingredient.ingredient_name,
            purchase_date=ingredient.purchase_date,
            expiration_date=ingredient.expiration_date,
            storage_type=ingredient.storage_type,
        )

    async def delete_ingredient(self, ingredient_id: int):
        is_deleted = await self.ingredient_repo.delete_ingredient(
            ingredient_id, self.user.id
        )

        if not is_deleted:
            raise IngredientNotFoundException()

    async def update_ingredient(
        self, ingredient_id: int, request: UpdateIngredientRequest
    ) -> GetIngredientResponse:
        storage_value = request.storage_type.value if request.storage_type else None

        updated_ingredient = await self.ingredient_repo.update_ingredient(
            ingredient_id=ingredient_id,
            user_id=self.user.id,
            purchase_date=request.purchase_date,
            expiration_date=request.expiration_date,
            storage_type=storage_value,
        )

        if not updated_ingredient:
            raise IngredientNotFoundException()

        return GetIngredientResponse(
            id=updated_ingredient.id,
            ingredient_name=updated_ingredient.ingredient_name,
            purchase_date=updated_ingredient.purchase_date,
            expiration_date=updated_ingredient.expiration_date,
            storage_type=updated_ingredient.storage_type,
        )
