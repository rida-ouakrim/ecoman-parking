import sqlite3

spots = []

def add_col(prefix, start_n, end_n, base_x, base_y, dy, w, h):
    step = -1 if start_n > end_n else 1
    curr_y = base_y
    for i in range(start_n, end_n + step, step):
        spots.append({
            "code": f"{prefix}{str(i).zfill(2)}",
            "x": base_x,
            "y": curr_y,
            "w": w,
            "h": h,
            "type": "horiz"
        })
        curr_y += dy

def add_row(prefix, start_n, end_n, base_x, base_y, dx, w, h):
    step = -1 if start_n > end_n else 1
    curr_x = base_x
    for i in range(start_n, end_n + step, step):
        spots.append({
            "code": f"{prefix}{str(i).zfill(2)}",
            "x": curr_x,
            "y": base_y,
            "w": w,
            "h": h,
            "type": "vert"
        })
        curr_x += dx

# ---- RIGHT BLOCKS ----
add_col("B1L", 29, 1, 1050, 50, 25, 80, 21)
add_col("B2L", 29, 1, 940, 50, 25, 80, 21)

# ---- CENTER BLOCKS ----
add_col("C1L", 24, 1, 800, 150, 25, 80, 21)

# Inside dashed blue area
add_col("C2L", 21, 1, 650, 225, 25, 80, 21)
add_col("C1L", 42, 22, 540, 225, 25, 80, 21)
add_col("C1L", 63, 43, 430, 225, 25, 80, 21)

# ---- LEFT BLOCKS ----
add_col("C3L", 14, 1, 300, 225, 25, 80, 21)

# C4: 3 cols of 7
add_col("C4L", 21, 15, 100, 600, 25, 60, 21)
add_col("C4L", 14, 8, 180, 600, 25, 60, 21)
add_col("C4L", 7, 1, 260, 600, 25, 60, 21)

# ---- TOP BLOCKS ----
add_row("D1L", 30, 16, 430, 50, 25, 21, 80)
add_row("D1L", 15, 1, 430, 150, 25, 21, 80)

# ---- BOTTOM BLOCKS ----
add_row("A1L", 20, 1, 600, 900, 25, 21, 80)

add_col("A1L", 26, 24, 450, 850, 25, 60, 21)
add_col("A1L", 23, 21, 520, 850, 25, 60, 21)

add_row("E1L", 16, 9, 100, 850, 25, 21, 80)
add_row("E1L", 8, 1, 100, 950, 25, 21, 80)

add_col("E1L", 18, 17, 300, 850, 25, 60, 21)

svg_elements = []
for s in spots:
    code = s["code"]
    bg_color = "#198754"
    stroke = "#fff"
    stroke_width = "1.5"
    
    rect = f'<rect x="{s["x"]}" y="{s["y"]}" width="{s["w"]}" height="{s["h"]}" rx="2" fill="{bg_color}" stroke="{stroke}" stroke-width="{stroke_width}" />'
    
    txt_x = s["x"] + s["w"]/2
    txt_y = s["y"] + s["h"]/2 + 3
    
    if s["type"] == "vert":
        transform = f'transform="rotate(-90 {txt_x} {txt_y})"'
        text = f'<text x="{txt_x}" y="{txt_y}" {transform} fill="white" font-size="10" font-family="sans-serif" font-weight="bold" text-anchor="middle">{code}</text>'
    else:
        text = f'<text x="{txt_x}" y="{txt_y}" fill="white" font-size="10" font-family="sans-serif" font-weight="bold" text-anchor="middle">{code}</text>'
        
    svg_elements.append(rect)
    svg_elements.append(text)

svg_str = f"""<html><body style="background-color: #6c757d;">
    <svg viewBox="0 0 1200 1100" width="1200px" height="1100px" style="background-color: #6c757d;">
        {" ".join(svg_elements)}
    </svg>
</body></html>"""

with open("scratch/preview.html", "w") as f:
    f.write(svg_str)
print("Done")
