import streamlit as st
import hashlib
import json
from google.oauth2 import service_account
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from googleapiclient.errors import HttpError
from PIL import Image
import io
import base64

# ========================= CONFIG =========================
DRIVE_FOLDER_ID = st.secrets["DRIVE_FOLDER_ID"]
SHEET_ID = st.secrets["SHEET_ID"]

# Đọc JSON từ secrets → parse lại thành dict
service_info = {
    "type": st.secrets["type"],
    "project_id": st.secrets["project_id"],
    "private_key_id": st.secrets["private_key_id"],
    "private_key": st.secrets["private_key"],
    "client_email": st.secrets["client_email"],
    "client_id": st.secrets["client_id"],
    "token_uri": st.secrets["token_uri"],
}

creds = service_account.Credentials.from_service_account_info(
    service_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
)


# ========================= GOOGLE SHEETS =========================
def get_sheet():
    creds = service_account.Credentials.from_service_account_info(
        service_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

# ========================= GOOGLE DRIVE =========================
def upload_to_drive(filename, img_bytes):
    try:
        creds = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = build("drive", "v3", credentials=creds)

        file_metadata = {
            "name": filename,
            "parents": [DRIVE_FOLDER_ID]
        }

        media = MediaInMemoryUpload(img_bytes, mimetype="image/jpeg")

        up = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        file_id = up.get("id")
        return f"https://drive.google.com/uc?id={file_id}"
    except HttpError as e:
        st.error(f"Upload lỗi: {e}")
        return None

# ========================= HASH IMAGE =========================
def get_image_hash(img_bytes):
    return hashlib.sha256(img_bytes).hexdigest()

# ========================= LOAD METADATA =========================
def load_all_metadata():
    sh = get_sheet()
    rows = sh.get_all_values()
    return rows[1:]  # bỏ header

# ========================= CHECK DUPLICATE =========================
def is_duplicate_image(new_hash):
    rows = load_all_metadata()
    for row in rows:
        url, cat, style, h = row
        if h == new_hash:
            return True, url
    return False, None

# ========================= SAVE METADATA =========================
def save_metadata(url, category, style, img_hash):
    sh = get_sheet()
    sh.append_row([url, category, style, img_hash])

# ========================= UI =========================
st.title("👕 AI Phối Đồ – Lưu Tủ Đồ Google Drive + Sheet")
st.write("Upload ảnh quần áo, tự động lưu vào Google Drive + Google Sheet, chống trùng ảnh.")

option = st.selectbox("Chọn loại nhập ảnh:", ["📁 Upload file", "📸 Camera"])

img_data = None

if option == "📁 Upload file":
    uploaded = st.file_uploader("Chọn ảnh", type=["jpg", "jpeg", "png"])
    if uploaded:
        img_data = uploaded.read()

if option == "📸 Camera":
    cam = st.camera_input("Chụp ảnh")
    if cam:
        img_data = cam.getvalue()

if img_data:
    st.image(img_data, caption="Ảnh bạn vừa chọn", use_container_width=True)

    category = st.selectbox("Loại item:", ["top", "bottom", "shoes", "outer"])
    style = st.selectbox("Phong cách:", ["casual", "sport", "streetwear", "minimal", "korean"])

    if st.button("Lưu vào tủ đồ"):
        img_hash = get_image_hash(img_data)

        # Check duplicate
        dup, old_url = is_duplicate_image(img_hash)
        if dup:
            st.warning(f"⚠ Ảnh này đã tồn tại trong tủ đồ!\nLink ảnh cũ: {old_url}")

        else:
            filename = f"{category}_{style}_{img_hash[:10]}.jpg"
            url = upload_to_drive(filename, img_data)

            if url:
                save_metadata(url, category, style, img_hash)
                st.success("✅ Đã lưu thành công!")
                st.write("Link ảnh trên Drive:")
                st.code(url)

# ========================= GỢI Ý OUTFIT =========================
st.header("👗 Gợi ý outfit theo phong cách")
chosen_style = st.selectbox("Chọn style muốn phối:", 
                            ["casual", "sport", "streetwear", "minimal", "korean"])

if st.button("Gợi ý outfit"):
    if chosen_style == "casual":
        st.info("👕 Áo thun basic + 👖 quần jean + 👟 sneaker trắng")
    elif chosen_style == "sport":
        st.info("🏃 Áo thể thao + quần short training + giày chạy bộ")
    elif chosen_style == "streetwear":
        st.info("🧥 Hoodie oversize + jean rách + giày chunky")
    elif chosen_style == "minimal":
        st.info("🧶 Áo polo + quần tây slimfit + giày lười trắng")
    elif chosen_style == "korean":
        st.info("🧣 Áo sweater + sơ mi bên trong + quần baggy + giày cổ thấp")
