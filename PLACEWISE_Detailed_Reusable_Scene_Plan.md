# PLACEWISE --- Detailed Reusable Scene and Furniture Arrangement Plan

## 1. Product objective

PLACEWISE lets a user upload a photograph, speak naturally in
Tanglish/Tamil/English about what should stay or go, and receive: 1. An
edited/rearranged version of the original photograph. 2. An annotated
arrangement plan showing object identities, proposed positions and
movements.

**Core cost-saving principle:** use AI and computer vision to prepare a
reusable scene once. After that, perform object removal, movement,
scaling, rotation, layout changes, undo/redo and rendering locally. Do
not call a paid image-generation API every time the user changes an
object's position.

There are two phases: - **Scene preparation:** detection, segmentation,
cutout extraction and background reconstruction. - **Arrangement
interaction:** inexpensive local operations on reusable assets and scene
metadata.

## 2. Product principles and MVP scope

### User experience principles

-   The photograph is the main interface; voice is the primary input.
-   The user may list only objects to remove, only objects to keep, or
    both.
-   Unmentioned objects are kept by default unless the user specifies
    otherwise.
-   Ambiguous references must be resolved by asking the user to tap an
    object.
-   Users can correct detection errors.
-   The final image and arrangement plan must come from the same scene
    state.
-   Keep the original photograph untouched and recoverable.
-   The edited result is a visualization, not a guarantee of physically
    measured clearance.

### Supported objects

Furniture: sofa, chair, table, bed, cupboard, shelf and desk.
Appliances: television, refrigerator, washing machine and fan. Household
objects: lamp, plant, basket, boxes and selected clutter.

Prioritize reliable support for a smaller set of common objects rather
than claiming universal recognition.

### Build in the MVP

-   Photo upload and preview.
-   Tanglish voice recording and transcription using Gnani Prisma.
-   Object detection and segmentation.
-   Object labels and user corrections.
-   Keep/remove instruction interpretation.
-   Reusable object cutouts and cleaned background.
-   Local drag, move, scale, rotate and hide operations.
-   Basic rule-based arrangement.
-   Final image and annotated-plan rendering.
-   Undo, redo, reset and download.

Postpone full 3D reconstruction, exact room measurement, AR placement,
shopping integration and repeated generative editing for every
interaction.

## 3. End-to-end workflow

### Phase A --- Upload and prepare the room

**Step 1: Upload a photograph**

Accept JPEG, PNG and WebP. Validate file size and dimensions, preserve
the original, correct EXIF orientation, create a working copy and assign
a room/session ID.

Suggested endpoint: `POST /api/rooms`

Example response:

``` json
{
  "room_id": "room_001",
  "status": "uploaded",
  "image_width": 1920,
  "image_height": 1080
}
```

**Step 2: Detect objects**

Run a local detector such as YOLO. Store a unique ID, class, confidence
and bounding box for every instance. Multiple chairs must have different
IDs.

Example:

``` json
{
  "object_id": "chair_02",
  "class": "chair",
  "confidence": 0.94,
  "bbox": [420, 280, 610, 590]
}
```

These values are illustrative. Do not assume every detection is correct.

**Step 3: Generate object masks**

Use SAM 2 or a compatible segmentation model to create pixel-level
masks. A bounding box identifies an approximate region; a segmentation
mask identifies the object's pixels.

Save the original crop, transparent cutout, binary/alpha mask and object
metadata.

``` text
room_001/
  original.jpg
  objects/
    sofa_01.png
    chair_01.png
    chair_02.png
  masks/
    sofa_01.png
    chair_01.png
    chair_02.png
```

**Step 4: Let the user verify detections**

Show selectable outlines and labels over the photo. Allow the user to
tap an object, rename it, add a missed object, remove a false detection
or distinguish similar objects.

### Phase B --- Understand the voice instruction

**Step 5: Transcribe speech**

Use Gnani Prisma v2.5 for speech-to-text. Show the transcript and allow
the user to correct it before execution.

Example:

> "Sofa-vum TV-vum bookshelf-um venum. Rendu chairs-um coffee table-um
> vendaam. Remaining things neat-ah arrange pannunga."

