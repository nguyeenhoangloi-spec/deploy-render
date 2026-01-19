import os, sys, pickle
import cv2
import face_recognition

DATASET_DIR = "dataset"
OUTPUT_FILE = "encodings.pkl"

if len(sys.argv) < 2:
    print("Usage: python update_single_embedding.py <person_key>")
    sys.exit(1)

person = sys.argv[1]
person_dir = os.path.join(DATASET_DIR, person)
if not os.path.isdir(person_dir):
    print(f"Person directory not found: {person_dir}")
    sys.exit(1)

# Load existing encodings
encodings = []
names = []
if os.path.exists(OUTPUT_FILE):
    try:
        with open(OUTPUT_FILE, 'rb') as f:
            data = pickle.load(f)
        encodings = data.get('encodings', [])
        names = data.get('names', [])
    except Exception as e:
        print(f"[WARN] Cannot read existing encodings: {e}")

# Remove old entries for this person to avoid duplicates
if names:
    filtered_encodings = []
    filtered_names = []
    for enc, name in zip(encodings, names):
        if name != person:
            filtered_encodings.append(enc)
            filtered_names.append(name)
    encodings = filtered_encodings
    names = filtered_names

# Build new encodings for this person
images = [f for f in os.listdir(person_dir) if f.lower().endswith((".jpg",".jpeg",".png",".bmp"))]
count = 0
for img_name in images:
    path = os.path.join(person_dir, img_name)
    img_bgr = cv2.imread(path)
    if img_bgr is None:
        print(f"[SKIP] Invalid image: {path}")
        continue
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    boxes = face_recognition.face_locations(rgb, model='hog')
    if not boxes:
        print(f"[SKIP] No face in {path}")
        continue
    encs = face_recognition.face_encodings(rgb, boxes)
    if encs:
        encodings.append(encs[0])
        names.append(person)
        count += 1

with open(OUTPUT_FILE, 'wb') as f:
    pickle.dump({"encodings": encodings, "names": names}, f)
print(f"Updated encodings for {person}: {count} images. Total entries: {len(names)}")
