from ovigia_dados.sports.client import ApiFootballClient


def test_client_rotation():
    client = ApiFootballClient(api_keys=["key1", "key2", "key3"])
    assert client.get_current_key() == "key1"
    client.rotate_key()
    assert client.get_current_key() == "key2"
    client.rotate_key()
    assert client.get_current_key() == "key3"
    client.rotate_key()
    assert client.get_current_key() == "key1"
