from telegrab.introspection import describe_command
from telegrab.models import ExitCode, TelegrabError


def test_describe_root_command() -> None:
    target, description = describe_command(None)

    assert target == "telegrab"
    assert description["commands"] == ["fetch", "login", "status", "doctor", "describe"]


def test_describe_fetch_command() -> None:
    target, description = describe_command("fetch")

    assert target == "fetch"
    assert description["response"]["command"] == "fetch"
    assert description["options"][0]["name"] == "--output-dir"


def test_describe_unknown_command_raises() -> None:
    try:
        describe_command("unknown")
    except TelegrabError as err:
        assert err.code == ExitCode.INVALID_LINK
    else:
        raise AssertionError("Expected TelegrabError")
