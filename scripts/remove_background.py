import os
from PIL import Image

def remove_white_background(input_path, output_path, tolerance=30):
    print(f"Processing {input_path}...")
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()

    newData = []
    for item in datas:
        # Check if pixel is close to white
        # item is (R, G, B, A)
        if item[0] > (255 - tolerance) and item[1] > (255 - tolerance) and item[2] > (255 - tolerance):
            newData.append((255, 255, 255, 0)) # Make transparent
        else:
            newData.append(item)

    img.putdata(newData)
    img.save(output_path, "PNG")
    print(f"Saved to {output_path}")

# Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
# Map: source_file -> target_file (in app/assets/images)
# Note: target names override the old "broken" names
tasks = {
    "house_solid.png": "../app/assets/images/house_v2.png",
    "battery_solid.png": "../app/assets/images/battery.png",
    "ev_car_solid.png": "../app/assets/images/ev_car.png",
    "grid_pole_solid.png": "../app/assets/images/grid_pole.png"
}

for src, dest in tasks.items():
    src_path = os.path.join(base_dir, src)
    dest_path = os.path.join(base_dir, dest)
    remove_white_background(src_path, dest_path, tolerance=30)
