# PLACEWISE --- Selected Instance Segmentation & Annotation Plan

**Version:** MVP implementation specification\
**Primary goal:** Produce accurate, separate pixel-level masks for
furniture and household objects so PLACEWISE can remove, extract, move
and rearrange them without repeatedly generating new images.

------------------------------------------------------------------------

## 1. Final technology choices

These are the recommended choices for the first PLACEWISE
implementation. Avoid spending time evaluating several alternatives in
parallel.

  -----------------------------------------------------------------------
  Area                    Selected choice         Why this is the MVP
                                                  choice
  ----------------------- ----------------------- -----------------------
  Object segmentation     **YOLOv8s-seg**         Practical balance of
  model                                           speed, model size and
                                                  segmentation capability

  Initial pretrained      **`yolov8s-seg.pt`**    Gives a starting point
  weights                                         before custom training

  Annotation platform     **CVAT**                Supports polygon masks,
                                                  instance-level
                                                  annotation and YOLO
                                                  segmentation export

  Assisted mask           **SAM 2**               Helps propose object
  generation                                      masks that annotators
                                                  can correct

  Dataset format          **Ultralytics YOLO      Directly compatible
                          segmentation**          with YOLOv8-seg
                                                  training

  Image preprocessing     **OpenCV + Pillow**     Resize, mask
                                                  processing, alpha
                                                  cutouts and compositing

  Background              **LaMa, run locally**   Reconstructs the areas
  reconstruction                                  hidden behind
                                                  removed/moved objects
                                                  without a paid
                                                  image-generation call

  Arrangement UI          **React + TypeScript +  Independent object
                          React Konva**           layers, drag, resize,
                                                  rotate and export

  Backend                 **Python + FastAPI**    Connects detection,
                                                  masks, scene data,
                                                  voice and rendering

  Speech recognition      **Gnani Prisma v2.5**   Converts Tanglish
                                                  speech to text

  Geometry checks         **Shapely**             Basic overlap and
                                                  boundary checks in
                                                  image coordinates

  Scene storage for MVP   **JSON manifest + local Avoids unnecessary
                          files**                 database work during
                                                  the prototype
  -----------------------------------------------------------------------

**Do not add another image-generation model to the normal rearrangement
loop.** Use image AI only if a future feature genuinely needs generative
reconstruction beyond what local inpainting can provide.

## 2. What PLACEWISE must produce

For every visible object instance, the segmentation stage should return:

-   A class label, such as `sofa`, `chair` or `potted_plant`.
-   A confidence score.
-   A bounding box.
-   An individual pixel-level mask.
-   A unique PLACEWISE object ID.
-   A transparent PNG cutout derived from the original photograph.

Example output:

``` json
{
  "object_id": "chair_02",
  "class_name": "chair",
  "confidence": 0.94,
  "bbox_xyxy": [420, 280, 610, 590],
  "mask_path": "masks/chair_02.png",
  "cutout_path": "objects/chair_02.png"
}
```

The numbers are illustrative. YOLO predicts the class, confidence, box
and mask. PLACEWISE assigns stable object IDs and asset paths after
inference.

### Keep these stages separate

1.  **Segmentation:** what object is present, and which pixels belong to
    it?
2.  **Instruction understanding:** does the user want to KEEP, REMOVE or
    MOVE it?
3.  **Arrangement:** where should a retained object go?
4.  **Rendering:** how should the edited photograph and annotated plan
    be drawn?

YOLO must not be responsible for deciding whether an object should be
removed or moved.

------------------------------------------------------------------------

## 3. Dataset class list --- selected MVP taxonomy