**Step 6: Parse the transcript into structured intent**

Extract objects to keep, remove, move or fix; relative placement
requests; and whether clarification is needed.

``` json
{
  "mode": "KEEP_AND_REMOVE",
  "keep": ["sofa", "tv", "bookshelf"],
  "remove": ["chair", "coffee_table"],
  "rearrange_remaining": true,
  "unmentioned_objects": "KEEP",
  "clarification_required": false
}
```

The parser should produce structured actions, not edit pixels.

**Step 7: Resolve words to detected object IDs**

Rules: - "Rendu chairs vendaam" maps to both chair instances if there
are exactly two. - "Andha chair vendaam" is ambiguous if multiple chairs
exist; ask the user to tap one. - "Sofa venum" maps to the sofa
detection. - "TV pakkathula table vaiyunga" creates a relative placement
request.

  -----------------------------------------------------------------------
  Instruction                         System behavior
  ----------------------------------- -----------------------------------
  Only removal list                   Remove listed objects; keep
                                      unmentioned objects

  Only keep list                      Keep listed objects; do not remove
                                      unmentioned objects

  Keep and remove                     Apply both lists

  Arrange everything                  Keep all objects and propose a
                                      layout

  Ambiguous reference                 Ask user to select the object

  Conflicting actions                 Ask which action takes priority

  Object not detected                 Ask user to identify it or correct
                                      detection
  -----------------------------------------------------------------------

Never silently remove an object because it was not mentioned.

### Phase C --- Create a reusable scene

**Step 8: Build the clean background once**

Create a combined mask for objects that may be moved or removed. Use the
combined mask with a local inpainting model such as LaMa to reconstruct
the background. Save it as `clean_background.png`.

Why mask all movable objects? If a sofa remains baked into the
background and is later moved, the original sofa will appear as a ghost.
A clean background lets the renderer composite retained objects at new
positions.

Important: - Include all pixels belonging to movable objects. - Expand
masks slightly if needed to avoid edge halos. - Do not mask fixed
structures such as walls, windows and doors. - Inspect the inpainted
background. - Keep the original photograph untouched. - Large occluded
regions may be reconstructed imperfectly.

For the MVP, fixed objects can remain part of the background if they are
not offered as movable layers.

**Step 9: Save the scene manifest**

The scene manifest is the source of truth for both outputs.

``` json
{
  "scene_id": "room_001",
  "original_image": "original.jpg",
  "clean_background": "clean_background.png",
  "canvas": {
    "width": 1920,
    "height": 1080
  },
  "objects": [
    {
      "id": "sofa_01",
      "name": "Sofa",
      "category": "furniture",
      "image": "objects/sofa_01.png",
      "mask": "masks/sofa_01.png",
      "original_position": {"x": 180, "y": 310},
      "position": {"x": 180, "y": 310},
      "width": 420,
      "height": 220,
      "scale": 1.0,
      "rotation": 0,
      "visible": true,
      "action": "KEEP",
      "fixed": false,
      "z_index": 3
    }
  ]
}
```

In production, also store anchor point, confidence, mask dimensions,
floor-contact point and optional depth/order information.

## 4. Local arrangement engine

Once the scene is prepared, object operations are metadata changes:

  User action            Scene update
  ---------------------- ------------------------------------------
  Remove chair           `visible = false`
  Move sofa left         Decrease sofa `x` coordinate
  Move table near sofa   Calculate a destination relative to sofa
  Rotate chair           Update `rotation`
  Resize object          Update `scale`
  Keep bookshelf fixed   Set `fixed = true`
  Restore original       Restore original scene state

No image-generation call is needed.

### Use React Konva for the editor

React Konva supports independent image nodes, drag-and-drop, scaling,
rotation, selection outlines, layer ordering and canvas export.

Documentation: https://konvajs.org/docs/react/

Suggested canvas:

``` text
ArrangementCanvas
├── BackgroundLayer
│   └── clean_background.png
├── ShadowLayer
├── FurnitureLayer
│   ├── sofa_01
│   ├── bookshelf_01
│   └── table_01
├── HouseholdObjectsLayer
│   ├── plant_01
│   └── lamp_01
└── AnnotationLayer
    ├── labels
    ├── movement arrows
    └── destination outlines
```

