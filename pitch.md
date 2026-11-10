# PLACEWISE – Your Space, Your Voice, Your Arrangement

## Solution Pitch

Rearranging a room or organizing a cluttered space can be frustrating. People often know what they want to keep and what they want to remove, but struggle to visualize how everything should be arranged. Existing interior-design tools can require manual placement, measurements and design knowledge, making them difficult for everyday users.

**PLACEWISE is an AI-powered, voice-controlled space rearrangement assistant that turns a simple photograph and natural-language instructions into a visual arrangement plan.**

Users upload or capture a photograph of their living room, bedroom, kitchen, workspace or another physical space. They then speak naturally in Tamil, Tanglish or English, explaining what they want to keep or remove. For example:

> “Sofa-vum TV-vum venum. Indha rendu chairs-um coffee table-um vendaam. Remaining things neat-ah arrange pannunga.”

PLACEWISE understands the instruction, identifies individual objects in the photograph, and translates the request into **KEEP, REMOVE and MOVE** actions. It then generates two outputs: an edited visualization of the rearranged space and an annotated arrangement plan showing object labels, proposed positions and movement directions.

## How It Works

- **Voice Understanding:** Gnani Prisma v2.5 converts natural Tanglish and Tamil speech into text, allowing users to interact without complicated menus or design terminology.
- **Object Intelligence:** YOLOv8 instance segmentation identifies individual furniture items, appliances and household objects with pixel-level masks.
- **Intelligent Arrangement:** A spatial planning engine determines suitable object positions while checking basic overlap and placement constraints.
- **Visual Reconstruction:** Local image processing and inpainting remove unwanted objects, reconstruct exposed background regions and reposition retained objects.
- **Dual Visual Output:** Users receive both a rearranged photograph and an annotated placement plan generated from the same arrangement decisions.

## What Makes PLACEWISE Different?

PLACEWISE focuses on people's existing belongings rather than furniture catalogues or virtual shopping. Its interaction is intentionally simple: users do not need to measure rooms, draw floor plans or manually position every object. They just describe what stays and what goes in their own language.

The system also uses reusable object masks and local image rendering, allowing users to experiment with multiple arrangements without repeatedly calling expensive image-generation APIs.

## Technology Stack

React, TypeScript, Tailwind CSS, Python FastAPI, Gnani Prisma v2.5, YOLOv8-seg, SAM 2, OpenCV, Pillow, LaMa inpainting and Shapely.

**PLACEWISE makes space organization accessible to everyone: show us your space, tell us what you want, and let AI help you visualize the possibilities.**
