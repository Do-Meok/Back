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


@pytest.mark.asyncio
async def test_get_refrigerators_api(authorized_client, db_session, test_user):
    """[API] 냉장고 전체 조회 GET"""
    # Given: 테스트용 냉장고 2개 생성
    fridge1 = Refrigerator(user_id=test_user.id, name="첫번째 냉장고", pos_x=1, pos_y=1)
    fridge2 = Refrigerator(user_id=test_user.id, name="두번째 냉장고", pos_x=2, pos_y=2)
    db_session.add_all([fridge1, fridge2])
    await db_session.commit()

    # When: 전체 조회 요청
    response = await authorized_client.get(BASE_URL)

    # Then
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # 생성한 냉장고가 목록에 포함되어 있는지 확인
    names = [f["name"] for f in data]
    assert "첫번째 냉장고" in names
    assert "두번째 냉장고" in names


@pytest.mark.asyncio
async def test_delete_refrigerator_api_success(authorized_client, db_session, test_user):
    """[API] 냉장고 삭제 DELETE 성공 테스트"""
    # Given: 삭제할 냉장고 생성
    fridge = Refrigerator(user_id=test_user.id, name="삭제될 냉장고", pos_x=1, pos_y=1)
    db_session.add(fridge)
    await db_session.commit()

    # When: 삭제 요청
    response = await authorized_client.delete(f"{BASE_URL}/{fridge.id}")

    # Then
    assert response.status_code == 204

    # 검증: 삭제 후 해당 ID로 조회 시 404 (또는 서비스 정책에 맞는 예외 코드) 발생 확인
    get_response = await authorized_client.get(f"{BASE_URL}/{fridge.id}")
    assert get_response.status_code in [403, 404]  # NotFound 또는 권한없음 예외가 발생해야 함


@pytest.mark.asyncio
async def test_delete_refrigerator_api_not_found(authorized_client):
    """[API] 냉장고 삭제 DELETE 존재하지 않는 ID 테스트"""
    # Given: 존재하지 않는 임의의 ID
    invalid_id = 999999

    # When: 삭제 요청
    response = await authorized_client.delete(f"{BASE_URL}/{invalid_id}")

    # Then: 적절한 에러 코드 확인 (예외 핸들러 설정에 따라 404 또는 403)
    assert response.status_code in [403, 404]


@pytest.mark.asyncio
async def test_create_refrigerator_api_validation_error(authorized_client):
    """[API] 냉장고 생성 POST 필수 데이터 누락 (422) 테스트"""
    # Given: AddRefrigeratorRequest 스키마에서 필수인 pos_x, pos_y를 누락
    payload = {"name": "잘못된 냉장고 데이터"}

    # When: 생성 요청
    response = await authorized_client.post(BASE_URL, json=payload)

    # Then: FastAPI 기본 Pydantic 검증 에러(422) 발생 확인
    assert response.status_code == 422
    assert "detail" in response.json()
