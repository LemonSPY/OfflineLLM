"""
Generates OfflineLLM's logo/icon artwork: a black clip-art silhouette of a
lighthouse rising left-of-center above a long low building with a stepped
roofline, its windows cut out as transparent "holes" (so they read as light
against a dark silhouette, like a paper-cut stencil). Original stylized
artwork inspired by a classic lighthouse-and-cellhouse composition, not a
trace of any photograph.

Outputs:
    logo.png   - the full landscape artwork (RGBA, transparent background)
    app.ico    - a square, icon-cropped version at standard Windows icon sizes

Run with: python generate_logo.py
(requires Pillow: pip install pillow)
"""

from PIL import Image, ImageDraw

W, H = 1200, 800
TOP_MARGIN = 40
BLACK = (0, 0, 0, 255)
CLEAR = (0, 0, 0, 0)

img = Image.new("RGBA", (W, H), CLEAR)
draw = ImageDraw.Draw(img)


def y(v):
    return v + TOP_MARGIN


# --- main building wall (single band, full width) ------------------------
wall_left, wall_right = 60, 1140
wall_top, wall_bottom = y(340), y(660)
draw.rectangle([wall_left, wall_top, wall_right, wall_bottom], fill=BLACK)

# --- stepped hip roof: taller ridge over the left two-thirds (where the
# lighthouse sits), lower ridge over the right wing - matches the real
# building's stepped roofline instead of one symmetric gable. -------------
STEP_X = 780
draw.polygon(
    [(40, y(340)), (STEP_X, y(340)), (680, y(260)), (260, y(260))],
    fill=BLACK,
)
draw.polygon(
    [(STEP_X, y(340)), (1160, y(340)), (1080, y(300)), (820, y(300))],
    fill=BLACK,
)

# --- lighthouse, positioned left-of-center over the taller roof section ---
LH_CX = 500  # ~40% across a 1200-wide canvas, matching the photo's framing

block_left, block_right = LH_CX - 100, LH_CX + 100
draw.rectangle([block_left, y(180), block_right, y(340)], fill=BLACK)
draw.polygon(
    [
        (block_left, y(180)),
        (block_right, y(180)),
        (LH_CX + 60, y(150)),
        (LH_CX - 60, y(150)),
    ],
    fill=BLACK,
)

# tapered tower
draw.polygon(
    [
        (LH_CX - 45, y(150)),
        (LH_CX + 45, y(150)),
        (LH_CX + 30, y(60)),
        (LH_CX - 30, y(60)),
    ],
    fill=BLACK,
)

# gallery deck (walkway ledge, slightly wider than the tower)
draw.rectangle([LH_CX - 50, y(45), LH_CX + 50, y(58)], fill=BLACK)

# lantern room
draw.rectangle([LH_CX - 25, y(15), LH_CX + 25, y(45)], fill=BLACK)

# conical roof cap + finial
draw.polygon([(LH_CX - 25, y(15)), (LH_CX + 25, y(15)), (LH_CX, y(0))], fill=BLACK)
draw.rectangle([LH_CX - 2, y(-10), LH_CX + 2, y(0)], fill=BLACK)

# --- window cutouts (transparent) ----------------------------------------


def windows_row(x_start, x_end, y_top, y_bot, count, w):
    span = x_end - x_start
    gap = (span - count * w) / (count + 1)
    x = x_start + gap
    for _ in range(count):
        draw.rectangle([x, y_top, x + w, y_bot], fill=CLEAR)
        x += w + gap


# upper-floor window row along the main facade
windows_row(120, 1080, y(390), y(430), count=15, w=34)

# lower-floor, wider window/door openings - concentrated under the taller
# left section, matching the photo's larger ground-floor openings
windows_row(140, 740, y(500), y(600), count=5, w=74)

# right wing gets its own, slightly smaller ground-floor openings since its
# wall is shorter
windows_row(800, 1080, y(520), y(600), count=3, w=64)

# small windows on the raised central block
windows_row(block_left + 20, block_right - 20, y(230), y(270), count=2, w=40)

# a thin glazing band in the lantern room
draw.rectangle([LH_CX - 18, y(22), LH_CX + 18, y(38)], fill=CLEAR)

img.save("logo.png")
print("wrote logo.png", img.size)

# --- square icon crop -----------------------------------------------------
# Center the crop on the lighthouse so the icon stays recognizable at small
# sizes even though the full logo is a wide landscape composition.
crop_size = H
left = max(0, min(W - crop_size, LH_CX - crop_size // 2))
icon_src = img.crop((left, 0, left + crop_size, crop_size))

icon_src.save("app.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("wrote app.ico")
