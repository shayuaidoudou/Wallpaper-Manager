import json
from pathlib import Path

from wallpaper_manager.adapters.jetbrains import (
    IdeaAdapter,
    JetBrainsAdapter,
    PyCharmAdapter,
    decode_background_value,
    encode_background_value,
)
from wallpaper_manager.core.models import AppId


def write_fixture(path: Path) -> None:
    path.write_text(
        """<application>
  <component name="OtherComponent"><option name="keep" value="yes" /></component>
  <component name="PropertyService"><![CDATA[{
  "keyToString": {
    "unrelated": "preserve me",
    "idea.background.editor": "/old.png,20,scale,center"
  },
  "keyToStringList": {"recent": ["one", "two"]}
}]]></component>
</application>
""",
        encoding="utf-8",
    )


def read_property_service(path: Path) -> dict:
    import xml.etree.ElementTree as ET

    root = ET.parse(path).getroot()
    component = next(
        item
        for item in root.findall("component")
        if item.get("name") == "PropertyService"
    )
    return json.loads(component.text)


def test_encode_decode():
    raw = encode_background_value("/tmp/a.png", 35)
    assert raw == "/tmp/a.png,35,scale,center"
    path, ui = decode_background_value(raw)
    assert path == "/tmp/a.png"
    assert ui == 35


def test_decode_malformed_value_returns_empty_state():
    assert decode_background_value("not-a-background") == (None, 0)
    assert decode_background_value("/tmp/a.png,nope,scale,center") == (None, 0)


def test_apply_read_and_clear_preserve_json_and_xml_components(tmp_path: Path):
    other_xml = tmp_path / "other.xml"
    write_fixture(other_xml)
    adapter = JetBrainsAdapter(AppId.IDEA, other_xml=other_xml)

    assert adapter.detect() is True
    adapter.apply("/tmp/new.png", 135)
    assert adapter.read() == ("/tmp/new.png", 100)

    data = read_property_service(other_xml)
    assert data["keyToString"]["unrelated"] == "preserve me"
    assert data["keyToStringList"] == {"recent": ["one", "two"]}
    assert "OtherComponent" in other_xml.read_text(encoding="utf-8")
    assert "<![CDATA[" in other_xml.read_text(encoding="utf-8")

    adapter.clear()
    assert adapter.read() == (None, 0)
    cleared = read_property_service(other_xml)
    assert "idea.background.editor" not in cleared["keyToString"]
    assert cleared["keyToString"]["unrelated"] == "preserve me"


def test_product_factories_use_expected_ids(tmp_path: Path):
    assert IdeaAdapter(other_xml=tmp_path / "idea.xml").app_id is AppId.IDEA
    assert PyCharmAdapter(other_xml=tmp_path / "pycharm.xml").app_id is AppId.PYCHARM
