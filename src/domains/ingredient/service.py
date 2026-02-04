from datetime import timedelta

from domains.ingredient.exceptions import (
    IngredientNotFoundException,
    ValueNotFoundException,
    NotFoundException,
    InvalidIngredientException,
)
from core.exception.exceptions import HaveNotPermissionException
from domains.ingredient.repository import IngredientRepository
from domains.user.models import User
from domains.ingredient.schemas import (
    AddIngredientRequest,
    AddIngredientResponse,
    SetIngredientRequest,
    StorageType,
    GetIngredientResponse,
    UpdateIngredientRequest,
    BulkMoveIngredientRequest,
    BulkMoveResponse,
)
from domains.ingredient.models import (
    Ingredient,
    MissingIngredientLog,
    ExpiryDeviationLog,
)


class IngredientService:
    def __init__(self, user: User, ingredient_repo: IngredientRepository):
        self.user = user
        self.ingredient_repo = ingredient_repo

    async def add_ingredient(
        self, request: AddIngredientRequest
    ) -> list[AddIngredientResponse]:
        banned_names = await self.ingredient_repo.get_existing_non_ingredients(
            request.ingredients
        )

        banned_set = set(banned_names)

        valid_names = [name for name in request.ingredients if name not in banned_set]

        if not valid_names:
            raise InvalidIngredientException()

        ingredients_to_save = [
            Ingredient(
                user_id=self.user.id,
                ingredient_name=name,
                purchase_date=request.purchase_date,
            )
            for name in valid_names
        ]

        saved_ingredients = await self.ingredient_repo.add_ingredients(
            ingredients_to_save
        )

        expiry_info_map = await self.ingredient_repo.get_expiry_infos(valid_names)

        missing_logs = []
        response_list = []

        for ing in saved_ingredients:
            if ing.ingredient_name not in expiry_info_map:
                missing_logs.append(
                    MissingIngredientLog(
                        user_id=self.user.id, ingredient_name=ing.ingredient_name
                    )
                )

            can_auto = ing.ingredient_name in expiry_info_map

            resp = AddIngredientResponse(
                id=ing.id,
                ingredient_name=ing.ingredient_name,
                purchase_date=ing.purchase_date,
                expiration_date=ing.expiration_date,
                storage_type=ing.storage_type,
                is_auto_fillable=can_auto,
            )
            response_list.append(resp)

        if missing_logs:
            await self.ingredient_repo.add_missing_logs(missing_logs)

        return response_list

    async def set_expiration_and_storage(
        self, ingredient_id: int, request: SetIngredientRequest
    ) -> GetIngredientResponse:
        if not request.expiration_date:
            raise ValueNotFoundException()
        if not request.storage_type:
            raise ValueNotFoundException()

        ingredient = await self.ingredient_repo.get_ingredient(
            ingredient_id, self.user.id
        )
        if not ingredient:
            raise IngredientNotFoundException()

        expiry_infos = await self.ingredient_repo.get_expiry_infos(
            [ingredient.ingredient_name]
        )
        can_auto = ingredient.ingredient_name in expiry_infos

        if can_auto:
            info = expiry_infos[ingredient.ingredient_name]
            user_days = (request.expiration_date - ingredient.purchase_date).days
            server_days = info.expiry_day
            diff = abs(user_days - server_days)

            is_date_deviated = diff >= 2
            is_storage_deviated = request.storage_type.value != info.storage_type

            if is_date_deviated or is_storage_deviated:
                log = ExpiryDeviationLog(
                    user_id=self.user.id,
                    ingredient_name=ingredient.ingredient_name,
                    deviation_day=diff,
                    storage_type=request.storage_type.value,
                )
                await self.ingredient_repo.add_deviation_log(log)

        updated = await self.ingredient_repo.set_ingredient(
            ingredient_id,
            self.user.id,
            request.expiration_date,
            request.storage_type.value,
        )

        if not updated:
            raise IngredientNotFoundException()

        return GetIngredientResponse(
            id=updated.id,
            ingredient_name=updated.ingredient_name,
            purchase_date=updated.purchase_date,
            expiration_date=updated.expiration_date,
            storage_type=updated.storage_type,
            is_auto_fillable=can_auto,
        )

    async def set_auto_expiration_and_storage(self, ingredient_id: int):
        ingredient = await self.ingredient_repo.get_ingredient(
            ingredient_id, self.user.id
        )
        if not ingredient:
            raise IngredientNotFoundException()

        expiry_infos = await self.ingredient_repo.get_expiry_infos(
            [ingredient.ingredient_name]
        )

        if ingredient.ingredient_name not in expiry_infos:
            raise NotFoundException(detail="자동 입력 데이터가 없는 식재료입니다.")

        info = expiry_infos[ingredient.ingredient_name]
        calculated_expiry = ingredient.purchase_date + timedelta(days=info.expiry_day)

        updated = await self.ingredient_repo.set_ingredient(
            ingredient_id, self.user.id, calculated_expiry, info.storage_type
        )

        return updated

    async def get_ingredients(
        self, storage: StorageType | None = None, is_unclassified: bool | None = None
    ):
        ingredient_list = await self.ingredient_repo.get_ingredients(
            user_id=self.user.id, storage=storage, is_unclassified=is_unclassified
        )

        if not ingredient_list:
            return []

        names = [ing.ingredient_name for ing in ingredient_list]
        expiry_info_map = await self.ingredient_repo.get_expiry_infos(names)

        response_list = []
        for ing in ingredient_list:
            can_auto = ing.ingredient_name in expiry_info_map
            resp = GetIngredientResponse(
                id=ing.id,
                ingredient_name=ing.ingredient_name,
                purchase_date=ing.purchase_date,
                expiration_date=ing.expiration_date,
                storage_type=ing.storage_type,
                is_auto_fillable=can_auto,
            )
            response_list.append(resp)

        return response_list

    async def get_ingredient(self, ingredient_id: int) -> GetIngredientResponse | None:
        ingredient = await self.ingredient_repo.get_ingredient(
            ingredient_id, self.user.id
        )

        if not ingredient:
            raise IngredientNotFoundException()

        expiry_infos = await self.ingredient_repo.get_expiry_infos(
            [ingredient.ingredient_name]
        )
        can_auto = ingredient.ingredient_name in expiry_infos

        return GetIngredientResponse(
            id=ingredient.id,
            ingredient_name=ingredient.ingredient_name,
            purchase_date=ingredient.purchase_date,
            expiration_date=ingredient.expiration_date,
            storage_type=ingredient.storage_type,
            is_auto_fillable=can_auto,
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

        updated = await self.ingredient_repo.update_ingredient(
            ingredient_id=ingredient_id,
            user_id=self.user.id,
            purchase_date=request.purchase_date,
            expiration_date=request.expiration_date,
            storage_type=storage_value,
        )

        if not updated:
            raise IngredientNotFoundException()

        expiry_infos = await self.ingredient_repo.get_expiry_infos(
            [updated.ingredient_name]
        )
        can_auto = updated.ingredient_name in expiry_infos

        return GetIngredientResponse(
            id=updated.id,
            ingredient_name=updated.ingredient_name,
            purchase_date=updated.purchase_date,
            expiration_date=updated.expiration_date,
            storage_type=updated.storage_type,
            is_auto_fillable=can_auto,
        )

    async def get_ingredients_in_compartment(
        self, compartment_id: int
    ) -> list[GetIngredientResponse]:
        ingredients = await self.ingredient_repo.get_ingredients_by_compartment(
            compartment_id, self.user.id
        )

        if not ingredients:
            return []

        names = [ing.ingredient_name for ing in ingredients]
        expiry_info_map = await self.ingredient_repo.get_expiry_infos(names)

        return [
            GetIngredientResponse(
                id=i.id,
                ingredient_name=i.ingredient_name,
                purchase_date=i.purchase_date,
                expiration_date=i.expiration_date,
                storage_type=i.storage_type,
                is_auto_fillable=i.ingredient_name in expiry_info_map,
            )
            for i in ingredients
        ]

    async def get_unassigned_ingredients(self) -> list[GetIngredientResponse]:
        ingredients = await self.ingredient_repo.get_unassigned_ingredients(
            self.user.id
        )

        if not ingredients:
            return []

        names = [ing.ingredient_name for ing in ingredients]
        expiry_info_map = await self.ingredient_repo.get_expiry_infos(names)

        return [
            GetIngredientResponse(
                id=i.id,
                ingredient_name=i.ingredient_name,
                purchase_date=i.purchase_date,
                expiration_date=i.expiration_date,
                storage_type=i.storage_type,
                is_auto_fillable=i.ingredient_name in expiry_info_map,
            )
            for i in ingredients
        ]

    async def move_ingredients(
        self, target_compartment_id: int, request: BulkMoveIngredientRequest
    ) -> BulkMoveResponse:
        is_my_compartment = await self.ingredient_repo.is_my_compartment(
            target_compartment_id, self.user.id
        )

        if not is_my_compartment:
            raise HaveNotPermissionException()

        count = await self.ingredient_repo.bulk_update_compartment(
            ingredient_ids=request.ingredient_ids,
            target_compartment_id=target_compartment_id,
            user_id=self.user.id,
        )

        if count != len(request.ingredient_ids):
            raise NotFoundException()

        return BulkMoveResponse(
            moved_count=count,
            message=f"식재료 {count}개가 성공적으로 이동되었습니다.",
            ingredient_ids=request.ingredient_ids,
        )