Start with these 15 classes. Do not expand the class list until the
first model is trained and evaluated.

  ------------------------------------------------------------------------
                      Class ID Class name            Annotation guidance
  ---------------------------- --------------------- ---------------------
                             0 `sofa`                Sofas and sectional
                                                     sofas

                             1 `chair`               Dining chairs,
                                                     armchairs and
                                                     individual chairs

                             2 `table`               Coffee, side and
                                                     dining tables

                             3 `tv`                  Television screens
                                                     and their visible
                                                     body/stand when
                                                     clearly part of the
                                                     TV instance

                             4 `bookshelf`           Bookcases and open
                                                     shelving units

                             5 `bed`                 Bed frame and
                                                     mattress as one
                                                     instance when
                                                     visually one bed

                             6 `cupboard`            Wardrobes and closed
                                                     storage cabinets

                             7 `potted_plant`        Plant and its pot as
                                                     one instance

                             8 `lamp`                Floor lamps and table
                                                     lamps

                             9 `bowl`                Individual visible
                                                     bowls

                            10 `refrigerator`        Refrigerator

                            11 `washing_machine`     Washing machine

                            12 `fan`                 Standing or table fan

                            13 `box`                 Individual storage or
                                                     cardboard boxes

                            14 `other_object`        Only for selected
                                                     objects that matter
                                                     to the demo; avoid
                                                     using this as a
                                                     catch-all for
                                                     arbitrary clutter
  ------------------------------------------------------------------------

### Important taxonomy rules

-   Use the same class for the same type of object in every image.
-   Annotate separate instances separately: `chair_01`, `chair_02`, etc.
-   Do not merge a sofa and cushions into one mask if the cushions are
    separate movable objects in your intended use case. For the MVP,
    choose one consistent policy and document it.
-   Keep the `other_object` category limited. If it becomes a large
    mixed class, it will be difficult for the model to learn
    consistently.
-   A model trained on this taxonomy can only be expected to recognize
    categories represented adequately in its dataset.

### Pretrained model limitation

The pretrained COCO YOLOv8 segmentation model does not contain every
PLACEWISE class. For example, `bookshelf` is not a standard COCO class.
Use pretrained weights as an initialization, then fine-tune on your
custom annotated dataset. Do not assume the pretrained model already
recognizes all 15 labels.

------------------------------------------------------------------------

## 4. Annotation tool and exact annotation method

### Selected tool: CVAT

Use CVAT for the ground-truth dataset.

1.  Create a CVAT project named `PLACEWISE-Furniture-Segmentation`.
2.  Add the 15 class labels listed above.
3.  Create tasks from your room photographs.
4.  Annotate each object as an independent polygon/mask.
5.  Review and correct all automatically proposed masks.
6.  Export in Ultralytics YOLO segmentation format.

CVAT: https://www.cvat.ai/\
CVAT documentation: https://docs.cvat.ai/

### Annotation standard

**Trace the visible silhouette, not a rectangle around the object.**

For a sofa: - Follow the backrest and armrests. - Include visible
cushions that are part of the sofa under your chosen class policy. -
Include visible legs if they are clearly part of the sofa. - Exclude
floor, wall and nearby tables.

For a chair: - Include the visible seat, back, frame and legs. - Keep a
chair separate from an adjacent table. - Do not draw through an
occluding object.

For a table: - Include the visible tabletop and legs/supports. - Exclude
objects sitting on the tabletop if they are separately labelled classes.

For a plant: - Follow the visible leaf silhouette and pot. - Do not
include the wall or window behind the leaves.

For a TV: - Include the visible television body. - Treat a separate TV
cabinet or console as a separate object if it is in the taxonomy.

### Occlusion rule

Annotate **visible pixels only**. If a coffee table hides the lower part
of a sofa, annotate the visible sofa region; do not invent the hidden
sofa boundary.

### Partial-object rule

If an object is cut off by the edge of the photograph, annotate the
visible portion if its class is identifiable. Do not hallucinate the
missing part.

### Annotation quality checklist

Before accepting an image:

-   [ ] Every target object instance has its own annotation.
-   [ ] The class is correct.
-   [ ] The polygon follows the visible silhouette.
-   [ ] Adjacent objects are not merged.
-   [ ] Background pixels are not unnecessarily included.
-   [ ] Occluded regions are treated consistently.
-   [ ] Partial objects are annotated only where visible.
-   [ ] There are no duplicate masks.
-   [ ] Small but important parts such as chair legs are included where
    visible.

