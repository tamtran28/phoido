import streamlit as st
import hashlib
import io
import random

from PIL import Image

from google.oauth2 import service_account
import gspread

import cloudinary
import cloudinary.uploader


# =============== CONFIG STREAMLIT ===============
st.set_page_config(page_title="Phối đồ Cloud Closet", layout="wide")

CATEGORIES = ["Áo", "Quần", "Giày", "Phụ kiện"]
STYLES = ["casual", "sport", "streetwear"]

# =============== CONFIG GOOGLE SERVICE ACCOUNT ===============
service_info = {
    "type": st.secrets["type"],
    "project_id": st.secrets["project_id"],
    "private_key_id": st.secrets["private_key_id"],
    "private_key": st.secrets["private_key"],
    "client_email": st.secrets["client_email"],
    "client_id": st.secrets["client_id"],
    "token_uri": st.secrets["token_uri"],
    # mấy URL này Google dùng mặc định, mình hardcode luôn
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "universe_domain": "googleapis.com",
}

SHEET_ID = st.secrets["SHEET_ID"]

# =============== CONFIG CLOUDINARY ===============
cloudinary.config(
    cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key=st.secrets["CLOUDINARY_API_KEY"],
    api_secret=st.secrets["CLOUDINARY_API_SECRET"]
)


# =============== GOOGLE SHEETS HELPERS ===============
def get_sheet():
    creds = service_account.Credentials.from_service_account_info(
        service_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1


def load_all_metadata():
    sh = get_sheet()
    rows = sh.get_all_values()
    if len(rows) <= 1:
        return []
    return rows[1:]  # bỏ header


def save_item_to_sheet(url, category, style, img_hash):
    sh = get_sheet()
    sh.append_row([url, category, style, img_hash])


def load_items(style_filter=None):
    rows = load_all_metadata()
    items = {cat: [] for cat in CATEGORIES}
    for row in rows:
        # đảm bảo row đủ 4 cột
        if len(row) < 4:
            continue
        url, cat, style, h = row
        if cat not in items:
            continue
        if style_filter and style != style_filter:
            continue
        items[cat].append(url)
    return items


# =============== CLOUDINARY HELPERS ===============
def upload_to_cloudinary(img_bytes):
    try:
        result = cloudinary.uploader.upload(
            img_bytes,
            folder="phoido_app",
            resource_type="image"
        )
        return result["secure_url"]
    except Exception as e:
        st.error(f"❌ Lỗi Cloudinary: {e}")
        return None


# =============== IMAGE HASH / DUPLICATE ===============
def get_image_hash(img_bytes):
    return hashlib.sha256(img_bytes).hexdigest()


def is_duplicate_image(new_hash):
    rows = load_all_metadata()
    for row in rows:
        if len(row) < 4:
            continue
        url, cat, style, h = row
        if h == new_hash:
            return True, url
    return False, None


# =============== UI ===============
st.sidebar.title("👗 Phối đồ Closet")
page = st.sidebar.radio(
    "Chọn chức năng",
    ["Upload đồ", "Xem tủ đồ", "Gợi ý outfit"]
)


# =============== PAGE: UPLOAD ĐỒ ===============
if page == "Upload đồ":
    st.header("📤 Thêm trang phục vào tủ (Cloudinary + Google Sheet)")

    col1, col2 = st.columns(2)
    category = col1.selectbox("Loại trang phục", CATEGORIES)
    style = col2.selectbox("Phong cách", STYLES)

    st.markdown("### 📸 Chụp ảnh bằng camera")
    camera_img = st.camera_input("Nhấn để chụp ảnh")

    st.markdown("### 📁 Hoặc upload ảnh từ máy")
    upload_img = st.file_uploader("Chọn ảnh", type=["png", "jpg", "jpeg"])

    img = None
    img_bytes = None

    if camera_img is not None:
        img_bytes = camera_img.getvalue()
        img = Image.open(io.BytesIO(img_bytes))
    elif upload_img is not None:
        img_bytes = upload_img.read()
        img = Image.open(io.BytesIO(img_bytes))

    if img is not None:
        st.subheader("Ảnh xem trước")
        st.image(img, width=300)

        if st.button("Lưu vào tủ đồ"):
            # chuẩn hóa ảnh sang PNG để hash cho ổn định
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            norm_bytes = buf.getvalue()

            img_hash = get_image_hash(norm_bytes)

            dup, old_url = is_duplicate_image(img_hash)
            if dup:
                st.warning("⚠ Ảnh này đã tồn tại trong tủ đồ!")
                st.image(old_url, width=250)
            else:
                st.info("⏳ Đang upload ảnh lên Cloudinary...")
                url = upload_to_cloudinary(norm_bytes)
                if url:
                    save_item_to_sheet(url, category, style, img_hash)
                    st.success("🎉 Đã lưu thành công!")
                    st.image(url, width=250)
                else:
                    st.error("❌ Upload thất bại. Hãy thử lại.")


# =============== PAGE: XEM TỦ ĐỒ ===============
elif page == "Xem tủ đồ":
    st.header("👕 Tủ đồ của bạn")

    style_filter = st.selectbox("Lọc theo phong cách", ["Tất cả"] + STYLES)

    if style_filter == "Tất cả":
        items = load_items()
    else:
        items = load_items(style_filter)

    for cat in CATEGORIES:
        st.subheader(cat)
        urls = items.get(cat, [])
        if not urls:
            st.caption("Chưa có món nào")
            continue
        cols = st.columns(4)
        for i, url in enumerate(urls):
            cols[i % 4].image(url, width=150)


# =============== PAGE: GỢI Ý OUTFIT ===============
elif page == "Gợi ý outfit":
    st.header("🎨 Gợi ý outfit")

    style_choice = st.selectbox("Chọn phong cách", STYLES)

    items_by_style = load_items(style_choice)
    fallback_items = load_items()

    outfit = {}

    for cat in CATEGORIES:
        if items_by_style.get(cat):
            outfit[cat] = random.choice(items_by_style[cat])
        elif fallback_items.get(cat):
            outfit[cat] = random.choice(fallback_items[cat])

    if not outfit:
        st.warning("Tủ đồ đang trống. Hãy upload vài món trước đã nhé!")
    else:
        cols = st.columns(4)
        for i, cat in enumerate(CATEGORIES):
            cols[i].subheader(cat)
            if cat in outfit:
                cols[i].image(outfit[cat], width=200)
            else:
                cols[i].caption("Chưa có món để gợi ý")
