import sys
sys.path.insert(0, 'backend')
from app.services.object_detector import RoomObjectDetector

detector = RoomObjectDetector()
objs = detector.detect_objects('demo/rooms/real_living_room.jpg', 'demo_real')
print(f"Detected {len(objs)} objects:")
for o in objs:
    print(f" - {o['object_id']}: class={o['class']}, conf={o['confidence']}, bbox={o['bbox']}, mask={o['mask_path']}")