**Quality beats quantity:** a smaller, consistently annotated dataset is
better than a large dataset full of loose boxes and inconsistent
polygons.

------------------------------------------------------------------------

## 5. Semi-automatic annotation --- SAM 2 plus human review

Use SAM 2 to propose masks and reduce manual polygon work. Human review
remains mandatory.

### Selected workflow

1.  Run a detector to propose object boxes.
2.  Pass each relevant box/prompt to SAM 2.
3.  Generate a proposed mask.
4.  Open the mask in CVAT or the annotation review workflow.
5.  Correct boundaries, class labels and missed objects.
6.  Export only reviewed annotations.

SAM 2 repository: https://github.com/facebookresearch/sam2

### Important distinction

SAM 2 is a promptable segmentation model, not a guarantee that the
correct object was selected. If the detector misses an object or gives a
poor prompt, SAM may segment the wrong region. Review the result.

### Optional auto-annotation experiment

Ultralytics provides an `auto_annotate` workflow. Test it on a small
sample first; do not automatically accept all generated masks as ground
truth.

``` python
from ultralytics.data.annotator import auto_annotate

auto_annotate(
    data="dataset/images/train",
    det_model="yolov8s.pt",
    sam_model="sam_b.pt",
    device="0",
    conf=0.25,
    iou=0.5
)
```

This is an annotation-assistance experiment. Confirm the installed
Ultralytics version and supported model arguments before running it. The
detector may not know your custom classes yet, so manual annotation or a
suitable custom detector may still be needed.

------------------------------------------------------------------------

## 6. Dataset size and collection plan

Use staged collection rather than trying to annotate a huge dataset
immediately.

  ------------------------------------------------------------------------
  Stage                                 Image target Purpose
  --------------------- ---------------------------- ---------------------
  Pipeline test                               30--50 Verify CVAT export,
                                                     training and
                                                     inference

  First custom model                        150--300 Establish baseline
                                                     performance

  Improved MVP dataset                      500--750 Add variation and
                                                     improve weak classes

  Later expansion                      1,000--1,500+ Broader environments
                                                     and object variation
  ------------------------------------------------------------------------

These are planning targets, not guarantees of accuracy.

### Photograph diversity

Collect images with: - Different room types and layouts. - Different
furniture styles, colours and materials. - Wide and close camera
views. - Bright, dim and mixed lighting. - Multiple instances of the
same class. - Partial occlusion. - Objects cut off at image
boundaries. - Cluttered and uncluttered spaces. - Different camera
heights and perspectives.

### Dataset split

Use a starting split of approximately: - 70% training. - 20%
validation. - 10% test.

Split by room, source or capture session. Do not put near-identical
photographs of the same room in both training and test sets; that can
make the test score misleading.

Make sure each image has a matching label file. Images without target
objects should have an empty label file.

------------------------------------------------------------------------

## 7. YOLOv8-seg training configuration

### Selected starting model

`yolov8s-seg.pt`

Start with 640-pixel training images and a conservative batch size.
Adjust the batch size to fit the available GPU memory.

``` python
from ultralytics import YOLO

model = YOLO("yolov8s-seg.pt")

results = model.train(
    data="PLACEWISE-DATASET/data.yaml",
    epochs=100,
    imgsz=640,
    batch=8,
    patience=20,
    workers=4,
    project="PLACEWISE",
    name="furniture_segmentation"
)
```

If GPU memory is insufficient, reduce `batch` (for example, to 4 or 2).
If small objects and boundaries are poorly resolved, experiment with a
larger image size such as 960, provided the hardware supports it.

### Dataset directory

``` text
PLACEWISE-DATASET/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
├── labels/
│   ├── train/
│   ├── val/
│   └── test/
└── data.yaml
```

