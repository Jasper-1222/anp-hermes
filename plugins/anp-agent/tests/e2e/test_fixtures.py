import pytest


@pytest.mark.asyncio
async def test_did_document_server_hosts_document(did_document_server, anp_caller_identity):
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(did_document_server.document_url) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["id"] == anp_caller_identity["did"]
