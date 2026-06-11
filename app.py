import sys
import subprocess

# --- BỘ TỰ ĐỘNG KIỂM TRA VÀ CÀI ĐẶT THƯ VIỆN NẰM TRONG APP.PY ---
required_libraries = {
    "pandas": "pandas",
    "openpyxl": "openpyxl",
    "PIL": "Pillow",
    "requests": "requests"
}

for module_name, pip_name in required_libraries.items():
    try:
        __import__(module_name)
    except ImportError:
        # Nếu thiết bị hoặc đám mây thiếu thư viện, code sẽ tự cài ngay lập tức
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])

# --- SAU KHI ĐẢM BẢO ĐỦ THƯ VIỆN, TIẾN HÀNH CHẠY ỨNG DỤNG ---
import streamlit as st
import pandas as pd
from PIL import Image
import os

# 1. Cấu hình giao diện trang web
st.set_page_config(
    page_title="Dữ Liệu Mẫu Xét Nghiệm",
    page_icon="logo.png",
    layout="wide"
)



# Đường dẫn Google Sheet gốc của bạn
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/17IJKbyYH7e3EoOLPdrWdpXZQjkPG66V_tYxQ6HSBnmo/edit?usp=sharing"

# Sử dụng st.cache_resource để tối ưu hiệu năng đọc luồng file từ Google Sheets
@st.cache_resource(ttl=60)
def load_data_from_google_sheets(url):
    sheet_id = url.split("/d/")[1].split("/")[0]
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    excel_file = pd.ExcelFile(export_url)
    return excel_file

st.title("Tra Cứu Dữ Liệu Mẫu")
st.write("")

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
    with st.spinner("🔄 Đang đồng bộ dữ liệu từ Google Sheets..."):
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
        
        # [CẢI TIẾN]: Chỉ ẩn những cột trống nằm NGOÀI phạm vi quy tắc của bạn
        # Chuyển các chuỗi trống rác thành dạng NaN để xử lý chuẩn xác
        df_check = df_rule.replace(["-", "", "nan", "NaN"], None)
        
        # Duyệt qua các cột, nếu cột nào trống 100% HOÀN TOÀN từ đầu đến cuối thì mới ẩn
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
        
        # 🔎 THANH CÔNG CỤ TÌM KIẾM TỔNG HỢP (HỖ TRỢ ĐA TỪ KHÓA)
        search_query = st.text_input(
            "🔍 Nhập các từ khóa tìm kiếm (cách nhau bằng dấu cách):", 
            placeholder="Ví dụ: 'toxocara pos', '7438 pos', 'hpv 16'..."
        )
        
        df_filtered = df_data.copy()
        
        # [ĐÃ SỬA LỖI] Ép kiểu an toàn từng ô sang chuỗi str(x) để loại bỏ hoàn toàn lỗi float/NaN khi nối dòng
        if search_query:
            keywords = [kw.strip().lower() for kw in search_query.split() if kw.strip()]
            
            if keywords:
                # Sử dụng List Comprehension ép kiểu str(x) cho từng ô trên từng dòng
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
            
            # Thống kê số lượng theo thời gian thực (Real-time Metrics)
            with st.expander("📊 Thống kê nhanh số lượng mẫu đang hiển thị", expanded=True):
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
        
        # Nút xuất file dữ liệu đã lọc ra CSV
        if not df_filtered.empty:
            csv_data = df_filtered.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"📥 Tải danh sách kết quả tìm kiếm này",
                data=csv_data,
                file_name=f"Live_Search_Filtered.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ Không tìm thấy mẫu nào khớp với các từ khóa tìm kiếm của bạn.")
            
except Exception as e:
    st.error(f"❌ Không thể kết nối hoặc đọc dữ liệu từ Google Sheets: {e}")