### `data.yaml`

``` yaml
path: PLACEWISE-DATASET

train: images/train
val: images/val
test: images/test

names:
  0: sofa
  1: chair
  2: table
  3: tv
  4: bookshelf
  5: bed
  6: cupboard
  7: potted_plant
  8: lamp
  9: bowl
  10: refrigerator
  11: washing_machine
  12: fan
  13: box
  14: other_object
```

### Validate mask quality

``` python
from ultralytics import YOLO

model = YOLO(
    "PLACEWISE/furniture_segmentation/weights/best.pt"
)

metrics = model.val(
    data="PLACEWISE-DATASET/data.yaml"
)

print("Box mAP50-95:", metrics.box.map)
print("Mask mAP50-95:", metrics.seg.map)
print("Mask mAP50:", metrics.seg.map50)
```

Track mask metrics as well as box metrics. A correct box does not mean
the object boundary is good enough for extraction.

------------------------------------------------------------------------

## 8. Inference and individual mask extraction

Use the custom trained model for prediction.

``` python
from ultralytics import YOLO
import cv2
import numpy as np
from pathlib import Path

model = YOLO(
    "PLACEWISE/furniture_segmentation/weights/best.pt"
)

image_path = "test_room.jpg"
image = cv2.imread(image_path)

results = model.predict(
    source=image_path,
    conf=0.35,
    imgsz=960,
    retina_masks=True,
    verbose=False
)

result = results[0]

if result.masks is not None:
    masks = result.masks.data.cpu().numpy()

    for index, mask in enumerate(masks):
        class_id = int(result.boxes.cls[index])
        confidence = float(result.boxes.conf[index])
        class_name = model.names[class_id]

        # Resize mask to the original image dimensions if needed.
        mask = cv2.resize(
            mask,
            (image.shape[1], image.shape[0]),
            interpolation=cv2.INTER_NEAREST
        )

        binary_mask = (mask > 0.5).astype(np.uint8) * 255

        print({
            "object_id": f"{class_name}_{index + 1}",
            "class": class_name,
            "confidence": round(confidence, 3)
        })

        cv2.imwrite(
            f"mask_{index + 1}.png",
            binary_mask
        )
```

Check the mask dimensions and alignment against the original image. Do
not assume the mask is automatically aligned with an image that has been
resized or EXIF-rotated differently.

### Generate transparent cutouts

``` python
from PIL import Image
import numpy as np

original = Image.open(image_path).convert("RGBA")

# binary_mask must be the matching original-resolution mask.
alpha = Image.fromarray(binary_mask).convert("L")

cutout = original.copy()
cutout.putalpha(alpha)

cutout.save("chair_01.png")
```

The transparent PNG is a reusable object asset. Preserve the original
crop and mask as well, so the cutout can be regenerated if needed.

------------------------------------------------------------------------

## 9. PLACEWISE object metadata and action labels

YOLO produces segmentation information. PLACEWISE adds object identity
and user intent.

Example:

``` json
{
  "objects": [
    {
      "id": "sofa_01",
      "class": "sofa",
      "confidence": 0.96,
      "action": "MOVED",
      "source_bbox": [100, 300, 450, 650],
      "destination_bbox": [300, 350, 650, 700],
      "mask_path": "masks/sofa_01.png",
      "cutout_path": "objects/sofa_01.png"
    },
    {
      "id": "chair_01",
      "class": "chair",
      "confidence": 0.91,
      "action": "REMOVE",
      "source_bbox": [500, 350, 700, 600],
      "mask_path": "masks/chair_01.png",
      "cutout_path": "objects/chair_01.png"
    },
    {
      "id": "tv_01",
      "class": "tv",
      "confidence": 0.98,
      "action": "KEEP",
      "source_bbox": [800, 100, 1050, 280],
      "destination_bbox": [800, 100, 1050, 280],
      "mask_path": "masks/tv_01.png",
      "cutout_path": "objects/tv_01.png"
    }
  ]
}
```

