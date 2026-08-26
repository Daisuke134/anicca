import plistlib
from pathlib import Path


PLIST = Path(__file__).parent / "launchd" / "ai.anicca.capafy-loop-daily.plist"


def test_capafy_supply_owner_wakes_hourly_without_duplicate_schedule() -> None:
    config = plistlib.loads(PLIST.read_bytes())

    assert config["StartInterval"] == 3600
    assert config["ThrottleInterval"] == 60
    assert "StartCalendarInterval" not in config
    assert config["Label"] == "ai.anicca.capafy-loop-daily"
