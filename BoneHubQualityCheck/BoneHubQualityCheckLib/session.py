"""The editor's session with the quality-check server: connection, lease, files, verdict.

Everything here is plain Python with no 3D Slicer imports, so it can be exercised outside
the application. The scene side of a review -- volumes, segmentations, the segment editor
-- lives in the module's logic class instead.

The extension works in the editor role: it corrects segmentations and uploads them. The
server refuses the key of an account that is not an editor, and tells a reviewer to use the
server's review page instead. Whatever the account is sent of each scan -- the image, the
segmentation, or both -- is enough to work on.

Reviewers judge each scan first. An editor is handed the scans a reviewer sent back --
a label rejected, or a bone reported missing -- and those without any segmentation. The
upload waits on the server: the labels it corrects go back to a reviewer, or are accepted on
the editor's word when the server takes it (``edits_need_review`` off), and nothing reaches
the dataset before the server's administrator approves the scan.

A session owns one working folder per assignment, at the scan's path in the database, and
names the files in it as the database does::

    <workspace>/<scan_key>/       e.g. <workspace>/ds-0027/sub-000001/scan-01/
        segmentation.seg.nrrd     the segmentation under review, if the server sends it
        image.nii.gz              the image, if the server sends it
        corrected.seg.nrrd        what the editor sends back
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path, PurePosixPath

from .client import EDITOR, BoneHubQCClient, QCClientError
from .labels import SCHEMA_VERSION, LabelMap, schema_is_supported
from .segmentation import SEGMENTATION_SUFFIX

#: Downloads and the upload share one timeout; a whole-body CT over a slow link is slow.
DEFAULT_TIMEOUT = 300

#: The quality-check server this extension is written for: its major version, which is that of
#: the BoneHub format it serves. A server of version 1.x hands out scans through the API this
#: extension speaks.
SERVER_VERSION = "1"

#: The working folder for a scan the server has not named.
UNASSIGNED_FOLDER = "unassigned"


def server_is_supported(version) -> bool:
    """True if a server's version has the major version this extension is written for."""
    return isinstance(version, str) and version.split(".")[0] == SERVER_VERSION