Suggested visualization:

  State                  Colour
  ---------------------- --------------
  KEEP                   Cyan/blue
  REMOVE                 Red
  MOVED                  Green
  Proposed destination   Dashed green
  Movement arrow         Yellow

These are frontend conventions, not YOLO output.

------------------------------------------------------------------------

## 10. Build the arrangement renderer

Use the following division of responsibility:

### YOLOv8-seg

-   Finds supported object instances.
-   Predicts class and confidence.
-   Produces boxes and masks.

### PLACEWISE backend

-   Assigns IDs.
-   Matches Tanglish references to objects.
-   Stores KEEP/REMOVE/MOVE decisions.
-   Calculates proposed positions.
-   Checks simple overlap constraints.

### Frontend renderer

-   Displays coloured masks and labels.
-   Draws destination boxes and movement arrows.
-   Allows users to select and correct objects.

### Image renderer

-   Uses the cleaned background.
-   Composites visible transparent object cutouts.
-   Exports the rearranged photograph.

Do not ask YOLO to draw arrows, assign KEEP/MOVED status or generate the
final edited photograph.

------------------------------------------------------------------------

## 11. Ten-day implementation plan for two developers

### Days 1--2: Dataset and annotation setup

**Developer A** - Create the CVAT project and class taxonomy. - Collect
the first 30--50 room photographs. - Define annotation rules and review
a sample.

**Developer B** - Build a Python inference script using
`yolov8s-seg.pt`. - Test pretrained predictions on representative room
images. - Create a visual mask-inspection script.

**Milestone:** agreed class definitions, annotation workflow and working
inference baseline.

### Days 3--4: Annotation and first training run

**Developer A** - Annotate individual furniture instances. - Use SAM 2
to propose masks where helpful. - Correct all proposed masks before
export.

**Developer B** - Export YOLO segmentation labels. - Check dataset paths
and class IDs. - Train the first custom YOLOv8-seg model.

**Milestone:** first custom model and a validation report.

### Days 5--6: Mask extraction

**Developer A** - Improve poor annotations and weak classes. - Inspect
per-class mask quality. - Run inference on unseen photographs.

**Developer B** - Extract transparent PNG cutouts. - Save masks, boxes
and metadata. - Build the object-instance JSON representation.

**Milestone:** separate cutouts for detected furniture objects.

### Days 7--8: PLACEWISE visualization

**Developer A** - Implement KEEP/REMOVE/MOVE metadata. - Implement
simple object-position updates. - Add basic geometric checks.

**Developer B** - Render coloured masks and object labels. - Render
destination outlines and movement arrows. - Add the before/after
interface.

**Milestone:** an annotated arrangement plan generated from the same
object data.

### Days 9--10: Integration and demo

-   Test multiple chairs and tables in one image.
-   Test partially visible and overlapping objects.
-   Fix incorrect masks and object IDs.
-   Demonstrate removal and movement.
-   Report measured results and known limitations.

------------------------------------------------------------------------

## 12. Evaluation checklist

Evaluate the actual extracted objects, not just the model's colourful
prediction overlay.

  -----------------------------------------------------------------------
  Evaluation area                     What to inspect
  ----------------------------------- -----------------------------------
  Detection                           Was every relevant object found?

  Classification                      Is each object assigned the right
                                      class?

  Instance separation                 Are two adjacent chairs separate
                                      instances?

  Mask boundary                       Does the mask follow the visible
                                      silhouette?

  Occlusion                           Are only visible pixels annotated?

  Cutout                              Does the transparent PNG retain the
                                      object without excess background?

  Thin structures                     Are chair legs, plant leaves and
                                      table supports preserved?

  Background                          Are holes left after removal
                                      reconstructed acceptably?

  Arrangement                         Are moved objects composited in the
                                      intended locations?
  -----------------------------------------------------------------------