### Coordinate model

Use one coordinate system based on the original image dimensions: - `x`,
`y`: top-left or chosen anchor coordinate. - `width`, `height`: rendered
dimensions. - `scale`: scale multiplier. - `rotation`: angle in
degrees. - `z_index`: compositing order. - `visible`: whether the object
is shown. - `fixed`: whether automatic layout may move it.

Store coordinates consistently and convert to browser canvas coordinates
only for display.

### Basic arrangement rules

Start with deterministic rules: - Keep fixed objects unchanged. - Place
small tables near sofas when requested. - Orient televisions toward
seating only when the image provides enough evidence. - Avoid object
bounding-box overlap. - Keep objects within the estimated visible room
region. - Avoid known doors and walkways. - Prefer small movements over
large movements when the user gives no specific direction. - Preserve
original object scale unless requested otherwise.

Use Shapely for overlap checks. Add OR-Tools only if rule-based
placement becomes insufficient.

A 2D photograph is not true room geometry. Perspective affects apparent
size and distance. Present the layout as an approximate visual
suggestion, not a physically verified floor plan.

## 5. Rendering without repeated AI generation

### Render pipeline

1.  Load the clean background.
2.  Read the current scene manifest.
3.  Select objects where `visible = true`.
4.  Sort objects by `z_index`.
5.  Apply position, scale and rotation to each transparent object.
6.  Composite objects over the background.
7.  Add shadows where feasible.
8.  Export the final image.
9.  Render annotations from the same scene state.

Use Pillow/OpenCV on the backend for final export. React Konva can
provide instant browser previews.

### Shadows and blending

Simple compositing can look like stickers. Improve it with: - Soft
contact shadows below furniture. - Careful edge feathering. - Correct
z-ordering. - Color/brightness matching only when necessary. -
Perspective-aware scale where enough visual information exists.

For the MVP, prioritize clean masks and sensible placement over advanced
lighting reconstruction.

### Prevent ghost objects

-   Create the clean background with all movable-object masks.
-   Composite retained objects back into the scene.
-   Do not use the original photograph as the base for every
    rearrangement.
-   Keep fixed room structures in the background.

If a fixed object cannot be separated from the room cleanly, treat it as
background and do not offer it as a movable layer.

### Annotated arrangement plan

Use the exact same object positions as the final image.

Suggested conventions: - Green outline: retained object. - Red/grey
marker: removed object. - Dashed outline: proposed destination. - Arrow:
movement direction. - Label: object name and ID.

The plan is an overlay, not a second independently generated layout.

## 6. Multiple layouts, undo and redo

Store the reusable assets and layout snapshots:

``` text
room_001/
├── original.jpg
├── clean_background.png
├── scene.json
├── objects/
│   ├── sofa_01.png
│   ├── chair_01.png
│   ├── chair_02.png
│   └── table_01.png
├── masks/
│   ├── sofa_01.png
│   ├── chair_01.png
│   ├── chair_02.png
│   └── table_01.png
└── layouts/
    ├── layout_01.json
    ├── layout_02.json
    └── layout_03.json
```

Each layout stores object visibility, positions, scale, rotation and
z-order.

Implement: - Undo: restore previous scene state. - Redo: reapply next
state. - Reset: restore original positions and visibility. - Save
layout: create a named snapshot. - Duplicate layout: experiment on a
copy.

None of these operations requires an image-generation call.

## 7. Tanglish command execution

Example:

> "Sofa konjam left move pannunga. Rendu chairs remove pannunga. Table-a
> sofa pakkathula vaiyunga."

Prisma transcribes the instruction. The parser resolves object
references and generates operations:

``` json
{
  "operations": [
    {"object_id": "sofa_01", "action": "MOVE", "dx": -40, "dy": 0},
    {"object_id": "chair_01", "action": "REMOVE"},
    {"object_id": "chair_02", "action": "REMOVE"},
    {"object_id": "table_01", "action": "MOVE_NEAR", "target_id": "sofa_01"}
  ]
}
```

These values are illustrative. Actual movement should be calculated from
image dimensions, object footprints and constraints.

