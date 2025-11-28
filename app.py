import streamlit as st
from PIL import Image
import os
import random

# --- SETUP ---
st.set_page_config(page_title="Mix & Match Clothes", layout="wide")

UPLOAD_FOLDER = "items"
CATEGORIES = ["Áo", "Quần", "Giày", "Phụ kiện"]

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
for c in CATEGORIES:
    os.makedirs(os.path.join(UPLOAD_FOLDER, c), exist_ok=True)


# --- SIDEBAR MENU ---
page = st.sidebar.radio("Chọn tính năng:", ["Upload đồ", "Xem tủ đồ", "Gợi ý outfit"])


# --- PAGE 1: UPLOAD ---
if page == "Upload đồ":
    st.header("📤 Upload đồ vào tủ")

    category = st.selectbox("Phân loại", CATEGORIES)
    file = st.file_uploader("Chọn ảnh trang phục", type=["png", "jpg", "jpeg"])

    if file:
        img = Image.open(file)
        save_path = os.path.join(UPLOAD_FOLDER, category, file.name)
        img.save(save_path)
        st.success("Đã lưu vào tủ đồ!")
        st.image(img, width=250)



# --- LẤY ITEM TỪ THƯ MỤC ---
def load_items():
    items = {}
    for cat in CATEGORIES:
        folder = os.path.join(UPLOAD_FOLDER, cat)
        files = [os.path.join(folder, f) for f in os.listdir(folder)]
        items[cat] = files
    return items


# --- PAGE 2: XEM TỦ ---
if page == "Xem tủ đồ":
    st.header("👕 Tủ đồ của bạn")

    items = load_items()
    for cat in CATEGORIES:
        st.subheader(f"### {cat}")
        cols = st.columns(4)
        for i, img_path in enumerate(items[cat]):
            try:
                img = Image.open(img_path)
                cols[i % 4].image(img, width=150)
            except:
                pass


# --- PAGE 3: GỢI Ý OUTFIT ---
if page == "Gợi ý outfit":
    st.header("🎨 Gợi ý outfit tự động")

    items = load_items()

    # Lấy ngẫu nhiên mỗi loại 1 item
    outfit = {}
    for cat in CATEGORIES:
        if items[cat]:
            outfit[cat] = random.choice(items[cat])

    # Hiển thị outfit
    cols = st.columns(4)
    idx = 0
    for cat, img_path in outfit.items():
        img = Image.open(img_path)
        cols[idx].subheader(cat)
        cols[idx].image(img, width=200)
        idx += 1

    if not outfit:
        st.warning("Bạn chưa có món đồ nào trong tủ!")
