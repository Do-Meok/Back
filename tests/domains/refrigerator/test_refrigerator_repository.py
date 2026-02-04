import pytest
from domains.refrigerator.repository import RefrigeratorRepository
from domains.refrigerator.models import Refrigerator, Compartment


@pytest.mark.asyncio
async def test_add_refrigerator_with_compartments(db_session, test_user):
    """[Repository] 냉장고와 칸들이 함께 저장되는지 테스트"""
    repo = RefrigeratorRepository(db_session)

    # Given
    refrigerator = Refrigerator(user_id=test_user.id, name="테스트냉장고", pos_x=2, pos_y=2)
    # 칸 4개 수동 추가 (Service 로직 흉내)
    for i in range(4):
        refrigerator.compartments.append(Compartment(name=f"{i}번", order_index=i))

    # When
    saved = await repo.add_refrigerator(refrigerator)

    # Then
    assert saved.id is not None
    assert len(saved.compartments) == 4
    assert saved.compartments[0].refrigerator_id == saved.id  # FK 잘 들어갔는지


@pytest.mark.asyncio
async def test_get_refrigerator_loading(db_session, test_user):
    """[Repository] 조회 시 compartments가 Eager Loading(selectinload) 되는지 확인"""
    repo = RefrigeratorRepository(db_session)

    # Setup: 데이터 미리 넣기
    refrigerator = Refrigerator(user_id=test_user.id, name="조회용", pos_x=1, pos_y=1)
    refrigerator.compartments.append(Compartment(name="칸1", order_index=0))

    db_session.add(refrigerator)
    await db_session.commit()
    await db_session.refresh(refrigerator)  # ID 확보

    # When: 조회
    # (주의: 세션을 새로고침하거나 분리해서 캐시가 아닌 DB에서 가져오게 하면 더 확실함)
    found = await repo.get_refrigerator(refrigerator.id)

    # Then
    assert found is not None
    assert found.name == "조회용"
    # selectinload 덕분에 await 없이 접근 가능해야 함
    assert len(found.compartments) == 1
    assert found.compartments[0].name == "칸1"
