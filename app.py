import streamlit as st
from PIL import Image
import os
import json
import random

st.set_page_config(page_title="Mix & Match - Free", layout="wide")

UPLOAD_FOLDER = "items"
META_FILE = "items_meta.json"
CATEGORIES = ["Áo", "Quần", "Giày", "Phụ kiện"]
STYLES = ["casual", "sport", "streetwear"]

# Khởi tạo thư mục
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
for c in CATEGORIES:
    os.makedirs(os.path.join(UPLOAD_FOLDER, c), exist_ok=True)

# ========== META ==========
def load_meta():
    if not os.path.exists(META_FILE):
        return []
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_meta(meta):
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def add_item(path, category, style):
    meta = load_meta()
    meta = [m for m in meta if m.get("path") != path]
    meta.append({
        "path": path,
        "category": category,
        "style": style
    })
    save_meta(meta)

def load_items(style=None):
    meta = load_meta()
    items = {cat: [] for cat in CATEGORIES}

    for m in meta:
        if not os.path.exists(m["path"]):
            continue

        if style and m["style"] != style:
            continue

        items[m["category"]].append(m["path"])

    return items

# ========== UI ==========
page = st.sidebar.radio(
    "Chọn tính năng",
    ["Upload đồ", "Xem tủ đồ", "Gợi ý outfit"]
)

# ================= UPLOAD =================
if page == "Upload đồ":
    st.header("📤 Upload đồ mới")

    col1, col2 = st.columns(2)
    category = col1.selectbox("Loại trang phục", CATEGORIES)
    style = col2.selectbox("Phong cách", STYLES)

    file = st.file_uploader("Chọn ảnh trang phục", type=["png", "jpg", "jpeg"])

    if file:
        img = Image.open(file)
        path = os.path.join(UPLOAD_FOLDER, category, file.name)
        img.save(path)
        add_item(path, category, style)
        st.success("Đã thêm vào tủ đồ!")
        st.image(img, width=250)

# ================= TỦ ĐỒ =================
elif page == "Xem tủ đồ":
    st.header("👕 Tủ đồ của bạn")

    style_filter = st.selectbox(
        "Lọc theo phong cách",
        ["Tất cả"] + STYLES
    )

    if style_filter == "Tất cả":
        items = load_items()
    else:
        items = load_items(style_filter)

    for cat in CATEGORIES:
        st.subheader(cat)
        cols = st.columns(4)
        idx = 0

        for img_path in items[cat]:
            img = Image.open(img_path)
            cols[idx % 4].image(img, width=150)
            idx += 1

# ================= GỢI Ý OUTFIT =================
elif page == "Gợi ý outfit":
    st.header("🎨 Gợi ý outfit")

    style_choice = st.selectbox("Phong cách", STYLES)

    items = load_items(style_choice)
    fallback = load_items()

    outfit = {}

    for cat in CATEGORIES:
        if items[cat]:
            outfit[cat] = random.choice(items[cat])
        elif fallback[cat]:
            outfit[cat] = random.choice(fallback[cat])

    st.subheader("Outfit đề xuất")
    cols = st.columns(4)
    i = 0
    for cat, img_path in outfit.items():
        img = Image.open(img_path)
        cols[i].subheader(cat)
        cols[i].image(img, width=200)
        i += 1
