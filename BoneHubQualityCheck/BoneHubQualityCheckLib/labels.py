"""The BoneHub label map as the client sees it, the origins of labels, the colour each label is
drawn in, and the colours that tell a scan's bones apart on screen.

The label map itself is never hard-coded here: it is fetched from the server's
``/api/v1/labels`` endpoint, so a database that gains labels does not need a new release of
the extension. This module only wraps that payload and decides how a label is shown.

Label values follow version 1 of the BoneHub format: nine digits built from a bone's
structure, part, tissue and side (see ``bonehub_format/labelmap.py``). Each label of a scan's
segmentation has an origin in its ``scan.json``: ``source``, ``manual``,
``model:<name>@<version>`` or ``derived:<tool>@<version>`` (see :data:`ORIGIN_KINDS`). When
its administrator approves a scan, the server records each label an editor drew as ``manual``.
"""

from __future__ import annotations

import colorsys

#: The version of the BoneHub format this extension is written for, as major.minor. The
#: segmentation files and the origins of labels are those of this version; a minor version of
#: the format only adds to them.
SCHEMA_VERSION = "1.0"

#: The kinds of origin a label has in ``scan.json``. Served by the server as well; this copy is
#: the fallback for a kind the server did not describe.
ORIGIN_KINDS: dict[str, str] = {
    "source": "came with the source dataset",
    "manual": "drawn by hand for this dataset",
    "model": "predicted by a model (model:<name>@<version>)",
    "derived": "computed from another file of the same scan (derived:<tool>@<version>)",
}


def origin_kind(origin) -> str:
    """The kind of an origin: ``source``, ``manual``, ``model`` or ``derived``.

    The module's panel is a narrow dock, so a table cell has room for the kind, not for
    ``model:TotalSegmentator@2.4.0``; the whole origin goes in the tooltip.
    """
    return str(origin or "").split(":", 1)[0]


def label_color(value: int) -> tuple[float, float, float]:
    """The RGB colour in 0..1 that BoneHub's segmentation files give a label value.

    A copy of ``_segment_color`` in ``bonehub_format/segmentation_file.py``: the hue comes
    from the body region and the shade from the finer fields. A segment loaded from a
    database file already carries this colour in the file header; drawing the segments
    added here the same way keeps a bone one colour however it reached the scene.
    """
    value = int(value)
    region = value // 100_000_000
    structure = value // 100_000
    tissue = (value // 10) % 100
    hue = ((region / 10.0) + (structure % 100) * 0.013) % 1.0
    saturation = 0.45 + ((structure // 100) % 5) * 0.09
    lightness = min(0.42 + tissue * 0.09, 0.78)
    return colorsys.hls_to_rgb(hue, lightness, saturation)


#: The golden ratio's fractional part. Hues stepped round the colour wheel by it each land far
#: from the ones just before them, however many follow.
_GOLDEN_STEP = 0.6180339887498949


def distinct_color(index: int) -> tuple[float, float, float]:
    """An RGB colour in 0..1 for the ``index``-th bone of a scan, far from the bones next to it.

    For finding a bone on screen only: an upload is always written in :func:`label_color`'s
    colours, whatever colour its segments have. :func:`label_color` takes its hue from the body
    region, so the bones of one region -- the two femurs, a run of vertebrae -- come out in near
    shades of one hue. Here the hue steps round the wheel by the golden ratio and the lightness
    takes turns, so that bones one after the other in label order, which are anatomical
    neighbours, stand apart.
    """
    index = int(index)
    hue = (index * _GOLDEN_STEP) % 1.0
    lightness = (0.52, 0.7, 0.38)[index % 3]
    return colorsys.hls_to_rgb(hue, lightness, 0.85)


def schema_is_supported(version) -> bool:
    """True if a server serves a version of the BoneHub format with the major version this
    extension is written for. A minor version only adds to the format, so its segmentation
    files and origins are those this extension reads."""
    return isinstance(version, str) and version.split(".")[0] == SCHEMA_VERSION.split(".")[0]


class LabelMap:
    """The BoneHub label names and their values, and the kinds of origin of a label, as served
    by ``/api/v1/labels``."""

    def __init__(self, name_to_value: dict | None = None, origins: dict | None = None):
        # Background is never a segment, so it is left out even if a server sends it.
        self.name_to_value: dict[str, int] = {
            str(k): int(v) for k, v in (name_to_value or {}).items() if int(v) != 0
        }
        self.value_to_name: dict[int, str] = {v: k for k, v in self.name_to_value.items()}
        self.origins: dict[str, str] = dict(ORIGIN_KINDS)
        self.origins.update({str(kind): str(text) for kind, text in (origins or {}).items()})

    @classmethod
    def from_payload(cls, payload: dict) -> "LabelMap":
        """Build from the body of ``GET /api/v1/labels``."""
        payload = payload or {}
        return cls(payload.get("label_name_to_value"), payload.get("label_origins"))

    def __bool__(self) -> bool:
        return bool(self.name_to_value)

    def __len__(self) -> int:
        return len(self.name_to_value)

    def value_of(self, name: str):
        """The BoneLabelMap value of a label name, or None when the name is not a BoneHub label."""
        return self.name_to_value.get(name)

    def name_of(self, value: int):
        """The label name of a BoneLabelMap value, or None when the value is not a BoneHub label."""
        try:
            return self.value_to_name.get(int(value))
        except (TypeError, ValueError):
            return None

    def sorted_names(self) -> list:
        """Every label name, ordered by value, which is anatomical order."""
        return [name for name, _ in sorted(self.name_to_value.items(), key=lambda item: item[1])]

    def describe_origin(self, origin) -> str:
        """An origin with the server's wording for its kind, for a tooltip:
        ``model:TotalSegmentator@2.4.0: predicted by a model (model:<name>@<version>)``."""
        meaning = self.origins.get(origin_kind(origin))
        return f"{origin}: {meaning}" if meaning else str(origin)

    def color_of(self, name: str) -> tuple[float, float, float]:
        value = self.name_to_value.get(name)
        return label_color(value) if value is not None else (0.5, 0.5, 0.5)
