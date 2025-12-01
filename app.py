import streamlit as st
from PIL import Image
import hashlib
import io
import random
import time

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import gspread


# ========================= CONFIG =========================
st.set_page_config(page_title="Mix & Match Closet", layout="wide")

CATEGORIES = ["Áo", "Quần", "Giày", "Phụ kiện"]
STYLES = ["casual", "sport", "streetwear"]


# ========================= HASH IMAGE (CHỐNG TRÙNG) =========================
def get_image_hash(img_bytes):
    return hashlib.sha256(img_bytes).hexdigest()


# ========================= GOOGLE DRIVE =========================
def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDIZHirc2vmjWqM\nSAorxmfvwhW1dsFnv/EADtSidanariWk7c823e+G/gNMLJspSxLz1FUplz9MK/aX\n09Z3vYGr5iMqp2750YDATzsQ8fJVdiY/RU6F4VJdoQDRO8o8V3wXfG5JPetBmrA2\nxa5EP9tLxVOmuq95mUTDydEioUZEYEu9Ai7SKFMYKjqSLkciqNcRTwLtay2FlTNK\nmd79Rc9dlpj7Uye1dOeUG2KUh8zA0I0W+ZLdIuX5mMciA26l2w5pD5PZX37Hy2b4\nAC3UIHLC6LhMDiVjQ3EkMPD117cuJwWigCypY+az+iHeSyUPb9azgeTB3hPrMAfp\npGUvw5yhAgMBAAECggEAE24efy1NWIj8vEZd6hmuSUKN3U76+MbVJNbLSkdTZVc+\nYiwGzACf8XxesHugvdPALjE34rT+F7IpklYhdPHEiXjijwe2DHYCYGMuTHnRL/Up\nRzg+oV+UH2z1idQcy1YGO7a+cM6WqYFItb7cI1T3u/SRpFh0nDs+vicq5osxp35s\nw8dNMo2tr+BPE1IL3IyLDtGxZIvwk31lJ6LjCYTjBGk/wvtCGiV3m09uYDI9+Kcz\npUGDrSF2GGnuLzhIAD6DIP8ohASkCBPge6wvPYA+jL9qdmAzmHt71JopgoaYmCV6\ngYKnqiNX6QJe2x9T3Nbrk7qE//hMG2IA4Tk/Yv9HiwKBgQDyRdYChCKMLNG5aFZc\ndquRI3rTDLkDb7eqmnBl+4Oj9OzvgGaexR5xrSKPztudTJCf+08ZRP5jdvKJrg4c\nDetBarESmWtZJhLPSUTloZfIevKwzh+AqLoWN1ReYENfPW/K/+oemNu7rqV6M6B0\ntEJcW3JFlNUD8ngrtmQri3Y45wKBgQDTvylk7uQl+RA7kD8fhhVrqayeAthueXRc\nRWa9x5Fccg8TfA0aZZGCnx6f58paZ1S427mVyfirSQTEpeox1vGzB1dp+jEEjDth\nQOyYmgKXBkaDVzsB7II2PbJT6UUtBockHY3PL5J/49yL47R1fbETqwbpJGbyX7ni\nUIiyKzwlNwKBgFScXylxzD74SCZgcgjIyRJfOb4La3Hvyk0isq5rMIZKO5VJWo2I\neiFpPfDLZZeB7eBxfCZvGgjSudGrn/HcSpUGFeFRA1SXH2qVRCKOVNwHVEq7MfVU\n9+haWnS7WcwhQLG8vp8A83yQeeo7rYYUjjiDF12FpP9D5wQdJs6uXhNxAoGBAJGa\nTJOMNbPq3P+oQ8+getBKn1kUKdFlkN72Fhz/wvPntng2gCgbmYBRfFSGpb2eekKX\nTLk0ZdsaXb3/PNhCrnbl4HUORnCTIS3R4B9bH9bLyOb9r6S2Bh/YMuzCZf/9EiaC\ncAX892cbv4ct7+QupvoYS6s7jdKygnad3DFvy27nAoGABMqCIuB+WDcbcIPk0LrB\nMuNuXKHkTDL4hvIRHFScD+i97cS7HnHG71XAvQIJeYhcSG5aqnc6Q0Y23BvtzW9L\nOkzIYYIyZrW2xrEPIRbsFAz/iE4Nu1C6sXV+/e58J1G3O+qNlLMLFubT6CFqgqYv\n9fhtomBdsWzkV3Bv1uY558o="],
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def upload_to_drive(image_bytes, filename, retry=2):
    drive = get_drive_service()
    folder_id = st.secrets["DRIVE_FOLDER_ID"]

    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype="image/png")

    for attempt in range(retry + 1):
        try:
            # Tạo metadata file Drive
            file_metadata = {"name": filename, "parents": [folder_id]}

            # Upload ảnh lên Drive
            uploaded = drive.files().create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()

            file_id = uploaded["id"]

            # Cho phép ai cũng xem (public)
            drive.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"}
            ).execute()

            # URL ảnh trực tiếp
            url = f"https://drive.google.com/uc?export=view&id={file_id}"
            return url

        except Exception as e:
            if attempt == retry:
                raise e
            time.sleep(1)  # retry


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
    rows = sh.get_all_values()
    return rows[1:]  # bỏ header


