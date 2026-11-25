"""Support code for the BoneHub Quality Check module.

Nothing in this package imports 3D Slicer, so it can be tested on its own:

- :mod:`client`       the dependency-free REST client, vendored from the server repository
- :mod:`labels`       the BoneHub label map, the origins of labels, and the colour each label
                       is drawn in
- :mod:`segmentation` writing the corrected segmentation in BoneHub's ``.seg.nrrd`` format
- :mod:`session`      the editor's session: connection, lease, downloads, verdict
"""

from .client import BoneHubQCClient, QCClientError
from .labels import ORIGIN_KINDS, LabelMap, label_color, origin_kind
from .segmentation import SEGMENTATION_SUFFIX, write_segmentation
from .session import BoneHubQCSession

__all__ = [
    "ORIGIN_KINDS",
    "SEGMENTATION_SUFFIX",
    "BoneHubQCClient",
    "BoneHubQCSession",
    "LabelMap",
    "QCClientError",
    "label_color",
    "origin_kind",
    "write_segmentation",
]