Record: - Box mAP50-95. - Mask mAP50-95. - Per-class mask AP. -
Precision and recall. - Manual cutout quality review. - Number of missed
or merged instances in a fixed test set.

Do not claim perfect segmentation. Even a strong model can fail on
transparent surfaces, reflective furniture, thin legs, heavy occlusion
and unusual object shapes. Improve those cases with better annotations,
additional examples and manual correction.

------------------------------------------------------------------------

## 13. Critical technical limitations

1.  **A segmentation mask only covers visible pixels.** It cannot
    recover the hidden back or underside of a sofa.
2.  **Cutting an object out does not reconstruct the room behind it.**
    Use local inpainting for the clean background.
3.  **One photograph does not reveal exact 3D geometry.** Avoid claiming
    physically verified placements.
4.  **Thin structures are difficult.** Inspect chair legs, plant leaves,
    lamp stands and table supports at full resolution.
5.  **Pretrained classes are not your custom taxonomy.** Fine-tune on
    your own annotated dataset.
6.  **Stable identity is application logic.** YOLO instance order can
    change between runs; PLACEWISE assigns IDs for the current scene and
    should not assume detection index is a permanent identity.
7.  **Human correction is part of the MVP.** A user should be able to
    correct missed or incorrectly segmented objects.

------------------------------------------------------------------------

## 14. Final selected pipeline

``` text
User uploads room photograph
          |
          v
YOLOv8s-seg custom model
          |
          v
Object classes + boxes + instance masks
          |
          v
SAM 2 assistance / manual correction
          |
          v
Reviewed masks and transparent object cutouts
          |
          +------------------------------+
          |                              |
          v                              v
Combined movable-object mask       Object metadata
          |                              |
          v                              v
Local LaMa background             Gnani Prisma transcript
reconstruction                         |
          |                        Instruction parser
          |                              |
          |                        KEEP / REMOVE / MOVE
          |                              |
          +---------------+--------------+
                          |
                          v
                 PLACEWISE scene JSON
                          |
                Arrangement engine
                          |
             +------------+------------+
             |                         |
             v                         v
       Local image renderer      Plan renderer
             |                         |
             v                         v
       Rearranged photo         Annotated plan
```

## 15. Final decisions --- do not overcomplicate the MVP

1.  Use **YOLOv8s-seg** as the custom instance-segmentation model.
2.  Use **CVAT** for dataset annotation and review.
3.  Use **SAM 2** to assist annotation, not to replace human review.
4.  Use the **Ultralytics YOLO segmentation format**.
5.  Start with the 15-class taxonomy in this document.
6.  Begin with 30--50 photographs to validate the pipeline, then grow
    toward 150--300 carefully annotated photographs for the first custom
    model.
7.  Use **LaMa locally** for background reconstruction.
8.  Extract transparent object cutouts using OpenCV/Pillow.
9.  Use **React Konva** for object manipulation and visual annotations.
10. Use the same scene metadata to render the edited photograph and the
    arrangement plan.

**First milestone:** take one cluttered living-room photograph, segment
each visible sofa, chair, table, TV, bookshelf and plant as a separate
instance, and export each as a transparent PNG with its own mask. Only
after that works should you spend time building automatic furniture
rearrangement.

## Official references

-   [Ultralytics YOLO segmentation
    task](https://docs.ultralytics.com/tasks/segment/)
-   [Ultralytics segmentation dataset
    format](https://docs.ultralytics.com/datasets/segment/)
-   [Ultralytics training
    mode](https://docs.ultralytics.com/modes/train/)
-   [Ultralytics validation
    mode](https://docs.ultralytics.com/modes/val/)
-   [CVAT](https://www.cvat.ai/)
-   [CVAT documentation](https://docs.cvat.ai/)
-   [SAM 2 repository](https://github.com/facebookresearch/sam2)
-   [LaMa inpainting repository](https://github.com/advimman/lama)
-   [React Konva documentation](https://konvajs.org/docs/react/)
-   [OpenCV documentation](https://docs.opencv.org/)
