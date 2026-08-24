from unittest.mock import AsyncMock, MagicMock

import pytest
from domains.refrigerator.exception import RefrigeratorNotFoundException
from domains.refrigerator.schemas import AddRefrigeratorRequest
from domains.refrigerator.service import RefrigeratorService

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

    async def test_get_refrigerators_success(self, mocks):
        """[Service] 사용자의 전체 냉장고 목록 조회 성공"""
        user, repo = mocks
        service = RefrigeratorService(user, repo)

        # Given: Pydantic model_validate를 통과할 수 있도록 가짜 객체 생성
        class DummyFridge:
            def __init__(self, id, name, pos_x, pos_y):
                self.id = id
                self.name = name
                self.pos_x = pos_x
                self.pos_y = pos_y
                self.compartments = []

        repo.get_refrigerators.return_value = [
            DummyFridge(id=1, name="메인냉장고", pos_x=2, pos_y=2),
            DummyFridge(id=2, name="김치냉장고", pos_x=1, pos_y=1),
        ]

        # When
        result = await service.get_refrigerators()

        # Then
        repo.get_refrigerators.assert_called_once_with(user.id)
        assert len(result) == 2
        # 반환된 객체가 GetRefrigeratorResponse로 잘 변환되었는지 속성 확인
        assert result[0].name == "메인냉장고"
        assert result[1].name == "김치냉장고"

    async def test_delete_refrigerator_success(self, mocks):
        """[Service] 내 냉장고 삭제 성공"""
        user, repo = mocks
        service = RefrigeratorService(user, repo)

        # Given: 내 소유의 냉장고 Mock
        mock_ref = MagicMock()
        mock_ref.id = 10
        mock_ref.user_id = user.id  # 권한 통과를 위해 내 ID와 동일하게 설정

        repo.get_refrigerator.return_value = mock_ref

        # When
        await service.delete_refrigerator(10)

        # Then
        repo.get_refrigerator.assert_called_once_with(10)
        repo.delete_refrigerator.assert_called_once_with(mock_ref)

    async def test_delete_refrigerator_not_found(self, mocks):
        """[Service] 없는 냉장고 삭제 시 예외 발생"""
        user, repo = mocks
        service = RefrigeratorService(user, repo)

        # Given: DB 조회 결과가 None
        repo.get_refrigerator.return_value = None

        # When & Then
        with pytest.raises(RefrigeratorNotFoundException) as exc:
            await service.delete_refrigerator(999)
        assert "삭제할 냉장고를 찾을 수 없습니다" in str(exc.value)

        repo.delete_refrigerator.assert_not_called()

    async def test_delete_refrigerator_forbidden(self, mocks):
        """[Service] 남의 냉장고 삭제 시 예외 발생 (권한 없음)"""
        user, repo = mocks
        service = RefrigeratorService(user, repo)

        # Given: 남의 소유로 된 냉장고 Mock
        mock_ref = MagicMock()
        mock_ref.id = 10
        mock_ref.user_id = "other-user-999"  # 내 ID와 다름

        repo.get_refrigerator.return_value = mock_ref

        # When & Then
        with pytest.raises(RefrigeratorNotFoundException) as exc:
            await service.delete_refrigerator(10)
        assert "삭제 권한이 없습니다" in str(exc.value)

        repo.delete_refrigerator.assert_not_called()