Internal operation vocabulary: - `KEEP` - `REMOVE` - `MOVE` -
`MOVE_NEAR` - `MOVE_LEFT` - `MOVE_RIGHT` - `MOVE_FORWARD` -
`MOVE_BACK` - `ROTATE` - `RESIZE` - `FIX` - `ARRANGE`

The user does not need to speak these exact terms. The parser maps
natural speech into them.

Before applying an operation: 1. Resolve object references to IDs. 2.
Check that the operation is supported. 3. Check whether the object is
fixed. 4. Calculate the proposed position. 5. Run collision and boundary
checks. 6. Ask for clarification if ambiguous. 7. Apply the operation
and update scene state. 8. Render the preview locally.

## 8. Recommended technology stack

  -----------------------------------------------------------------------
  Component               Technology              Role
  ----------------------- ----------------------- -----------------------
  Frontend                React + TypeScript      Main application

  Styling                 Tailwind CSS            UI

  Interactive canvas      React Konva             Object layers and
                                                  manipulation

  Backend                 Python FastAPI          APIs and processing
                                                  jobs

  Speech-to-text          Gnani Prisma v2.5       Tanglish transcription

  Optional speech         Gnani Timbre v2.5       Voice feedback
  response                                        

  Object detection        YOLO                    Object instances

  Segmentation            SAM 2 or compatible     Pixel masks
                          model                   

  Image processing        OpenCV + Pillow         Cutouts, compositing,
                                                  export

  Background inpainting   LaMa                    Local background
                                                  reconstruction

  Geometry                Shapely                 Overlap and boundary
                                                  checks

  Optional optimization   OR-Tools                Advanced layout
                                                  selection

  Storage                 Local filesystem        Original, masks,
                          initially               cutouts, layouts
  -----------------------------------------------------------------------

Verify model compatibility, hardware requirements, licenses, API
versions and challenge credits before implementation. Keep model
integrations behind service interfaces so they can be replaced
independently.

## 9. Backend API design

  -------------------------------------------------------------------------
  Method and endpoint                   Purpose
  ------------------------------------- -----------------------------------
  `POST /api/rooms`                     Upload image and create room

  `GET /api/rooms/{id}`                 Get room and preparation status

  `POST /api/rooms/{id}/prepare`        Run detection, segmentation and
                                        background preparation

  `GET /api/rooms/{id}/objects`         Get detected objects

  `PATCH /api/rooms/{id}/objects`       Correct labels, masks or object
                                        metadata

  `POST /api/rooms/{id}/transcribe`     Transcribe voice instruction

  `POST /api/rooms/{id}/instructions`   Parse and resolve instruction

  `POST /api/rooms/{id}/operations`     Apply structured scene operations

  `POST /api/rooms/{id}/layouts`        Save a layout snapshot

  `GET /api/rooms/{id}/layouts`         List saved layouts

  `POST /api/rooms/{id}/render`         Render image and annotated plan
                                        locally

  `GET /api/rooms/{id}/results`         Get output paths/URLs
  -------------------------------------------------------------------------

For a single-user demo, local file storage and JSON manifests are
enough. Add a database only when persistence, accounts or concurrent
users become necessary.

## 10. Suggested project structure

``` text
placewise/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ImageUploader.tsx
│   │   │   ├── VoiceRecorder.tsx
│   │   │   ├── TranscriptEditor.tsx
│   │   │   ├── ObjectDetectionOverlay.tsx
│   │   │   ├── ObjectToolbar.tsx
│   │   │   ├── ArrangementCanvas.tsx
│   │   │   ├── LayoutHistory.tsx
│   │   │   └── ResultViewer.tsx
│   │   ├── features/
│   │   │   ├── scene/
│   │   │   ├── instructions/
│   │   │   └── arrangement/
│   │   ├── services/
│   │   └── pages/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── rooms.py
│   │   │   ├── vision.py
│   │   │   ├── voice.py
│   │   │   ├── instructions.py
│   │   │   ├── layouts.py
│   │   │   └── rendering.py
│   │   ├── services/
│   │   │   ├── object_detector.py
│   │   │   ├── segmentation.py
│   │   │   ├── background_inpainting.py
│   │   │   ├── gnani_prisma.py
│   │   │   ├── instruction_parser.py
│   │   │   ├── object_resolver.py
│   │   │   ├── layout_engine.py
│   │   │   ├── scene_renderer.py
│   │   │   └── plan_renderer.py
│   │   ├── schemas/
│   │   └── config.py
│   └── requirements.txt
│
├── storage/
│   └── rooms/
├── tests/
│   ├── test_instruction_parser.py
│   ├── test_object_resolution.py
│   ├── test_layout_constraints.py
│   └── test_scene_rendering.py
└── README.md
```

