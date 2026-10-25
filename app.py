import time
import random
import math
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Cấu hình trang web rộng
st.set_page_config(
    page_title="Mô phỏng Hệ thống EFGT",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS TỐI ƯU GIAO DIỆN CANVA & HIGHLIGHT HỘP GIÁ TRỊ METRIC ---
st.markdown("""
<style>
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    .main-title {
        text-align: center;
        color: #38bdf8;
        font-family: sans-serif;
        font-size: 18px !important;
        font-weight: bold;
        margin-bottom: 8px !important;
    }
    
    /* TẠO HỘP BO TRÒN VÀ VIỀN NỔI BẬT CHO 4 Ô GIÁ TRỊ METRIC */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
        border: 1.5px solid #38bdf8 !important;
        border-radius: 10px !important;
        padding: 6px 8px !important;
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2) !important;
        text-align: center !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 14px !important;
        font-weight: bold !important;
        color: #38bdf8 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 11px !important;
        font-weight: 600 !important;
        color: #cbd5e1 !important;
    }
    
    div.stButton > button {
        padding: 2px 10px !important;
        font-size: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- KHỐI TOÁN HỌC NHIỆT ĐỘNG ---
def tinh_toan_nguoc_efgt(m_fuel_sec):
    LHV_rac = 9500        # kJ/kg
    eta_comb = 0.82       # Hiệu suất buồng đốt
    Cp = 1.005            # kJ/kg.K
    T1 = 25 + 273.15      # K
    pi_c = 5.5            # Tỉ số nén
    eta_c, eta_t = 0.78, 0.82
    k = 1.4
    dp_HTHE = 0.03
    HIEU_SUAT_MAY_PHAT = 0.95
    TY_LE_DIEN_TU_TRI = 0.06
    P_ATM = 1.013         # bar

    Q_fuel = m_fuel_sec * LHV_rac
    Q_in = Q_fuel * eta_comb

    T2s = T1 * (pi_c ** ((k - 1) / k))
    T2 = T1 + (T2s - T1) / eta_c
    T3 = 950 + 273.15

    delta_T = T3 - T2
    if delta_T <= 0:
        return 0.0, 0.0, 0.0

    m_dot_real = Q_in / (Cp * delta_T)

    P2 = P_ATM * pi_c
    P3 = P2 * (1 - dp_HTHE)
    T4s = T3 * ((P_ATM / P3) ** ((k - 1) / k))
    T4 = T3 - eta_t * (T3 - T4s)

    W_c = m_dot_real * Cp * (T2 - T1)
    W_t = m_dot_real * Cp * (T3 - T4)
    W_net_real = (W_t - W_c) * HIEU_SUAT_MAY_PHAT * (1 - TY_LE_DIEN_TU_TRI)

    return max(W_net_real, 0.0), T4 - 273.15, m_dot_real

# --- KHỞI TẠO TRẠNG THÁI MÔ PHỎNG ---
if 'x_data' not in st.session_state:
    st.session_state.x_data = []
    st.session_state.y_fuel = []
    st.session_state.y_power = []
    st.session_state.y_t4 = []
    st.session_state.y_energy = []
    st.session_state.time_elapsed = 0
    st.session_state.total_energy_kwh = 0.0
    st.session_state.running = False

if 'base_fuel' not in st.session_state:
    st.session_state.base_fuel = 85.0

# Tiêu đề chính
st.markdown("<div class='main-title'>⚡ GIÁM SÁT ĐỒNG BỘ TOÀN DIỆN NHÀ MÁY ĐIỆN RÁC EFGT</div>", unsafe_allow_html=True)

# BẢNG ĐIỀU KHIỂN & Ô NHẬP TẢI RÁC
col_ctrl1, col_ctrl2, col_input = st.columns([1, 1, 3])

with col_ctrl1:
    if st.button("🚀 Bắt đầu / Dừng", use_container_width=True):
        st.session_state.running = not st.session_state.running

with col_ctrl2:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.x_data.clear()
        st.session_state.y_fuel.clear()
        st.session_state.y_power.clear()
        st.session_state.y_t4.clear()
        st.session_state.y_energy.clear()
        st.session_state.time_elapsed = 0
        st.session_state.total_energy_kwh = 0.0
        st.session_state.running = False

with col_input:
    fuel_input = st.number_input(
        "🔥 Nhập lượng rác nạp (g/s):",
        min_value=10.0,
        max_value=500.0,
        value=float(st.session_state.base_fuel),
        step=1.0,
        disabled=st.session_state.running,
        help="Nhập số từ 10.0 đến 500.0 g/s khi hệ thống đang dừng"
    )
    if not st.session_state.running:
        st.session_state.base_fuel = fuel_input

# HÀM VẼ SƠ ĐỒ HỆ THỐNG SVG (ĐÃ BỎ HÌNH TAM GIÁC & DỜI MŨI TÊN TRÁNH CHỮ TUABIN KHÍ)
def tao_so_do_svg_moi(is_running=False, fuel_grams=85.0):
    fan_class = "fan-spinning" if is_running else ""

    svg = f"""
    <svg viewBox="0 0 600 380" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" style="background-color: #1e293b; border-radius: 10px; border: 1px solid #334155; padding: 5px;">
      <defs>
        <marker id="arrow-white" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#f8fafc"/>
        </marker>
        <style>
          @keyframes spin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
          }}
          .fan-spinning {{
            transform-origin: center;
            transform-box: fill-box;
            animation: spin 0.6s linear infinite;
          }}
        </style>
      </defs>

      <!-- 1. Hệ Thống lọc, thu giữ khí thải -->
      <rect x="25" y="25" width="180" height="65" fill="#bef264" stroke="#84cc16" stroke-width="2" rx="12"/>
      <text x="115" y="52" fill="#0f172a" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">Hệ Thống lọc,</text>
      <text x="115" y="70" fill="#0f172a" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">thu giữ khí thải</text>

      <!-- 2. Bộ HTHE Gián tiếp -->
      <rect x="225" y="105" width="130" height="70" fill="#b91c1c" stroke="#ef4444" stroke-width="2" rx="10"/>
      <text x="290" y="146" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">Bộ HTHE Gián tiếp</text>

      <!-- 3. Máy nén khí -->
      <rect x="130" y="200" width="80" height="80" fill="#000000" stroke="#475569" stroke-width="2" rx="18"/>
      <g transform="translate(170, 240)">
        <g class="{fan_class}">
          <line x1="-22" y1="0" x2="22" y2="0" stroke="#ffffff" stroke-width="6" stroke-linecap="round"/>
          <line x1="0" y1="-22" x2="0" y2="22" stroke="#ffffff" stroke-width="6" stroke-linecap="round"/>
        </g>
      </g>
      <text x="170" y="300" fill="#f8fafc" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">Máy nén khí</text>

      <!-- 4. Tuabin khí -->
      <rect x="390" y="200" width="80" height="80" fill="#000000" stroke="#475569" stroke-width="2" rx="18"/>
      <g transform="translate(430, 240)">
        <g class="{fan_class}">
          <line x1="-22" y1="0" x2="22" y2="0" stroke="#ffffff" stroke-width="6" stroke-linecap="round"/>
          <line x1="0" y1="-22" x2="0" y2="22" stroke="#ffffff" stroke-width="6" stroke-linecap="round"/>
        </g>
      </g>
      <text x="430" y="300" fill="#f8fafc" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">Tuabin khí</text>

      <!-- 5. Lò đốt rác ngoài -->
      <rect x="220" y="280" width="140" height="70" fill="#ea580c" stroke="#f97316" stroke-width="2" rx="10"/>
      <text x="290" y="321" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">Lò đốt rác ngoài</text>

      <!-- 6. Trục quay -->
      <line x1="210" y1="240" x2="390" y2="240" stroke="#f8fafc" stroke-width="4"/>

      <!-- 7. Đường ống & Mũi tên -->
      <!-- Đường nạp khí đầu vào Máy nén -->
      <line x1="30" y1="240" x2="120" y2="240" stroke="#f8fafc" stroke-width="3" marker-end="url(#arrow-white)"/>
      
      <!-- Đường ống TỪ Bộ HTHE Gián tiếp ĐI XUỐNG Máy nén khí -->
      <path d="M 225 140 L 170 140 L 170 190" fill="none" stroke="#f8fafc" stroke-width="3" marker-end="url(#arrow-white)"/>
      
      <!-- Đường ống TỪ Tuabin khí ĐI NGƯỢC LÊN Bộ HTHE Gián tiếp -->
      <path d="M 430 200 L 430 140 L 360 140" fill="none" stroke="#f8fafc" stroke-width="3" marker-end="url(#arrow-white)"/>
      
      <!-- Đường ống Tuabin -> Lò đốt (Dời điểm đi xuống sang x=460 để không đè lên chữ Tuabin khí) -->
      <path d="M 460 280 L 460 315 L 370 315" fill="none" stroke="#f8fafc" stroke-width="3" marker-end="url(#arrow-white)"/>
      <text x="430" y="335" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold" text-anchor="middle">Khí sạch nóng</text>

      <!-- Đường ống HTHE -> Lọc khí thải -->
      <path d="M 290 105 L 290 58 L 215 58" fill="none" stroke="#f8fafc" stroke-width="3" marker-end="url(#arrow-white)"/>
      <text x="270" y="48" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold" text-anchor="middle">Khói thải lò</text>

      <!-- Đường truyền nhiệt -->
      <line x1="290" y1="280" x2="290" y2="175" stroke="#fb923c" stroke-width="3" stroke-dasharray="5,5"/>
    </svg>
    """
    return svg

# CHIA BỐ CỤC 2 CỘT
col_left, col_right = st.columns([1, 1])

if not st.session_state.running:
    current_fuel = st.session_state.base_fuel
    p_calc, t4_calc, _ = tinh_toan_nguoc_efgt(current_fuel / 1000.0)
    current_power = p_calc
    current_t4 = t4_calc
    current_energy = st.session_state.total_energy_kwh
else:
    current_fuel = st.session_state.y_fuel[-1] if st.session_state.y_fuel else st.session_state.base_fuel
    current_power = st.session_state.y_power[-1] if st.session_state.y_power else 0.0
    current_t4 = st.session_state.y_t4[-1] if st.session_state.y_t4 else 0.0
    current_energy = st.session_state.total_energy_kwh

# --- CỘT TRÁI: SƠ ĐỒ HỆ THỐNG ---
with col_left:
    st.markdown("<p style='font-size: 13px; font-weight: bold; color: #cbd5e1; margin-bottom: 2px;'>⚙️ SƠ ĐỒ HỆ THỐNG EFGT</p>", unsafe_allow_html=True)
    svg_code = tao_so_do_svg_moi(st.session_state.running, current_fuel)
    st.markdown(svg_code, unsafe_allow_html=True)

# --- CỘT PHẢI: BIỂU ĐỒ REAL-TIME & 4 HỘP GIÁ TRỊ METRIC BÊN DƯỚI ---
with col_right:
    st.markdown("<p style='font-size: 13px; font-weight: bold; color: #cbd5e1; margin-bottom: 2px;'>📊 BIỂU ĐỒ REAL-TIME</p>", unsafe_allow_html=True)
    chart_placeholder = st.empty()

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔥 Rác Nạp", f"{current_fuel:.1f} g/s")
    m2.metric("⚡ Điện Lưới", f"{current_power:.2f} kW")
    m3.metric("🌡️ Khí T4", f"{current_t4:.1f} °C")
    m4.metric("🔋 Tích Lũy", f"{current_energy:.4f} kWh")

def render_chart():
    if not st.session_state.x_data:
        return None
    
    x_vis = st.session_state.x_data[-20:]
    y_fuel_vis = st.session_state.y_fuel[-20:]
    y_power_vis = st.session_state.y_power[-20:]
    y_t4_vis = st.session_state.y_t4[-20:]
    y_energy_vis = st.session_state.y_energy[-20:]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)

    fig.add_trace(go.Scatter(
        x=x_vis,
        y=y_fuel_vis,
        mode='lines+markers',
        name='Tải Rác',
        line=dict(color='#f43f5e', width=2),
        marker=dict(size=5, color='#f43f5e'),
        customdata=list(zip(y_power_vis, y_t4_vis, y_energy_vis)),
        hovertemplate="⏱ <b>T gian:</b> %{x}s<br>" +
                      "🔥 <b>Rác nạp:</b> %{y:.1f} g/s<br>" +
                      "⚡ <b>Điện lưới:</b> %{customdata[0]:.2f} kW<br>" +
                      "🌡 <b>Khí T4:</b> %{customdata[1]:.1f} °C<br>" +
                      "🔋 <b>Tích lũy:</b> %{customdata[2]:.4f} kWh<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x_vis,
        y=y_power_vis,
        mode='lines+markers',
        name='Điện Lưới',
        line=dict(color='#38bdf8', width=2),
        marker=dict(size=5, color='#38bdf8'),
        customdata=list(zip(y_fuel_vis, y_t4_vis, y_energy_vis)),
        hovertemplate="⏱ <b>T gian:</b> %{x}s<br>" +
                      "🔥 <b>Rác nạp:</b> %{customdata[0]:.1f} g/s<br>" +
                      "⚡ <b>Điện lưới:</b> %{y:.2f} kW<br>" +
                      "🌡 <b>Khí T4:</b> %{customdata[1]:.1f} °C<br>" +
                      "🔋 <b>Tích lũy:</b> %{customdata[2]:.4f} kWh<extra></extra>"
    ), row=2, col=1)

    fig.update_layout(
        paper_bgcolor='#0f172a',
        plot_bgcolor='#1e293b',
        font=dict(color='#cbd5e1', family="monospace"),
        margin=dict(l=10, r=10, t=5, b=10),
        height=320,
        showlegend=False,
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#1e293b",
            bordercolor="#38bdf8",
            font_size=11,
            font_family="monospace"
        )
    )

    fig.update_xaxes(gridcolor='#334155', showgrid=True, zeroline=False)
    fig.update_yaxes(gridcolor='#334155', showgrid=True, zeroline=False)
    fig.update_yaxes(title_text="Rác (g/s)", title_font=dict(color="#f43f5e", size=10), row=1, col=1)
    fig.update_yaxes(title_text="Điện (kW)", title_font=dict(color="#38bdf8", size=10), row=2, col=1)
    fig.update_xaxes(title_text="Thời gian (s)", title_font=dict(color="#cbd5e1", size=10), row=2, col=1)

    return fig

fig = render_chart()
if fig:
    chart_placeholder.plotly_chart(fig, use_container_width=True)

# VÒNG LẶP MÔ PHỎNG VẬN HÀNH
if st.session_state.running:
    st.session_state.time_elapsed += 1
    
    fuel_g = st.session_state.base_fuel + random.uniform(-2.5, 2.5)
    
    m_fuel_sec = fuel_g / 1000.0
    p_real, t4_real, _ = tinh_toan_nguoc_efgt(m_fuel_sec)
    
    st.session_state.total_energy_kwh += p_real / 3600.0
    st.session_state.x_data.append(st.session_state.time_elapsed)
    st.session_state.y_fuel.append(fuel_g)
    st.session_state.y_power.append(p_real)
    st.session_state.y_t4.append(t4_real)
    st.session_state.y_energy.append(st.session_state.total_energy_kwh)

    time.sleep(1)
    st.rerun()
