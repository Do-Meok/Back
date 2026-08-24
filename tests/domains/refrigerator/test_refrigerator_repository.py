import pytest
from domains.refrigerator.models import Compartment, Refrigerator
from domains.refrigerator.repository import RefrigeratorRepository


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


@pytest.mark.asyncio
async def test_get_refrigerators_success(db_session, test_user):
    """[Repository] 특정 사용자의 전체 냉장고 목록 및 칸(Compartment) 조회 테스트"""
    repo = RefrigeratorRepository(db_session)

    # Given: 동일한 사용자에게 2개의 냉장고 생성 (하나는 일반, 하나는 김치냉장고 가정)
    fridge1 = Refrigerator(user_id=test_user.id, name="메인 냉장고", pos_x=1, pos_y=1)
    fridge1.compartments.append(Compartment(name="냉장실", order_index=0))
    fridge1.compartments.append(Compartment(name="냉동실", order_index=1))

    fridge2 = Refrigerator(user_id=test_user.id, name="서브 냉장고", pos_x=2, pos_y=1)
    fridge2.compartments.append(Compartment(name="보관칸", order_index=0))

    db_session.add_all([fridge1, fridge2])
    await db_session.commit()

    # When: 해당 사용자의 아이디로 전체 냉장고 조회
    refrigerators = await repo.get_refrigerators(test_user.id)

    # Then
    assert len(refrigerators) == 2

    # selectinload(Eager Loading)가 잘 적용되어 칸 정보까지 가져왔는지 검증
    names = [f.name for f in refrigerators]
    assert "메인 냉장고" in names
    assert "서브 냉장고" in names

    # 메인 냉장고의 칸 개수 확인
    main_fridge = next(f for f in refrigerators if f.name == "메인 냉장고")
    assert len(main_fridge.compartments) == 2


@pytest.mark.asyncio
async def test_delete_refrigerator_success(db_session, test_user):
    """[Repository] 냉장고 삭제 시 정상적으로 DB에서 지워지는지 테스트"""
    repo = RefrigeratorRepository(db_session)

    # Given: 삭제할 냉장고 미리 생성 및 저장
    fridge = Refrigerator(user_id=test_user.id, name="버릴 냉장고", pos_x=3, pos_y=3)
    db_session.add(fridge)
    await db_session.commit()

    # 삭제 전 DB에 존재하는지 확실히 검증
    saved_fridge = await repo.get_refrigerator(fridge.id)
    assert saved_fridge is not None

    # When: 삭제 메서드 실행
    await repo.delete_refrigerator(saved_fridge)

    # Then: 삭제 후 다시 조회했을 때 None이어야 함
    deleted_fridge = await repo.get_refrigerator(fridge.id)
    assert deleted_fridge is None