## 11. Development plan for a two-person team

### Stage 1 --- Foundation

**Developer A** - Set up FastAPI. - Implement upload and image
normalization. - Integrate YOLO. - Save object detections.

**Developer B** - Set up React and Tailwind. - Build upload screen. -
Build photograph preview. - Build object-label overlay.

**Milestone:** upload a room photograph and inspect detected objects.

### Stage 2 --- Segmentation and reusable assets

**Developer A** - Integrate segmentation. - Generate masks and
transparent object cutouts. - Save asset metadata. - Test local
inpainting.

**Developer B** - Build object correction and selection UI. - Display
object instances. - Add manual correction controls.

**Milestone:** obtain a clean background and reusable object layers for
one test room.

### Stage 3 --- Voice and instruction understanding

**Developer A** - Build instruction schema. - Implement object reference
resolution. - Implement ambiguity and conflict handling.

**Developer B** - Integrate Gnani Prisma. - Build voice recorder and
transcript editor. - Test Tanglish commands.

**Milestone:** a spoken instruction becomes correct object-level
actions.

### Stage 4 --- Arrangement editor

**Developer A** - Implement layout rules. - Implement geometric
checks. - Implement scene JSON updates.

**Developer B** - Integrate React Konva. - Implement drag, move, scale
and rotate. - Implement selection and layer ordering.

**Milestone:** users can rearrange extracted objects without
image-generation calls.

### Stage 5 --- Rendering and plan

**Developer A** - Implement local image compositing. - Add background
and object shadows. - Export final image.

**Developer B** - Implement annotation overlay. - Add before/after
comparison. - Add undo, redo, reset and save layout.

**Milestone:** final photograph and placement plan match the same scene
state.

### Stage 6 --- Integration and demo

-   Test removal-first and keep-first Tanglish instructions.
-   Test multiple instances of the same object.
-   Test object correction.
-   Test overlapping masks and inpainting artifacts.
-   Test repeated layout changes without AI image calls.
-   Record a short demonstration.
-   Document limitations honestly.

## 12. Testing and evaluation

Start with 10--20 room photographs, 5--10 common object classes and
30--50 Tanglish instructions.

  Area                   Metric
  ---------------------- ------------------------------------------------------
  Detection              Correct object instances
  Segmentation           Mask quality and edge accuracy
  Speech                 Correct transcription of object names
  Intent                 Correct KEEP/REMOVE/MOVE extraction
  Reference resolution   Correct matching to object IDs
  Background             Visible inpainting artifacts
  Rendering              Correct visibility, scale, position and z-order
  Layout                 Overlap and boundary violations
  User experience        Whether the result is understandable and useful
  Cost                   Paid API calls per prepared room and per layout edit

A key cost test: - One new photograph triggers scene preparation. - Ten
subsequent layout changes trigger no image-generation calls. - Voice
commands may require speech-recognition calls, but movement and
rendering remain local.

Record actual measurements. Do not publish accuracy claims without
testing.

## 13. Risks and safeguards

### Background reconstruction

A single photo cannot reveal the exact surface hidden behind furniture.
Inpainting estimates missing pixels and large occluded regions may look
artificial.

Mitigation: - Prefer photos with visible floor/wall around objects. -
Use conservative masks. - Inspect the clean background. - Let users
retry preparation if reconstruction is poor. - Keep the original
photograph.

### Object identity

Transparent cutouts preserve the source object's appearance better than
asking a generative model to redraw it. Moving an object may expose
surfaces that were never photographed.

