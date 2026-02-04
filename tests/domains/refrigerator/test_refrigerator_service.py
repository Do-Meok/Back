import pytest
from unittest.mock import AsyncMock, MagicMock
from domains.refrigerator.service import RefrigeratorService
from domains.refrigerator.schemas import AddRefrigeratorRequest
from domains.refrigerator.exception import RefrigeratorNotFoundException
from domains.user.models import User


@pytest.mark.asyncio
class TestRefrigeratorService:
    @pytest.fixture
    def mocks(self):
        user = User(id="user-uuid-123")
        repo = AsyncMock()
        return user, repo

    async def test_add_refrigerator_logic(self, mocks):
        """[Service] pos_x * pos_y 만큼 칸이 자동 생성되는지 확인"""
        user, repo = mocks
        service = RefrigeratorService(user, repo)

        req = AddRefrigeratorRequest(name="메인냉장고", pos_x=2, pos_y=3)  # 2x3 = 6칸 예상

        # Mock: 저장된 후 반환될 객체 흉내
        mock_saved = MagicMock()
        mock_saved.id = 1
        mock_saved.name = "메인냉장고"
        mock_saved.compartments = []  # 실제 리턴값은 중요치 않음, repo 호출 인자가 중요

        repo.add_refrigerator.return_value = mock_saved

        # When
        await service.add_refrigerator(req)

        # Then: repo.add_refrigerator가 호출될 때 넘어간 객체를 검사
        args, _ = repo.add_refrigerator.call_args
        passed_refrigerator = args[0]

        assert passed_refrigerator.user_id == user.id
        assert len(passed_refrigerator.compartments) == 6  # ★핵심: 6개가 만들어졌는가?
        assert passed_refrigerator.compartments[0].name == "1번칸"
        assert passed_refrigerator.compartments[5].name == "6번칸"

    async def test_get_refrigerator_success(self, mocks):
        """[Service] 내 냉장고 조회 성공"""
        user, repo = mocks
        service = RefrigeratorService(user, repo)

        # Mock: 내 냉장고
        mock_ref = MagicMock(id=1, user_id=user.id)
        repo.get_refrigerator.return_value = mock_ref

        # When
        result = await service.get_refrigerator(1)

        # Then
        assert result == mock_ref

    async def test_get_refrigerator_not_found(self, mocks):
        """[Service] 없는 냉장고 조회 시 예외"""
        user, repo = mocks
        service = RefrigeratorService(user, repo)

        repo.get_refrigerator.return_value = None

        with pytest.raises(RefrigeratorNotFoundException) as exc:
            await service.get_refrigerator(999)
        assert "냉장고를 찾을 수 없습니다" in str(exc.value)

    async def test_get_refrigerator_forbidden(self, mocks):
        """[Service] 남의 냉장고 조회 시 예외"""
        user, repo = mocks
        service = RefrigeratorService(user, repo)

        # Mock: 남의 냉장고
        mock_ref = MagicMock(id=1, user_id="other-user-id")
        repo.get_refrigerator.return_value = mock_ref

        with pytest.raises(RefrigeratorNotFoundException) as exc:
            await service.get_refrigerator(1)
        assert "접근 권한이 없는" in str(exc.value)
