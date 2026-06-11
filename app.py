import streamlit as st
import pandas as pd
from PIL import Image
import os

# 1. Cấu hình giao diện trang web (Bật lại logo.png)
st.set_page_config(
    page_title="Dữ Liệu Mẫu Xét Nghiệm",
    page_icon="logo.png",
    layout="wide"
)

# --- KHỞI TẠO TRẠNG THÁI ĐĂNG NHẬP (PASSWORD PROTECTION) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Hàm kiểm tra mật khẩu
def check_password():
    if st.session_state["password_input"] == "khoathuongrd":
        st.session_state["authenticated"] = True
        st.session_state["password_error"] = False
    else:
        st.session_state["authenticated"] = False
        st.session_state["password_error"] = True

# Giao diện màn hình khóa (Nếu chưa đăng nhập thành công)
if not st.session_state["authenticated"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info("HỆ THỐNG NỘI BỘ KHOA THƯƠNG R&D")
        st.subheader("Vui lòng nhập mật khẩu để truy cập dữ liệu:")
        
        # Ô nhập mật khẩu ẩn ký tự
        st.text_input(
            "Mật khẩu:", 
            type="password", 
            key="password_input", 
            on_change=check_password,
            placeholder="Nhập mật khẩu vào đây và ấn Enter..."
        )
        
        # Báo lỗi nếu gõ sai
        if st.session_state.get("password_error", False):
            st.error("Mật khẩu không chính xác. Vui lòng thử lại!")
            
    st.stop() # Dừng toàn bộ code phía dưới lại, không cho load dữ liệu khi chưa qua cửa khẩu

# ------------------------------------------------------------------
# ĐÃ ĐĂNG NHẬP THÀNH CÔNG -> TOÀN BỘ LOGIC DƯỚI ĐÂY SẼ ĐƯỢC THỰC THI
# ------------------------------------------------------------------

# Đường dẫn Google Sheet gốc của bạn
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/17IJKbyYH7e3EoOLPdrWdpXZQjkPG66V_tYxQ6HSBnmo/edit?usp=sharing"

# Sử dụng st.cache_resource để tối ưu hiệu năng đọc luồng file từ Google Sheets
@st.cache_resource(ttl=60)
def load_data_from_google_sheets(url):
    sheet_id = url.split("/d/")[1].split("/")[0]
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    excel_file = pd.ExcelFile(export_url)
    return excel_file

# Tiêu đề chính và nút Đăng xuất cấu hình thẩm mỹ
col_title, col_logout = st.columns([6, 1])
with col_title:
    st.title("Tra Cứu Dữ Liệu Mẫu")
with col_logout:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Đăng xuất", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

st.write("---")

# Hàm phân loại thông minh cho cột Kết luận
def phan_loai_ket_luan(val):
    val_str = str(val).strip().lower()
    if pd.isna(val) or val_str == "" or val_str == "-" or val_str == "nan":
        return "Unknown"
    elif "neg" in val_str or "âm" in val_str:
        return "Âm tính"
    elif "pos" in val_str or "dương" in val_str:
        return "Dương tính"
    elif "gz" in val_str or "nghi ngờ" in val_str:
        return "Nghi ngờ"
    else:
        return "Unknown"

try:
    with st.spinner("Đang đồng bộ dữ liệu từ Google Sheets..."):
        excel_file = load_data_from_google_sheets(GOOGLE_SHEET_URL)
    
    all_sheets = excel_file.sheet_names
    
    rule_sheet_name = next((s for s in all_sheets if s.lower() == 'rule'), None)
    pathogen_sheets = [s for s in all_sheets if s.lower() != 'rule']

    # --- THANH ĐIỀU HƯỚNG SIDEBAR ---
    st.sidebar.header("DANH MỤC TRA CỨU")
    menu_options = []
    if rule_sheet_name:
        menu_options.append("Quy tắc Coding (Rule)")
    if pathogen_sheets:
        menu_options.append("Danh sách tác nhân gây bệnh")
        
    main_choice = st.sidebar.radio("Chọn phân hệ:", menu_options)

    # ----------------------------------------------------
    # PHÂN HỆ 1: QUY TẮC CODING (Rule)
    # ----------------------------------------------------
    if "Quy tắc Coding" in main_choice:
        st.header(f"Bảng Tra Cứu Quy Tắc Coding (`{rule_sheet_name}`)")
        
        # Đọc dữ liệu từ sheet Rule
        df_rule = pd.read_excel(excel_file, sheet_name=rule_sheet_name)
        df_rule = df_rule.dropna(how='all') # Loại bỏ các dòng trống hoàn toàn
        
        # Chuyển rác thành None để kiểm tra, chỉ ẩn những cột trống 100%
        df_check = df_rule.replace(["-", "", "nan", "NaN"], None)
        cols_to_keep = [col for col in df_rule.columns if not df_check[col].isna().all()]
        df_rule_visible = df_rule[cols_to_keep]
        
        # Hộp chọn lọc nhanh theo danh mục ở Cột đầu tiên (nếu có dữ liệu)
        if len(df_rule_visible.columns) > 0:
            first_column = df_rule_visible.columns[0]
            categories = ["Tất cả danh mục"] + list(df_rule_visible[first_column].dropna().unique())
            selected_cat = st.selectbox(f"Lọc nhanh theo {first_column}:", categories)
            
            if selected_cat != "Tất cả danh mục":
                df_rule_visible = df_rule_visible[df_rule_visible[first_column] == selected_cat]
        
        # Hiển thị bảng quy tắc coding rộng rãi lên giao diện
        st.dataframe(df_rule_visible, use_container_width=True, hide_index=True)
        st.caption(f"Tổng số dòng quy tắc hệ thống ghi nhận: {len(df_rule_visible)}")

    # ----------------------------------------------------
    # PHÂN HỆ 2: TRA CỨU MẪU THEO TÁC NHÂN
    # ----------------------------------------------------
    elif "Danh sách tác nhân gây bệnh" in main_choice:
        st.header("")
        
        pathogen_options = ["Tất cả tác nhân"] + pathogen_sheets
        selected_pathogen = st.sidebar.selectbox("Chọn tác nhân / Sheet dữ liệu:", pathogen_options)
        
        all_data_list = []
        
        # Đọc dữ liệu từ nguồn
        if selected_pathogen == "Tất cả tác nhân":
            st.subheader("Dữ liệu mẫu: Gom toàn bộ các tác nhân gây bệnh")
            for sheet in pathogen_sheets:
                df_sheet = pd.read_excel(excel_file, sheet_name=sheet)
                df_sheet = df_sheet.dropna(how='all')
                if not df_sheet.empty:
                    df_sheet.insert(0, "Tác nhân nguồn", sheet)
                    all_data_list.append(df_sheet)
            
            if all_data_list:
                df_data = pd.concat(all_data_list, axis=0, ignore_index=True, sort=False)
            else:
                df_data = pd.DataFrame()
        else:
            st.subheader(f"Dữ liệu mẫu: Tác nhân {selected_pathogen}")
            df_data = pd.read_excel(excel_file, sheet_name=selected_pathogen)
            df_data = df_data.dropna(how='all')
        
        # Thanh tìm kiếm tổng hợp (Đã bỏ emoji kính lúp)
        search_query = st.text_input(
            "Nhập các từ khóa tìm kiếm (cách nhau bằng dấu cách):", 
            placeholder="Ví dụ: 'toxocara pos', '7438 pos', 'hpv 16'..."
        )
        
        df_filtered = df_data.copy()
        
        # Lọc chuỗi an toàn chống lỗi ép kiểu dữ liệu hỗn hợp float/NaN
        if search_query:
            keywords = [kw.strip().lower() for kw in search_query.split() if kw.strip()]
            
            if keywords:
                combined_text_series = df_filtered.apply(
                    lambda row: " ".join([str(x) for x in row]).lower(), 
                    axis=1
                )
                
                final_mask = pd.Series(True, index=df_filtered.index)
                for kw in keywords:
                    final_mask = final_mask & combined_text_series.str.contains(kw, regex=False)
                
                df_filtered = df_filtered[final_mask]
            
        # Thực hiện lọc theo phân loại nhóm Kết quả
        if 'Kết luận' in df_filtered.columns:
            df_filtered['_PhanLoaiTmp'] = df_filtered['Kết luận'].apply(phan_loai_ket_luan)
            
            col1, col2 = st.columns([2, 5])
            with col1:
                status_options = ["Tất cả kết quả", "Dương tính", "Âm tính", "Nghi ngờ", "Unknown"]
                status_choice = st.selectbox("Bộ lọc nhanh nhóm kết quả:", status_options)
                
                if status_choice != "Tất cả kết quả":
                    df_filtered = df_filtered[df_filtered['_PhanLoaiTmp'] == status_choice]
            
            # Thống kê số lượng (Đã dọn sạch các chấm tròn màu sắc rườm rà)
            with st.expander("Thống kê nhanh số lượng mẫu đang hiển thị", expanded=True):
                m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
                m_col1.metric("Tổng số mẫu hiển thị", f"{len(df_filtered)} / {len(df_data)}")
                m_col2.metric("🟢 Dương tính", f"{len(df_filtered[df_filtered['_PhanLoaiTmp']=='Dương tính'])}")
                m_col3.metric("⚪ Âm tính", f"{len(df_filtered[df_filtered['_PhanLoaiTmp']=='Âm tính'])}")
                m_col4.metric("🟡 Nghi ngờ", f"{len(df_filtered[df_filtered['_PhanLoaiTmp']=='Nghi ngờ'])}")
                m_col5.metric("🔴 Unknown", f"{len(df_filtered[df_filtered['_PhanLoaiTmp']=='Unknown'])}")

            df_filtered = df_filtered.drop(columns=['_PhanLoaiTmp'])

        # TỰ ĐỘNG ẨN CỘT TRỐNG (Giữ giao diện gọn gàng)
        if not df_filtered.empty:
            df_cleaned_cols = df_filtered.replace(["-", "", "nan", "NaN"], None)
            empty_columns = df_cleaned_cols.columns[df_cleaned_cols.isna().all()]
            df_filtered = df_filtered.drop(columns=empty_columns)

        # Hiển thị bảng kết quả tra cứu sạch đẹp
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        
        # Nút xuất file dữ liệu đã lọc ra CSV (Đã bỏ emoji tải về)
        if not df_filtered.empty:
            csv_data = df_filtered.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"Tải danh sách kết quả tìm kiếm này",
                data=csv_data,
                file_name=f"Live_Search_Filtered.csv",
                mime="text/csv"
            )
        else:
            st.warning("Không tìm thấy mẫu nào khớp với các từ khóa tìm kiếm của bạn.")
            
except Exception as e:
    st.error(f"Không thể kết nối hoặc đọc dữ liệu từ Google Sheets: {e}")