Mitigation: - Preserve source cutouts. - Avoid unnecessary scaling and
rotation. - Use image editing only where reconstruction is required. -
Label the result as a visualization.

### Perspective and physical accuracy

A flat photograph is not a 3D room model. Perspective affects apparent
size and distance.

Mitigation: - Use image-coordinate layouts for visual proposals. - Avoid
claiming exact measurements. - Use approximate floor-contact and overlap
checks. - Treat physical clearance as unverified.

### Shadows and depth ordering

Cutouts may look pasted onto the room if shadows and occlusion are
wrong.

Mitigation: - Preserve alpha masks. - Store z-order. - Add soft contact
shadows. - Allow manual foreground/background ordering when necessary.

## 14. Cost-efficient API strategy

  --------------------------------------------------------------------------------
  Operation           Technology             Image-generation API Frequency
                                                            call? 
  ------------------- --------------------- --------------------- ----------------
  Speech              Gnani Prisma                             No Per voice input
  transcription                                                   

  Object detection    Local YOLO                               No Per new photo

  Segmentation        Local SAM 2                              No Per new photo

  Background          Local LaMa                               No Per prepared
  reconstruction                                                  scene

  Object cutout       OpenCV/Pillow                            No Per prepared
  generation                                                      scene

  Move/rotate/scale   React Konva / scene                      No As often as
                      engine                                      needed

  Object hide/show    Scene engine                             No As often as
                                                                  needed

  Layout checks       Shapely/rules                            No As often as
                                                                  needed

  Final image export  Pillow/OpenCV/Konva                      No As often as
                                                                  needed

  Plan rendering      SVG/Konva                                No As often as
                                                                  needed

  Optional voice      Gnani Timbre            No image-generation As needed
  response                                                   call 
  --------------------------------------------------------------------------------

The expensive scene-preparation work is performed once per new
photograph. Reuse the resulting assets for all later interactions.

## 15. Recommended implementation order

Do not integrate every AI model at once. Build in this order:

1.  **Static scene prototype:** use the illustrated room from the
    current PLACEWISE demo and make furniture separate transparent
    PNG/SVG layers.
2.  **Canvas editor:** implement drag, move, hide, scale, rotate, undo
    and reset using React Konva.
3.  **Local renderer:** export the scene as an image and generate an
    annotation overlay.
4.  **Scene manifest:** store all object properties in JSON.
5.  **Voice commands:** connect Prisma and map Tanglish instructions to
    scene operations.
6.  **Real-photo detection:** integrate YOLO and segmentation.
7.  **Background reconstruction:** add local inpainting and transparent
    cutout extraction.
8.  **Automatic arrangement:** implement basic placement rules and
    geometric checks.
9.  **Full integration:** ensure voice, scene state, edited image and
    plan stay synchronized.

This order gives you a working product early. Demonstrate the
arrangement engine using your existing illustrated room before solving
the harder problem of arbitrary real-world photographs.

## 16. Final architecture recommendation

PLACEWISE should have three major capabilities:

1.  **Understand:** Gnani Prisma plus an instruction parser turns
    natural Tanglish speech into object-level actions.
2.  **Prepare:** local vision models detect and segment objects, while
    local inpainting creates a reusable background.
3.  **Arrange and visualize:** a scene engine and React Konva manipulate
    transparent object layers and render both outputs locally.

The central design decision is to make the prepared scene reusable. The
user should be able to say "chair remove pannunga", then "sofa konjam
left move pannunga", then "table sofa pakkathula vaiyunga" without
regenerating the entire photograph after every command.

**Use AI to understand and prepare the room once. Use a local graphics
engine to explore arrangements repeatedly.**

## Useful references

-   [Gnani AI](https://www.gnani.ai/)
-   [Gnani API
    documentation](https://docs.gnani.ai/api/introduction/introduction)
-   [React Konva documentation](https://konvajs.org/docs/react/)
-   [SAM 2 repository](https://github.com/facebookresearch/sam2)
-   [Ultralytics documentation](https://docs.ultralytics.com/)
-   [LaMa inpainting repository](https://github.com/advimman/lama)
-   [OpenCV documentation](https://docs.opencv.org/)
-   [Shapely documentation](https://shapely.readthedocs.io/)
