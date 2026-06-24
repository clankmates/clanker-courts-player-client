from clanker_courts_player.runtime_registry import RegistryError, RunRegistry


def test_registry_creates_admin_and_run_tokens_without_storing_plaintext(tmp_path):
    registry = RunRegistry(tmp_path)
    admin_token = registry.ensure_admin_token()

    credentials = registry.create_run(
        profile="cc_blue",
        server="@server",
        game_id="game-1",
    )

    run = registry.get_run(credentials.run_id, credentials.run_token)
    assert run["profile"] == "cc_blue"
    assert run["artifact_dir"].endswith("game-1/cc-blue/game-1-cc-blue")
    assert credentials.run_token not in (tmp_path / "registry.json").read_text()
    assert admin_token not in (tmp_path / "registry.json").read_text()


def test_registry_rejects_wrong_run_token_and_duplicate_active_player(tmp_path):
    registry = RunRegistry(tmp_path)
    registry.create_run(profile="cc_blue", server="@server", game_id="game-1")

    try:
        registry.get_run("game-1-cc-blue", "wrong")
    except RegistryError as exc:
        assert exc.code == "unauthorized"
    else:
        raise AssertionError("wrong token should be rejected")

    try:
        registry.create_run(profile="cc_blue", server="@server", game_id="game-1")
    except RegistryError as exc:
        assert exc.code == "duplicate_player_run"
    else:
        raise AssertionError("duplicate active run should be rejected")


def test_registry_rotates_run_token(tmp_path):
    registry = RunRegistry(tmp_path)
    credentials = registry.create_run(profile="cc_blue", server="@server", game_id="game-1")

    new_token = registry.rotate_run_token(credentials.run_id)

    try:
        registry.get_run(credentials.run_id, credentials.run_token)
    except RegistryError as exc:
        assert exc.code == "unauthorized"
    else:
        raise AssertionError("old token should be rejected")

    assert registry.get_run(credentials.run_id, new_token)["run_id"] == credentials.run_id
