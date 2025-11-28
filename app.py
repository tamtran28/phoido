import streamlit as st
from PIL import Image
import hashlib
import io
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import gspread
import time

# ========================= CONFIG =========================
st.set_page_config(page_title="Mix & Match Anti-Duplicate", layout="wide")

CATEGORIES = ["Áo", "Quần", "Giày", "Phụ kiện"]
STYLES = ["casual", "sport", "streetwear"]


# ========================= UTIL: TÍNH HASH ẢNH =========================
def get_image_hash(img_bytes):
    return hashlib.sha256(img_bytes).hexdigest()


# ========================= GOOGLE DRIVE =========================
def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"],
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def upload_to_drive(image_bytes, filename, retry=2):
    drive = get_drive_service()
    folder_id = st.secrets["DRIVE_FOLDER_ID"]

    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype="image/png")

    for attempt in range(retry + 1):
        try:
            file_metadata = {
                "name": filename,
                "parents": [folder_id]
            }

            file = drive.files().create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()

            file_id = file["id"]

            # Make public
            drive.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"}
            ).execute()

            url = f"https://drive.google.com/uc?export=view&id={file_id}"
            return url

        except Exception as e:
            if attempt == retry:
                raise e
            time.sleep(1)  # đợi 1 giây rồi thử lại


# ========================= GOOGLE SHEETS =========================
def get_sheet():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["SHEET_ID"]).sheet1


def save_item_to_sheet(url, category, style, img_hash):
    sh = get_sheet()
    sh.append_row([url, category, style, img_hash])


def load_all_metadata():
    sh = get_sheet()
    rows = sh.get_all_values()[1:]  # bỏ header
    return rows


def load_items(style_filter=None):
    rows = load_all_metadata()
    items = {cat: [] for cat in CATEGORIES}

    for url, cat, style, img_hash in rows:
        if style_filter and style != style_filter:
            continue
        items[cat].append(url)

    return items


# ========================= CHECK DUPLICATE =========================
def is_duplicate_image(img_hash):
    rows = load_all_metadata()
    for url, cat, style, h in rows:
        if h == img_hash:
            return True, url
    return False, None


# ========================= UI =========================
page = st.sidebar.radio(
    "Chọn tính năng",
    ["Upload đồ", "Xem tủ đồ", "Gợi ý outfit"]
)


# ========================= PAGE: UPLOAD =========================
if page == "Upload đồ":
    st.header("📤 Upload hoặc chụp ảnh (anti-duplicate)")

    col1, col2 = st.columns(2)
    category = col1.selectbox("Loại trang phục", CATEGORIES)
    style = col2.selectbox("Phong cách", STYLES)

    st.markdown("### 📸 Chụp ảnh từ camera")
    camera_img = st.camera_input("Nhấn để chụp ảnh")

    st.markdown("### 📁 Hoặc upload file từ máy")
    file_img = st.file_uploader("Chọn ảnh", type=["jpg", "jpeg", "png"])

    img = None

    if camera_img:
        img = Image.open(camera_img)
    elif file_img:
        img = Image.open(file_img)

    if img:
        # Convert ảnh sang bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        img_hash = get_image_hash(img_bytes)

        # ========== CHỐNG TRÙNG ẢNH ==========
        duplicate, url = is_duplicate_image(img_hash)

        if duplicate:
            st.warning("⚠ Ảnh này đã tồn tại trong hệ thống!")
            st.image(url, caption="Ảnh đã lưu trước đó", width=250)
        else:
            # ========== UPLOAD LÊN DRIVE ==========
            filename = f"{category}_{style}_{random.randint(1000,9999)}.png"

            try:
                file_url = upload_to_drive(img_bytes, filename)
                save_item_to_sheet(file_url, category, style, img_hash)

                st.success("✅ Đã lưu vào Google Drive!")
                st.image(file_url, width=250)

            except Exception as e:
                st.error(f"❌ Lỗi upload lên Google Drive: {e}")


# ========================= PAGE: XEM TỦ =========================
elif page == "Xem tủ đồ":
    st.header("👕 Tủ đồ của bạn")

    style_filter = st.selectbox("Lọc theo phong cách", ["Tất cả"] + STYLES)

    if style_filter == "Tất cả":
        items = load_items()
    else:
        items = load_items(style_filter)

    for cat in CATEGORIES:
        st.subheader(f"### {cat}")
        cols = st.columns(4)
        idx = 0

        for url in items[cat]:
            cols[idx % 4].image(url, width=150)
            idx += 1


