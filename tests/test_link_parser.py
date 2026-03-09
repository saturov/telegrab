import pytest

from telegrab.link_parser import internal_channel_id_to_peer_id, parse_telegram_post_link
from telegrab.models import ExitCode, TelegrabError


def test_parse_public_t_me_link() -> None:
    parsed = parse_telegram_post_link("https://t.me/some_channel/42")
    assert parsed.username == "some_channel"
    assert parsed.message_id == 42
    assert parsed.internal_channel_id is None


def test_parse_public_telegram_me_link() -> None:
    parsed = parse_telegram_post_link("https://telegram.me/some_channel/42")
    assert parsed.username == "some_channel"
    assert parsed.message_id == 42


def test_parse_private_internal_link() -> None:
    parsed = parse_telegram_post_link("https://t.me/c/123456/987")
    assert parsed.internal_channel_id == 123456
    assert parsed.message_id == 987
    assert parsed.username is None


def test_parse_invalid_link_host() -> None:
    with pytest.raises(TelegrabError) as err:
        parse_telegram_post_link("https://example.com/channel/1")
    assert err.value.code == ExitCode.INVALID_LINK


def test_parse_invalid_message_id() -> None:
    with pytest.raises(TelegrabError) as err:
        parse_telegram_post_link("https://t.me/channel/not-a-number")
    assert err.value.code == ExitCode.INVALID_LINK


def test_parse_invalid_internal_channel_id() -> None:
    with pytest.raises(TelegrabError) as err:
        parse_telegram_post_link("https://t.me/c/0/12")
    assert err.value.code == ExitCode.INVALID_LINK


def test_parse_rejects_query_parameters() -> None:
    with pytest.raises(TelegrabError) as err:
        parse_telegram_post_link("https://telegram.me/some_channel/42?single")
    assert err.value.code == ExitCode.INVALID_LINK


def test_parse_rejects_fragments() -> None:
    with pytest.raises(TelegrabError) as err:
        parse_telegram_post_link("https://telegram.me/some_channel/42#fragment")
    assert err.value.code == ExitCode.INVALID_LINK


def test_parse_rejects_control_characters() -> None:
    with pytest.raises(TelegrabError) as err:
        parse_telegram_post_link("https://t.me/some_channel/42\n")
    assert err.value.code == ExitCode.INVALID_LINK


def test_internal_channel_to_peer_id() -> None:
    assert internal_channel_id_to_peer_id(123456) == -100123456
