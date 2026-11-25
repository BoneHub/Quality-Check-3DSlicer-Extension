# BoneHub Quality Check — 3D Slicer extension

Editor client for the [BoneHub quality-check server](https://github.com/BoneHub/qc-server),
the human half of a client–server setup for the quality check of the segmentations in a
database in the [BoneHub format](https://github.com/BoneHub/BoneHub-Format).

The server hands out one *scan* at a time: one image of a person and its segmentation, named
by its path in the database, such as `ds-0027/sub-000001/scan-01` (the first scan of subject 1
of dataset 27). The server runs the quality check in stages. Reviewers judge each scan first, label by
label, on the server's review page in the browser. A scan with a label they rejected or
a bone they reported missing goes to the editors, and so does a scan that has no
segmentation yet. Whether a rejected label needs correcting or should be taken out is the
editor's call. This extension is the editors'
client: it leases such a scan, loads its segmentation into 3D Slicer with every segment
named and coloured as its BoneHub label, together with its image when the server sends one,
shows why the scan came, and uploads the correction. A scan sent with its image but
no segmentation is segmented from scratch.

Nothing reaches the dataset until the server's administrator approves the scan. A
correction waits on the server: the labels it changes go back to a reviewer, unless the
server is set to take an editor's word for them, and only the administrator's approval
writes the corrected segmentation, and the origin of each label in the scan's `scan.json`,
into the dataset. An editor who
cannot correct a scan rejects it, which sends it to the administrator with a comment; the
dataset is left untouched.

The server gives each account one role or both: an **editor** corrects segmentations, here
in 3D Slicer; a **reviewer** judges them in the browser, on the server's review page. This
extension works as an editor. The key of an account that is a reviewer only is refused when
connecting, with the address of the review page to use instead; an account with both roles
can work in either.

Segmentations travel in the BoneHub format's own segmentation files, `.seg.nrrd`, which 3D
Slicer opens natively. The extension works with a quality-check server of version 1.x, which
serves version 1.x of the BoneHub format, only: it checks both when connecting, and a server
of another major version is refused with a message saying which side to update.

## Requirements

- 3D Slicer 5.6 or newer (developed and tested against 5.12)
- A server URL and an API key from your administrator, for an account with the editor role
  (whatever it is sent of each scan, see [below](#what-the-server-sends))
- A quality-check server of version 1.x (BoneHub format 1.x)

No Python packages are installed into Slicer: the client is written against the standard
library, and writing segmentations uses the numpy and SimpleITK that ship with Slicer.

## Installation

Until the extension is in the Extensions Manager, install it from source:

1. Clone this repository.
2. In Slicer, open **Edit → Application Settings → Modules**.
3. Drag the `BoneHubQualityCheck` folder into **Additional module paths**.
4. Restart Slicer. The module appears under **Segmentation → BoneHub Quality Check**.

## Correcting a scan

1. **Server** — enter the URL and your API key and press *Connect*. The key is masked; tick
   *Remember* to keep it in this computer's Slicer settings, or untick it on a shared
   machine. Connecting checks that the key is an editor's and that the server is of version
   1.x, and fetches the BoneHub label map from the server, so the extension never needs
   updating when the format gains labels. The status line also says whether the labels you
   correct go back to a reviewer, or are accepted when you tick them (see
   [below](#what-happens-to-your-correction)).
2. **Scan** — *Get next scan* leases a scan waiting for an editor and loads it into
   an empty scene: the scene is closed first, so nothing of the last scan — nor anything
   else you loaded — is left in it. The slice views are centred on the segmentation, so you
   land on the bones rather than on an empty corner of the volume. The section names the scan
   by its path and its dataset, and says [why the scan came to you](#why-a-scan-comes-to-you);
   below that it shows what the database says of the scan: its subject's `subject.json` and
   its own `scan.json`. When no scan waits for
   an editor, the extension says there is nothing to correct; try again later.
   You hold one scan at a time, until you upload, reject or release it. While you hold
   it, the same button reads *Reload scan from server*: it loads the scan again as the
   server has it, discarding the corrections you have not uploaded. When you connect, a
   scan you already hold, for instance from before restarting Slicer, is loaded again.
3. **Correction** — *Correct in Segment Editor* switches to the Segment Editor with the image
   and segmentation already selected. Use any of its tools. A segment's name is its
   label, so to fix a bone labelled on the wrong side, rename its segment (`FEMUR_LEFT` to
   `FEMUR_RIGHT`). To add a bone, pick its label in the drop-down here and press *Add
   segment*, then paint it. A bone a reviewer reported missing is picked in the drop-down
   for you, and clicking a label the segmentation lacks in the labels table picks that one.
   A scan sent without a segmentation starts empty, and every bone is added this way.
   Only names from that list exist in BoneHub; anything else is refused.
   *Show the segmentation in 3D* builds 3D models of the segmentation the server sent, one
   per label in its colour, and shows them in the 3D view, framed from the front. A layout
   without a 3D view is switched to the conventional one. The tick is remembered, so the
   scans that follow load with their models. The models follow your corrections, which
   slows the Segment Editor on a large segmentation: untick it to take them away. A scan
   sent without a segmentation has none to show; once you have painted something, the Segment
   Editor's *Show 3D* button shows it.
   *Give each bone a distinct colour* gives every segment a colour of its own. BoneHub colours
   the bones of a body region in near shades of one hue, so the two femurs or a run of
   vertebrae are hard to tell apart; here the segments are coloured in label order, which is
   anatomical, so neighbouring bones differ most. The Segment Editor's list, the slice views,
   the 3D view and the labels table all show the same colours, so a bone you spot in a view
   is found in the list by its colour. The colours never reach the server: your upload is
   written in the BoneHub colours, which are taken from each label's value, not from the
   segments. Unticking gives the segments their BoneHub colours back. A bone you add takes the
   next colour when you press *Add segment* or *Refresh*, or come back to the module from the
   Segment Editor; the others keep theirs. The tick is remembered for the scans that follow.
4. **Submit** — *Confirm and submit* uploads your correction, once you have confirmed what it
   will do; see [below](#what-happens-to-your-correction). *Reject* is for a scan you
   cannot correct — the image is unusable, say: it goes to the administrator with your
   comment, and nothing in the dataset changes. The comment is kept in the scan's history,
   where reviewers, the administrator and later editors read it.

`Refresh` re-reads the segments after an edit; returning to the module from the Segment
Editor does the same automatically.

### Why a scan comes to you

The box in the *Scan* section lists why the server handed you the scan:

- each label a reviewer rejected, and who rejected it: correct it, or delete its segment if
  the bone should not be there;
- each bone a reviewer reported missing;
- the administrator's word, when they sent the scan back to the editors;
- that the scan has no segmentation yet, when that is so.

When the segmentation you were sent is an earlier editor's correction rather than the
dataset's own, the box says whose it is: that correction waits on the server, and the dataset
keeps its own segmentation until the administrator approves the scan. Below that comes the
scan's history — every review, correction and step of the administrator so far, including
a reviewer's rejection of the scan as a whole before the administrator sent it to the
editors — with the comments.

The labels table says the same label by label, in its *Quality check* column:

| Quality check | Meaning |
| --- | --- |
| rejected (rita) | rita rejected the label: correct it, or delete its segment if the bone should not be there |
| missing (rita) | rita reported the bone missing: add it |
| accepted (rita) | rita accepted the label; it keeps that verdict unless you change it |
| to review | waits for a reviewer: nobody has reviewed it yet, or an editor corrected it |
| to review: removed by eddie | eddie took it out of the segmentation, and a reviewer has yet to agree |
| kept | not under review: reviewed on this database already, or of an origin the server does not review |
| removed | not in the segmentation, and nobody needs to look at it again |
| added | not in the segmentation you were sent: you added it |

Rejected labels are tinted red and missing ones amber; each row's tooltips say more.
*Painted* says whether your segmentation has the label, and *Origin* where the label comes
from, as the scan's `scan.json` records it today:

| Origin | Meaning |
| --- | --- |
| source | it came with the source dataset |
| manual | drawn by hand for this dataset |
| model | predicted by a model; the tooltip names it, e.g. `model:TotalSegmentator@2.4.0` |
| derived | computed from another file of the same scan; the tooltip names the tool |
| not listed | `scan.json` does not list the label, for instance a bone reported missing |

*· reviewed* follows the origin when the label has been reviewed on this database already,
on this server or another, and its segmentation is unchanged since. The BoneHub format does
not record reviews; the quality-check servers keep them. Only the administrator's approval
changes a label's origin, or makes it reviewed.

### What happens to your correction

The server compares your upload with the segmentation it replaces, voxel by voxel. What
becomes of each label then depends on the server's `edits_need_review` setting, which the
status line reports when you connect:

| Label | Corrections go back to a reviewer (the default) | The server takes an editor's word |
| --- | --- | --- |
| Changed or added by you, or rejected by a reviewer | goes back to a reviewer | accepted if you tick it, else goes back to a reviewer |
| Left as it was, and nobody has reviewed it yet | still waits for a reviewer | accepted if you tick it, else still waits for a reviewer |
| Left as it was, with a verdict | keeps its verdict | keeps its verdict, ticked or not |
| Taken out | removed once a reviewer agrees | removed |
| Reported missing, and not added | goes back to a reviewer, who sees you left it out | stays out |

The labels table has tick boxes only when the server takes an editor's word. Otherwise there
is nothing to tick, and the upload vouches for no label. Before uploading, the extension asks
you to confirm, and lists what can be told without the server's comparison: the labels you
took out, the missing bones still not there, and any segment left empty. After the upload, the status line gives the
server's word on where the scan went, with the labels it counts as changed, accepted,
taken out and waiting for a reviewer.

Whatever the setting, the correction waits on the server, and nothing reaches the dataset
before the administrator approves the scan. Approving moves the correction into the dataset
and updates the scan's `scan.json`: each label you drew or changed becomes `manual`, the
others keep their origin, and a label no longer in the segmentation is taken out. The
accepted labels become reviewed for every quality-check server on the database. The scan's
meshes and NURBS surfaces of the labels you changed are then out of date, and the
administrator is told so.

### What the server sends

The server's administrator decides, per account, whether it is sent each scan's image,
its segmentation, or both. Either one is enough to work on.

| The server sends | What happens |
| --- | --- |
| The image and the segmentation | Both are loaded. The segmentation is written back on the image's voxel grid |
| The segmentation only | The segmentation is loaded over a blank volume on its own voxel grid, which is the image's on the server, and written back on that grid. Painting, erasing, scissors, islands, smoothing, margins and the logical operators all work. Tools that follow image intensity, such as *Threshold* or *Grow from seeds*, have nothing to follow |
| The image only | The image is loaded with an empty segmentation. Add each bone's label with *Add segment* and paint it; the segmentation is written back on the image's voxel grid |

The segmentation sent is the one under review: an earlier editor's correction, when the
scan has been corrected before, or else the dataset's own.

The image only is what an account sent the image only always gets, and what any other
account gets for a scan that has no segmentation yet. The server hands an account sent
the image only nothing but such scans, as it will not let the account replace a
segmentation it has not seen. Should the server have a segmentation of a scan such an
account holds all the same, the extension warns on loading, because the upload would be
refused; reject such a scan with a comment, which sends it to the administrator.

A scan sent neither file is not loaded. The correction section stays locked and the
comment is filled in for you: reject the scan, which sends it to the administrator.
Releasing it puts it back in the queue, and you may be given it again.

Without the image there is only the segmentation's own grid to write back on. If the
server reports that the stored segmentation is not on its image's grid, the extension
warns you on loading, because the upload would be refused; reject such a scan with a
comment.

## How the segmentation survives the round trip

The scan's segmentation arrives as a BoneHub `.seg.nrrd`, which Slicer loads with one
segment per label, named after it and coloured as the format colours it. The file header
also tags each segment with its label value; the format's reader trusts that tag first,
so a segment whose tag and name disagree is renamed after its tag on loading. From then on
the segment's name is the only record of its label, and the tags are dropped so that they
cannot contradict a rename.

On submission the segments are written back in the same format, onto the image's own
voxel grid (without the image, the grid the segmentation arrived on, read from its file
header): one segment number per label, in ascending label value, as the database's own
files are numbered. A BoneHub mask holds one label per voxel, so where two segments
overlap the higher label value wins, the same way every time. The server refuses an upload
whose voxel grid does not match the image, so this is checked by the test suite rather
than left to chance; the server then keeps the upload, in canonical form, until the
administrator approves the scan.

A segment that is not named after a BoneHub label is caught before the upload, with a
message naming it, rather than being refused by the server after the wait.

## Advanced settings

| Setting | What it does |
| --- | --- |
| Working folder | Where images and segmentations are downloaded, each scan at its path in the database (`ds-0027/sub-000001/scan-01/` holding `image.nii.gz`, `segmentation.seg.nrrd` and your `corrected.seg.nrrd`). Defaults to a folder in the system temporary directory |
| Network timeout | Raise it for large images over a slow link |
| Keep downloaded files after submitting | Leaves the files in the working folder instead of deleting them |
| Get the next scan after submitting | Goes straight on to the next scan |
| Show the segmentation in 3D | Loads each scan's segmentation with its 3D models, when the server sends one. Off at first |
| Give each bone a distinct colour | Gives each scan's bones colours of their own on screen; uploads keep the BoneHub colours. Off at first |

## Layout

```
BoneHubQualityCheck/
├── BoneHubQualityCheck.py          the module: panel, scene logic and the self-test
├── BoneHubQualityCheckLib/
│   ├── client.py                   REST client, vendored from the server repository
│   ├── labels.py                   the BoneHub label map, the origins of labels, each label's colour, and the distinct colours for viewing
│   ├── segmentation.py             writing the corrected segmentation as a BoneHub .seg.nrrd
│   └── session.py                  connection, lease, downloads, verdict
└── Resources/
    ├── Icons/BoneHubQualityCheck.png
    └── UI/BoneHubQualityCheck.ui
```

Nothing in `BoneHubQualityCheckLib` imports Slicer, so the server-facing half can be run and
tested on its own. `client.py` is a verbatim copy of the server's
[`qc_server/client.py`](https://github.com/BoneHub/qc-server/blob/main/qc_server/client.py);
change it there and copy it across, so both sides stay on one definition of the API.

## Tests

There are two suites, both registered as ctest targets when the extension is built.

| Suite | What it covers |
| --- | --- |
| `BoneHubQualityCheck.py` | The label colours, and the label map with the origins of labels; that an account can connect whatever it is sent of each scan, and that only a server of version 1.x, serving version 1.x of the BoneHub format, is accepted; that a scan's files are kept at its path in the database and cleaned up with the folders left empty above them, and that a key leading out of the working folder is refused; how the quality check of a scan is put into words — each label's state and origin, the history, the requests, whose correction the segmentation is, what the database says of the scan, and the server's word on an upload; and the round trip of a BoneHub `.seg.nrrd` through the scene: that labels, voxels and the voxel grid come back unchanged (on an oblique image), that renaming a segment relabels it, that a missing bone can be added, that a segmentation edited without its image is written back on the image's grid, that a scan sent without its segmentation is painted from scratch and written back on the image's grid, that the segmentation sent gets a 3D model per label which changes no voxel of the upload, and one painted from scratch none, that the bones can be given distinct colours, neighbours far apart and a bone added in the next colour, which the Segment Editor lists and the views draw alike, while the upload is written in BoneHub colours and unticking gives each segment its BoneHub colour back, that a scan sent neither file is not loaded, that every scan starts from an empty scene, and that a segment which is not a BoneHub label is refused |
| `Testing/Python/BoneHubQualityCheckModuleTest.py` | The panel: that the `.ui` file still carries every widget the code uses, that the sections stay locked until there is something to do, that the scan button leases the next scan or, holding one, reloads it after asking, or says the lease has ended, and that connecting loads a scan already held but leaves one already loaded alone, that the key stays masked, that the editor sees the scan and why it came to them — its path and dataset, what the database says of it, the labels rejected and missing, which stand out, each label's origin, the administrator's requests, the history with its comments, and an earlier editor's correction — that a missing bone is picked for *Add segment*, that a scan without a segmentation opens for painting from scratch (with a warning for an account sent images only when the server has a segmentation it was not sent), that a scan sent neither file can only be rejected, that the Segment Editor can edit a scan without its image, that *Show the segmentation in 3D* builds and takes away the models of the segmentation sent, and is locked for one painted from scratch, that *Give each bone a distinct colour* recolours the bones and back, in the Segment Editor's list, the views and the labels table alike, and colours a scan loaded while it is on and a bone added, that tick boxes appear only when the server takes an editor's word and behave across a refresh, what confirming asks, sends and reports under either setting, that rejecting sends the scan to the administrator, and that an empty queue speaks of correcting |

The first also runs from **Reload and Test** in the module's *Advanced* section. Running
either against a source checkout, with `MODULE` standing for the path to the
`BoneHubQualityCheck` folder:

```bash
# the logic, no window needed
Slicer --no-main-window --testing --additional-module-paths "$MODULE" \
       --python-code "import BoneHubQualityCheck as m; m.BoneHubQualityCheckTest().runTest()"

# the panel, which needs a main window. Its folder goes on sys.path, not on the module
# path: it is a test, not a module for Slicer to load.
Slicer --testing --additional-module-paths "$MODULE" \
       --python-code "import sys; sys.path.append(r'$MODULE/Testing/Python'); \
                      import BoneHubQualityCheckModuleTest as t; t.BoneHubQualityCheckModuleTest().runTest()"
```

The round-trip test is the one that matters most: the server refuses an upload whose voxel
grid does not match the image, and a segmentation written back with the wrong label values
would corrupt the dataset silently once approved.

## License

See [LICENSE](LICENSE).
