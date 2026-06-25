import pytest

@pytest.mark.asyncio
async def test_reference_endpoint_missing_input(client):
    response = await client.post("/references", json={})
    
    assert response.status_code == 422
