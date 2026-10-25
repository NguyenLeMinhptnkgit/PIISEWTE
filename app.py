import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import time
import random

# Thiết lập cấu hình trang Streamlit
st.set_page_config(
    page_title="Mô phỏng Nhà máy Điện rác EFGT",
    page_icon="⚡",
    layout="wide"
)

# ==========================================
# 1. MÔ HÌNH TÍNH TOÁN NHIỆT ĐỘNG HỌC (EFGT)
# ==========================================
def tinh_toan_nguoc_efgt(m_fuel_sec, lhv_kjkg=9500, eta_comb=0.82, pi_c=5.5, t1_c=25.0, t3_c=950.0):
    """
    Tính toán hiệu suất và công suất phát điện dựa trên lượng rác nạp vào
    """
    T1 = t1_c + 273.15
    T3 = t3_c + 273.15
    gamma = 1.4
    Cp = 1.005  # kJ/kg.K
    eta_c = 0.85
    eta_t = 0.88
    eta_mech = 0.98
    eta_gen = 0.96

    # Nhiệt lượng đầu vào từ lò đốt rác
    Q_in = m_fuel_sec * lhv_kjkg * eta_comb  # kW

    # Máy nén khí (Compressor)
    T2s = T1 * (pi_c ** ((gamma - 1) / gamma))
    T2 = T1 + (T2s - T1) / eta_c

    # Lưu lượng khí nạp ước tính
    m_dot = Q_in / (Cp * (T3 - T2)) if (T3 - T2) > 0 else 0.1

    # Tuabin khí (Turbine)
    T4s = T3 / (pi_c ** ((gamma - 1) / gamma))
    T4 = T3 - eta_t * (T3 - T4s)

    # Công suất
    W_c = m_dot * Cp * (T2 - T1)
    W_t = m_dot * Cp * (T3 - T4)
    W_net = (W_t - W_c) * eta_mech
    P_elec = max(0.0, W_net * eta_gen)

    # Hiệu suất tổng
    Q_fuel_total = m_fuel_sec * lhv_kjkg
    eta_plant = (P_elec / Q_fuel_total * 100) if Q_fuel_total > 0 else 0.0

    return {
        "P_elec": P_elec,
        "eta_plant": eta_plant,
        "T2_C": T2 - 273.15,
        "T4_C": T4 - 273.15,
        "m_dot": m_dot,
        "Q_in": Q_in
    }

# ==========================================
# 2. HÀM HIỂN THỊ SƠ ĐỒ SVG ĐỘNG CẬP NHẬT
# ==========================================
def render_efgt_diagram():
    svg_code = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 500" width="100%" height="100%" style="background-color: #ffffff; font-family: Arial, sans-serif;">
      <defs>
        <!-- Mũi tên đầu đường ống -->
        <marker id="arrow-black" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#000000"/>
        </marker>
        
        <!-- Hiệu ứng quay biểu tượng (+) trong khối đen -->
        <style>
          @keyframes spin-cw {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          .spinning-cross-compressor {
            animation: spin-cw 2.0s linear infinite;
            transform-origin: 0px 0px;
          }
          .spinning-cross-turbine {
            animation: spin-cw 1.2s linear infinite;
            transform-origin: 0px 0px;
          }
          .bold-text {
            font-weight: bold;
            fill: #000000;
            text-anchor: middle;
            dominant-baseline: middle;
          }
        </style>
      </defs>

      <!-- ==================== ĐƯỜNG ỐNG & TRỤC NỐI ==================== -->
      
      <!-- 1. Mũi tên Khí nạp đầu vào bên trái -->
      <line x1="120" y1="310" x2="230" y2="310" stroke="#000000" stroke-width="4" marker-end="url(#arrow-black)" />
      
      <!-- 2. Trục kết nối thẳng giữa Máy nén khí và Tuabin khí -->
      <line x1="330" y1="310" x2="580" y2="310" stroke="#000000" stroke-width="4" />

      <!-- 3. Máy nén khí -> Bộ HTHE Gián tiếp (Lên rồi qua phải) -->
      <path d="M 280 260 L 280 190 L 345 190" fill="none" stroke="#000000" stroke-width="4" stroke-linejoin="round" marker-end="url(#arrow-black)" />

      <!-- 4. Bộ HTHE Gián tiếp -> Tuabin khí (Qua phải rồi xuống) -->
      <path d="M 515 190 L 630 190 L 630 260" fill="none" stroke="#000000" stroke-width="4" stroke-linejoin="round" marker-end="url(#arrow-black)" />

      <!-- 5. Tuabin khí -> Lò đốt rác ngoài (Xuống rồi qua trái) -->
      <path d="M 630 360 L 630 420 L 520 420" fill="none" stroke="#000000" stroke-width="4" stroke-linejoin="round" marker-end="url(#arrow-black)" />

      <!-- 6. Bộ HTHE Gián tiếp -> Hệ thống lọc (Lên rồi qua trái) -->
      <path d="M 430 150 L 430 100 L 295 100" fill="none" stroke="#000000" stroke-width="4" stroke-linejoin="round" marker-end="url(#arrow-black)" />

      <!-- 7. Đường nét đứt màu cam (Lò đốt rác ngoài -> Bộ HTHE Gián tiếp) -->
      <line x1="430" y1="380" x2="430" y2="230" stroke="#e06d1b" stroke-width="3" stroke-dasharray="6,4" />

      <!-- ==================== NHÃN CHÚ THÍCH DÒNG KHÍ ==================== -->
      <text x="362" y="120" class="bold-text" font-size="15">Khói thải lò</text>
      <text x="575" y="445" class="bold-text" font-size="15">Khí sạch nóng</text>

      <!-- ==================== MÔ-ĐUN CÁC KHỐI ==================== -->

      <!-- 1. Hệ Thống lọc, thu giữ khí thải (Góc trên trái - Xanh lá chuối) -->
      <g>
        <rect x="115" y="60" width="180" height="80" rx="14" fill="#a8f048" />
        <text x="205" y="88" class="bold-text" font-size="15">Hệ Thống lọc,</text>
