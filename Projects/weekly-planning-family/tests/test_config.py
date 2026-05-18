import pytest
from src.config import Config, ConfigError, load_config


def test_load_valid_config(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    assert isinstance(cfg, Config)
    assert cfg.calendars.shared_general == "shared-general-id@group.calendar.google.com"
    assert cfg.calendars.shared_meals == "shared-meals-id@group.calendar.google.com"
    assert cfg.gmail.accounts[0].name == "dalton"
    assert cfg.gmail.accounts[1].name == "maggie"
    assert cfg.gmail.kid_school_label_id == "Label_1234567890123456789"
    assert cfg.todoist.projects["shopping"].name == "To buy"
    assert cfg.todoist.projects["shopping"].id == "1111"
    assert cfg.todoist.collaborator_ids["dalton"] == "9001"
    assert cfg.session.server_port == 8000
    assert cfg.session.default_day == "thursday"
    assert cfg.calendars.schools[0].name == "Elementary"
    assert cfg.family.kids[0].name == "TestKid1"
    assert cfg.family.kids[1].age == 3


def test_indexed_error_path_for_list_items(fixtures_dir, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        (fixtures_dir / "config_valid.yaml").read_text().replace(
            "    - name: TestKid2\n      age: 3",
            "    - name: TestKid2",  # age missing on kid index 1
        )
    )
    with pytest.raises(ConfigError) as exc:
        load_config(bad)
    assert "family.kids[1]" in str(exc.value)


def test_missing_calendar_raises(fixtures_dir):
    with pytest.raises(ConfigError) as exc:
        load_config(fixtures_dir / "config_missing_calendar.yaml")
    assert "shared_general" in str(exc.value)


def test_account_lookup_by_name(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    assert cfg.gmail.account_by_name("dalton").address == "dalton@example.com"
    assert cfg.gmail.account_by_name("maggie").address == "maggie@example.com"
    with pytest.raises(ConfigError):
        cfg.gmail.account_by_name("notreal")


def test_todoist_project_lookup_by_role(fixtures_dir):
    cfg = load_config(fixtures_dir / "config_valid.yaml")
    assert cfg.todoist.project_id("shopping") == "1111"
    assert cfg.todoist.project_id("meals") == "1115"
    with pytest.raises(ConfigError):
        cfg.todoist.project_id("not_a_role")