class BoneHubQCSession:
    """One editor, one server, at most one scan in hand at a time."""

    def __init__(self, workspace: Path | None = None, timeout: int = DEFAULT_TIMEOUT):
        self.workspace = Path(workspace) if workspace else Path(tempfile.gettempdir()) / "BoneHubQualityCheck"
        self.timeout = timeout

        self.client: BoneHubQCClient | None = None
        self.server_info: dict = {}
        self.labels = LabelMap()
        self.handout: dict = {}
        self.image_path: Path | None = None
        self.segmentation_path: Path | None = None
        #: Working folder of the scan that was submitted or released last, kept so its
        #: downloads can still be cleaned up after the lease is gone.
        self.finished_folder: Path | None = None

    # ------------------------------------------------------------- connection
    @property
    def connected(self) -> bool:
        return self.client is not None and bool(self.server_info)

    @property
    def user_name(self) -> str:
        return self.server_info.get("user", "")

    @property
    def edits_need_review(self) -> bool:
        """Whether the labels an editor corrects go back to a reviewer, as the server said on
        connecting. When they do not, the corrected labels the editor vouches for are accepted.
        The safe answer, True, until the server says otherwise."""
        return bool(self.server_info.get("edits_need_review", True))

    def connect(self, base_url: str, api_key: str) -> dict:
        """Check the server, the key and its editor role, and the BoneHub format; fetch the label map.

        Raises ``QCClientError`` when the server is unreachable, the key is refused -- also
        when its account is not an editor, with the server's word on where to go instead --
        or the server is of another major version, or serves another major version of the
        BoneHub format. What the account is sent of each scan does not matter: an editor sent the
        image only segments from scratch. A connection that was already working is left in
        place, so a failed reconnect never strands an editor holding a scan they can no
        longer submit.
        """
        base_url = (base_url or "").strip()
        api_key = (api_key or "").strip()
        if not base_url:
            raise QCClientError("Enter the server URL, for example http://localhost:8000.")
        if not api_key:
            raise QCClientError("Enter the API key your administrator gave you.")

        client = BoneHubQCClient(base_url, api_key, timeout=self.timeout, role=EDITOR)
        info = client.ping()
        server = info.get("server_version")
        if not server_is_supported(server):
            raise QCClientError(
                f"The quality-check server is version {server or 'unknown'}, but this extension is written for "
                f"version {SERVER_VERSION}.x, which hands out the scans of a database in the BoneHub format "
                f"{SCHEMA_VERSION}. Update whichever of the two is older."
            )
        version = info.get("schema_version")
        if not schema_is_supported(version):
            raise QCClientError(
                f"The server serves version {version or 'unknown'} of the BoneHub format, but this extension is "
                f"written for version {SCHEMA_VERSION.split('.')[0]}.x, whose segmentations are "
                f"{SEGMENTATION_SUFFIX} files. Update whichever of the two is older."
            )
        # Every segment is checked against the label map, so a server that cannot send it
        # leaves nothing to review with.
        labels = LabelMap.from_payload(client.labels())
        if not labels:
            raise QCClientError("The server sent an empty BoneHub label map.")

        self.client = client
        self.server_info = info
        self.labels = labels
        return info

    def disconnect(self) -> None:
        self.client = None
        self.server_info = {}
        self.labels = LabelMap()
        self.clear_scan()

    def _require_client(self) -> BoneHubQCClient:
        if self.client is None:
            raise QCClientError("Connect to the server first.")
        return self.client

    # --------------------------------------------------------------- scans
    @property
    def has_scan(self) -> bool:
        return bool(self.handout)

    @property
    def assignment_id(self) -> str:
        return self.handout.get("assignment_id", "")

    @property
    def scan_key(self) -> str:
        return self.handout.get("scan_key", "")

    def clear_scan(self) -> None:
        self.handout = {}
        self.image_path = None
        self.segmentation_path = None

    def next_scan(self) -> dict:
        """Lease the next scan waiting for an editor and remember the handout. Raises 404
        when no scan waits for one."""
        self.clear_scan()
        self.handout = self._require_client().next_scan()
        return self.handout

    def open_assignments(self) -> list:
        """The scans this user holds as an editor; those they hold as a reviewer are not listed."""
        return self._require_client().my_assignments()

    def reload_assignment(self, assignment_id: str) -> dict:
        """Fetch the handout of a scan this editor already holds."""
        self.clear_scan()
        self.handout = self._require_client().assignment(assignment_id)
        return self.handout

    def extend_lease(self) -> dict:
        assignment = self._require_client().extend(self._require_assignment())
        self.handout["expires_at"] = assignment.get("expires_at", self.handout.get("expires_at"))
        return assignment

    def release_scan(self) -> dict:
        assignment = self._require_client().release(self._require_assignment())
        self.finished_folder = self.folder_of(self.scan_key) if self.scan_key else None
        self.clear_scan()
        return assignment

    def _require_assignment(self) -> str:
        if not self.handout:
            raise QCClientError("No scan is in hand. Ask for the next scan first.")
        return self.handout["assignment_id"]

    # ------------------------------------------------------------------ files
    def folder_of(self, scan_key: str) -> Path:
        """The working folder of a scan: its path in the database, under the workspace.

        The folder is deleted once the scan is done with, so a key that would lead out of the
        workspace is refused rather than followed.
        """
        parts = PurePosixPath(scan_key).parts
        if not parts or any(part in ("/", ".", "..") or "\\" in part or ":" in part for part in parts):
            raise QCClientError(f"The server named a scan '{scan_key}', which is not a path in a database.")
        return self.workspace.joinpath(*parts)

    def scan_folder(self) -> Path:
        folder = self.folder_of(self.scan_key or UNASSIGNED_FOLDER)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def corrected_path(self) -> Path:
        return self.scan_folder() / f"corrected{SEGMENTATION_SUFFIX}"

    def download_image(self) -> Path:
        """Download the image. Only call it when the handout says ``has_image``."""
        destination = self.scan_folder() / "image.nii.gz"
        self.image_path = self._require_client().download_image(self._require_assignment(), destination)
        return self.image_path

    def download_segmentation(self):
        """Download the segmentation under review -- an earlier editor's correction waiting on
        the server, or the dataset's own -- or return None when none is sent."""
        if not self.handout.get("has_segmentation"):
            self.segmentation_path = None
            return None
        destination = self.scan_folder() / f"segmentation{SEGMENTATION_SUFFIX}"
        self.segmentation_path = self._require_client().download_segmentation(self._require_assignment(), destination)
        return self.segmentation_path

    def discard_files(self, folder: Path | None = None) -> None:
        """Remove a scan's working folder, and its subject's and dataset's folders once no other
        scan is left in them. Safe to call when it was never created.

        Defaults to the scan in hand; pass ``finished_folder`` to clean up after a
        submission, which has already let go of the scan.
        """
        folder = folder or (self.folder_of(self.scan_key) if self.scan_key else None)
        if folder is None:
            return
        shutil.rmtree(folder, ignore_errors=True)
        try:
            above = folder.relative_to(self.workspace).parents  # sub-000001, then ds-0027, then the workspace
        except ValueError:  # the workspace was changed since: leave its folders alone
            return
        for parent in list(above)[:-1]:
            try:
                (self.workspace / parent).rmdir()
            except OSError:  # not empty, or gone already
                break

    # ----------------------------------------------------------- the verdict
    def submit(
        self,
        quality_check_confirmed: bool,
        segmentation_path: Path | None = None,
        confirmed_labels: list | None = None,
        comment: str | None = None,
    ) -> dict:
        """Send the verdict and let go of the scan.

        Confirmed, the corrected segmentation is uploaded, vouching for ``confirmed_labels``;
        rejected, the scan goes to the administrator with the comment. Either waits on the
        server: nothing reaches the dataset before the administrator approves the scan.
        The lease is only cleared when the server accepted the submission, so a refused
        upload leaves the editor holding the scan and able to try again.
        """
        result = self._require_client().submit(
            self._require_assignment(),
            quality_check_confirmed=quality_check_confirmed,
            segmentation_path=segmentation_path,
            confirmed_labels=confirmed_labels,
            comment=(comment or None),
        )
        self.finished_folder = self.folder_of(self.scan_key) if self.scan_key else None
        self.clear_scan()
        return result