# ========================= PAGE: GỢI Ý OUTFIT =========================
elif page == "Gợi ý outfit":
    st.header("🎨 Gợi ý Outfit theo phong cách")

    style_choice = st.selectbox("Chọn phong cách", STYLES)

    items = load_items(style_choice)
    fallback = load_items()

    outfit = {}

    for cat in CATEGORIES:
        if items[cat]:
            outfit[cat] = random.choice(items[cat])
        elif fallback[cat]:
            outfit[cat] = random.choice(fallback[cat])

    cols = st.columns(4)
    i = 0
    for cat, url in outfit.items():
        cols[i].subheader(cat)
        cols[i].image(url, width=200)
        i += 1

# import streamlit as st
# from PIL import Image
# import os
# import json
# import random

# st.set_page_config(page_title="Mix & Match - Free", layout="wide")

# UPLOAD_FOLDER = "items"
# META_FILE = "items_meta.json"
# CATEGORIES = ["Áo", "Quần", "Giày", "Phụ kiện"]
# STYLES = ["casual", "sport", "streetwear"]

# # Khởi tạo thư mục
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# for c in CATEGORIES:
#     os.makedirs(os.path.join(UPLOAD_FOLDER, c), exist_ok=True)

# # ========== META ==========
# def load_meta():
#     if not os.path.exists(META_FILE):
#         return []
#     try:
#         with open(META_FILE, "r", encoding="utf-8") as f:
#             return json.load(f)
#     except:
#         return []

# def save_meta(meta):
#     with open(META_FILE, "w", encoding="utf-8") as f:
#         json.dump(meta, f, ensure_ascii=False, indent=2)

# def add_item(path, category, style):
#     meta = load_meta()
#     meta = [m for m in meta if m.get("path") != path]
#     meta.append({
#         "path": path,
#         "category": category,
#         "style": style
#     })
#     save_meta(meta)

# def load_items(style=None):
#     meta = load_meta()
#     items = {cat: [] for cat in CATEGORIES}

#     for m in meta:
#         if not os.path.exists(m["path"]):
#             continue

#         if style and m["style"] != style:
#             continue

#         items[m["category"]].append(m["path"])

#     return items

# # ========== UI ==========
# page = st.sidebar.radio(
#     "Chọn tính năng",
#     ["Upload đồ", "Xem tủ đồ", "Gợi ý outfit"]
# )

# # ================= UPLOAD =================
# if page == "Upload đồ":
#     st.header("📤 Upload đồ mới")

#     col1, col2 = st.columns(2)
#     category = col1.selectbox("Loại trang phục", CATEGORIES)
#     style = col2.selectbox("Phong cách", STYLES)

#     file = st.file_uploader("Chọn ảnh trang phục", type=["png", "jpg", "jpeg"])

#     if file:
#         img = Image.open(file)
#         path = os.path.join(UPLOAD_FOLDER, category, file.name)
#         img.save(path)
#         add_item(path, category, style)
#         st.success("Đã thêm vào tủ đồ!")
#         st.image(img, width=250)

# # ================= TỦ ĐỒ =================
# elif page == "Xem tủ đồ":
#     st.header("👕 Tủ đồ của bạn")

#     style_filter = st.selectbox(
#         "Lọc theo phong cách",
#         ["Tất cả"] + STYLES
#     )

#     if style_filter == "Tất cả":
#         items = load_items()
#     else:
#         items = load_items(style_filter)

#     for cat in CATEGORIES:
#         st.subheader(cat)
#         cols = st.columns(4)
#         idx = 0

#         for img_path in items[cat]:
#             img = Image.open(img_path)
#             cols[idx % 4].image(img, width=150)
#             idx += 1

# # ================= GỢI Ý OUTFIT =================
# elif page == "Gợi ý outfit":
#     st.header("🎨 Gợi ý outfit")

#     style_choice = st.selectbox("Phong cách", STYLES)

#     items = load_items(style_choice)
#     fallback = load_items()

#     outfit = {}

#     for cat in CATEGORIES:
#         if items[cat]:
#             outfit[cat] = random.choice(items[cat])
#         elif fallback[cat]:
#             outfit[cat] = random.choice(fallback[cat])

#     st.subheader("Outfit đề xuất")
#     cols = st.columns(4)
#     i = 0
#     for cat, img_path in outfit.items():
#         img = Image.open(img_path)
#         cols[i].subheader(cat)
#         cols[i].image(img, width=200)
#         i += 1
