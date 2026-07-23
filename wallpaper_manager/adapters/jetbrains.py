from __future__ import annotations

import json
from pathlib import Path
from xml.dom import Node, minidom

from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.opacity import clamp_ui
from wallpaper_manager.detect.paths import find_jetbrains_other_xml

BACKGROUND_KEY = "idea.background.editor"


def encode_background_value(path: str, opacity_ui: int) -> str:
    return f"{path},{clamp_ui(opacity_ui)},scale,center"


def decode_background_value(value: str) -> tuple[str | None, int]:
    parts = value.rsplit(",", 3)
    if len(parts) != 4 or parts[2:] != ["scale", "center"]:
        return None, 0
    try:
        opacity = clamp_ui(int(parts[1]))
    except (TypeError, ValueError):
        return None, 0
    return parts[0], opacity


class JetBrainsAdapter:
    def __init__(
        self,
        app_id: AppId,
        other_xml: Path | None = None,
        product_prefix: str | None = None,
    ):
        self.app_id = app_id
        self.product_prefix = product_prefix or self._default_prefix(app_id)
        self.other_xml = (
            other_xml
            if other_xml is not None
            else find_jetbrains_other_xml(self.product_prefix)
        )

    @staticmethod
    def _default_prefix(app_id: AppId) -> str:
        if app_id is AppId.IDEA:
            return "IntelliJIdea"
        if app_id is AppId.PYCHARM:
            return "PyCharm"
        raise ValueError(f"Unsupported JetBrains app: {app_id}")

    def detect(self) -> bool:
        return self.other_xml is not None and self.other_xml.is_file()

    def read(self) -> tuple[str | None, int]:
        data = self._read_data()
        value = data.get("keyToString", {}).get(BACKGROUND_KEY)
        if not isinstance(value, str):
            return None, 0
        return decode_background_value(value)

    def apply(self, image_path: str, opacity_ui: int) -> None:
        def set_background(data: dict) -> None:
            data.setdefault("keyToString", {})[BACKGROUND_KEY] = encode_background_value(
                image_path, opacity_ui
            )

        self._mutate(set_background)

    def clear(self) -> None:
        if not self.detect():
            return

        def remove(data: dict) -> None:
            key_to_string = data.get("keyToString")
            if isinstance(key_to_string, dict):
                key_to_string.pop(BACKGROUND_KEY, None)

        self._mutate(remove)

    def _read_data(self) -> dict:
        if not self.detect():
            return {}
        try:
            doc = minidom.parse(str(self.other_xml))
            component = self._property_service(doc)
            if component is None:
                return {}
            raw = "".join(
                node.data
                for node in component.childNodes
                if node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE)
            )
            data = json.loads(raw)
        except (OSError, ValueError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _mutate(self, mutation) -> None:
        if self.other_xml is None:
            raise FileNotFoundError("JetBrains other.xml was not found")
        self.other_xml.parent.mkdir(parents=True, exist_ok=True)
        if self.other_xml.is_file():
            doc = minidom.parse(str(self.other_xml))
        else:
            doc = minidom.Document()
            doc.appendChild(doc.createElement("application"))
        component = self._property_service(doc)
        if component is None:
            component = doc.createElement("component")
            component.setAttribute("name", "PropertyService")
            doc.documentElement.appendChild(component)
            data: dict = {}
        else:
            raw = "".join(
                node.data
                for node in component.childNodes
                if node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE)
            )
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("JetBrains PropertyService JSON is invalid") from exc
            data = parsed if isinstance(parsed, dict) else {}
        mutation(data)
        serialized = json.dumps(data, indent=2, ensure_ascii=False)
        cdata = next(
            (
                node
                for node in component.childNodes
                if node.nodeType == Node.CDATA_SECTION_NODE
            ),
            None,
        )
        if cdata is None:
            component.appendChild(doc.createCDATASection(serialized))
        else:
            cdata.data = serialized
        self.other_xml.write_text(doc.toxml(), encoding="utf-8")

    @staticmethod
    def _property_service(doc: minidom.Document):
        for component in doc.getElementsByTagName("component"):
            if component.getAttribute("name") == "PropertyService":
                return component
        return None


def IdeaAdapter(
    other_xml: Path | None = None, product_prefix: str | None = None
) -> JetBrainsAdapter:
    return JetBrainsAdapter(AppId.IDEA, other_xml, product_prefix)


def PyCharmAdapter(
    other_xml: Path | None = None, product_prefix: str | None = None
) -> JetBrainsAdapter:
    return JetBrainsAdapter(AppId.PYCHARM, other_xml, product_prefix)
