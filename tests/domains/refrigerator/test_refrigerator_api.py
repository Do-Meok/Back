import pytest
from domains.refrigerator.models import Refrigerator, Compartment

# 라우터 prefix가 /api/v1/refrigerator 라고 가정합니다.
BASE_URL = "/api/v1/refrigerator"


@pytest.mark.asyncio
async def test_create_refrigerator_api(authorized_client):
    """[API] 냉장고 생성 POST"""
    payload = {"name": "API테스트냉장고", "pos_x": 3, "pos_y": 1}

    response = await authorized_client.post(BASE_URL, json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API테스트냉장고"
    # 응답 모델에 compartments가 포함되어 있다면 확인 (response_model 정의에 따라 다름)
    # 보통 AddResponse에는 id 정도만 주거나 전체를 주기도 함.


@pytest.mark.asyncio
async def test_get_refrigerator_api(authorized_client, db_session, test_user):
    """[API] 냉장고 상세 조회 GET"""
    # Setup: DB에 데이터 넣기
    fridge = Refrigerator(user_id=test_user.id, name="내꺼", pos_x=2, pos_y=2)
    # 칸 추가 (API 응답 확인용)
    c1 = Compartment(name="1번", order_index=0)
    c2 = Compartment(name="2번", order_index=1)
    fridge.compartments.extend([c1, c2])

    db_session.add(fridge)
    await db_session.commit()  # ID 생성

    # When
    response = await authorized_client.get(f"{BASE_URL}/{fridge.id}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "내꺼"
    assert len(data["compartments"]) == 2
    assert data["compartments"][0]["name"] == "1번"


@pytest.mark.asyncio
async def test_get_ingredients_in_compartment_api(authorized_client, db_session, test_user):
    """[API] 칸 내부 식재료 조회 GET"""
    # 1. 냉장고/칸 생성
    fridge = Refrigerator(user_id=test_user.id, name="재료테스트", pos_x=1, pos_y=1)
    db_session.add(fridge)
    await db_session.flush()

    comp = Compartment(refrigerator_id=fridge.id, name="칸1", order_index=0)
    db_session.add(comp)
    await db_session.commit()

    # 2. 식재료 서비스 로직은 이미 Mocking되거나 실제 동작하겠지만,
    # 여기서는 '엔드포인트가 정상 호출되는지'만 확인 (200 OK or 빈 리스트)
    # (실제 재료가 없으므로 빈 리스트 예상)

    response = await authorized_client.get(f"{BASE_URL}/{comp.id}/ingredients")

    # 내 칸이므로 접근 가능 -> 200 OK
    assert response.status_code == 200
    assert isinstance(response.json(), list)
