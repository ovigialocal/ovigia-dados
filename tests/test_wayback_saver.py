from ovigia_dados.wayback.save import WaybackSaveResult


def test_wayback_saver_signature():
    # Teste de robustez de estrutura
    res = WaybackSaveResult(
        url="https://example.com",
        status="saved",
        archive_url="https://web.archive.org/web/https://example.com",
        http_status=200,
    )
    assert res.status == "saved"
    assert res.http_status == 200