def load_items(style_filter=None):
    rows = load_all_metadata()
    items = {cat: [] for cat in CATEGORIES}

    for url, cat, style, h in rows:
        if style_filter and style != style_filter:
            continue
        items[cat].append(url)

    return items


# ========================= CHECK DUPLICATE IMAGE =========================
def is_duplicate_image(new_hash):
    rows = load_all_metadata()
    for url, cat, style, h in rows:
        if h == new_hash:
            return True, url
    return False, None


# ========================= UI =========================
page = st.sidebar.radio(
    "Chọn tính năng",
    ["Upload đồ", "Xem tủ đồ", "Gợi ý outfit"]
)


# ========================= PAGE: UPLOAD =========================
if page == "Upload đồ":
    st.header("📤 Thêm trang phục vào tủ (Lưu Google Drive)")

    col1, col2 = st.columns(2)
    category = col1.selectbox("Loại trang phục", CATEGORIES)
    style = col2.selectbox("Phong cách", STYLES)

    st.markdown("### 📸 Chụp ảnh bằng camera")
    camera_img = st.camera_input("Nhấn để chụp ảnh")

    st.markdown("### 📁 Upload ảnh từ máy")
    upload_img = st.file_uploader("Chọn ảnh", type=["png", "jpg", "jpeg"])

    img = None

    if camera_img:
        img = Image.open(camera_img)
    elif upload_img:
        img = Image.open(upload_img)

    if img:
        # Convert sang bytes
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        # Hash chống trùng
        img_hash = get_image_hash(img_bytes)

        # Kiểm tra trùng
        dup, old_url = is_duplicate_image(img_hash)

        if dup:
            st.warning("⚠ Ảnh này đã tồn tại trong tủ đồ!")
            st.image(old_url, caption="Ảnh đã lưu trước đó", width=250)

        else:
            filename = f"{category}_{style}_{random.randint(1000,9999)}.png"

            try:
                # Upload Drive
                url = upload_to_drive(img_bytes, filename)

                # Lưu metadata
                save_item_to_sheet(url, category, style, img_hash)

                st.success("✅ Đã lưu lên Google Drive!")
                st.image(url, width=250)

            except Exception as e:
                st.error(f"❌ Lỗi upload lên Drive: {e}")


# ========================= PAGE: XEM TỦ ĐỒ =========================
elif page == "Xem tủ đồ":
    st.header("👕 Tủ đồ của bạn")

    style_filter = st.selectbox("Lọc theo phong cách", ["Tất cả"] + STYLES)

    if style_filter == "Tất cả":
        items = load_items()
    else:
        items = load_items(style_filter)

    for cat in CATEGORIES:
        st.subheader(cat)
        cols = st.columns(4)
        i = 0
        for url in items[cat]:
            cols[i % 4].image(url, width=150)
            i += 1


# ========================= PAGE: GỢI Ý OUTFIT =========================
elif page == "Gợi ý outfit":
    st.header("🎨 Gợi ý Outfit")

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
