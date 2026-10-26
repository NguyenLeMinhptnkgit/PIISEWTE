import time
import random
import math
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Cấu hình trang web
st.set_page_config(
    page_title="Mô phỏng Hệ thống EFGT",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS GIAO DIỆN & METRIC BOXES ---
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

# --- KHỞI TẠO SESSION STATE ---
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

st.markdown("<div class='main-title'>⚡ GIÁM SÁT ĐỒNG BỘ TOÀN DIỆN NHÀ MÁY ĐIỆN RÁC EFGT</div>", unsafe_allow_html=True)

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
        disabled=st.session_state.running
    )
    if not st.session_state.running:
        st.session_state.base_fuel = fuel_input

# HÀM VẼ SƠ ĐỒ HỆ THỐNG SVG (ĐÃ KHẮC PHỤC LỖI HIỂN THỊ MÃ THUẦN)
def tao_so_do_svg_moi(is_running=False, fuel_grams=85.0):
    fan_class = "fan-spinning" if is_running else ""

    svg = f"""
    <svg viewBox="0 0 760 420" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" style="background-color: #1e293b; border-radius: 10px; border: 1px solid #334155; padding: 5px;">
      <defs>
        <marker id="arrow-white" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#ffffff"/>
        </marker>
        <marker id="arrow-green" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#bef264"/>
        </marker>
        <marker id="arrow-purple" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#d8b4fe"/>
        </marker>
        <marker id="arrow-orange" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#ea580c"/>
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

      <!-- CHÚ GIẢI (LEGEND) -->
      <g transform="translate(10, 8)">
        <line x1="5" y1="12" x2="40" y2="12" stroke="#ffffff" stroke-width="3" marker-end="url(#arrow-white)"/>
        <text x="50" y="16" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold">Hướng đi của dòng điện</text>

        <line x1="5" y1="32" x2="40" y2="32" stroke="#bef264" stroke-width="3" marker-end="url(#arrow-green)"/>
        <text x="50" y="36" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold">Hướng đi của luồng khí thải</text>

        <line x1="5" y1="52" x2="40" y2="52" stroke="#d8b4fe" stroke-width="3" marker-end="url(#arrow-purple)"/>
        <text x="50" y="56" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold">Hướng đi của luồng khí sạch</text>

        <line x1="5" y1="72" x2="40" y2="72" stroke="#ea580c" stroke-width="3" marker-end="url(#arrow-orange)"/>
        <text x="50" y="76" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold">Hướng đi của nhiệt từ lò đốt</text>
      </g>

      <!-- CÁC KHỐI THÀNH PHẦN -->
      <rect x="520" y="15" width="140" height="60" fill="#b91c1c" stroke="#ef4444" stroke-width="2" rx="10"/>
      <text x="590" y="50" fill="#ffffff" font-family="sans-serif" font-size="16" font-weight="bold" text-anchor="middle">Output</text>

      <rect x="330" y="90" width="160" height="65" fill="#b91c1c" stroke="#ef4444" stroke-width="2" rx="10"/>
      <text x="410" y="128" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">Bộ HTHE Gián tiếp</text>

      <rect x="230" y="190" width="75" height="75" fill="#000000" stroke="#475569" stroke-width="2" rx="16"/>
      <g transform="translate(267.5, 227.5)">
        <g class="{fan_class}">
          <line x1="-20" y1="0" x2="20" y2="0" stroke="#ffffff" stroke-width="5" stroke-linecap="round"/>
          <line x1="0" y1="-20" x2="0" y2="20" stroke="#ffffff" stroke-width="5" stroke-linecap="round"/>
        </g>
      </g>
      <text x="267.5" y="283" fill="#f8fafc" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">Máy nén khí</text>

      <rect x="540" y="190" width="75" height="75" fill="#000000" stroke="#475569" stroke-width="2" rx="16"/>
      <g transform="translate(577.5, 227.5)">
        <g class="{fan_class}">
          <line x1="-20" y1="0" x2="20" y2="0" stroke="#ffffff" stroke-width="5" stroke-linecap="round"/>
          <line x1="0" y1="-20" x2="0" y2="20" stroke="#ffffff" stroke-width="5" stroke-linecap="round"/>
        </g>
      </g>
      <text x="630" y="233" fill="#f8fafc" font-family="sans-serif" font-size="12" font-weight="bold">Tuabin khí</text>

      <rect x="340" y="320" width="150" height="65" fill="#ea580c" stroke="#f97316" stroke-width="2" rx="10"/>
      <text x="415" y="358" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">Lò đốt rác ngoài</text>

      <rect x="15" y="325" width="170" height="60" fill="#bef264" stroke="#84cc16" stroke-width="2" rx="10"/>
      <text x="100" y="350" fill="#0f172a" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">Hệ Thống lọc,</text>
      <text x="100" y="368" fill="#0f172a" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">thu giữ khí thải</text>

      <!-- ĐƯỜNG MŨI TÊN KẾT NỐI -->
      <!-- Khí sạch tím nạp vào Máy nén -->
      <line x1="140" y1="227.5" x2="222" y2="227.5" stroke="#d8b4fe" stroke-width="5" marker-end="url(#arrow-purple)"/>

      <!-- Khí sạch tím từ Máy nén sang Tuabin -->
      <line x1="305" y1="227.5" x2="532" y2="227.5" stroke="#d8b4fe" stroke-width="5" marker-end="url(#arrow-purple)"/>

      <!-- Khí sạch nóng tím từ Tuabin xuống Lò đốt -->
      <path d="M 577.5 265 L 577.5 352.5 L 498 352.5" fill="none" stroke="#d8b4fe" stroke-width="5" marker-end="url(#arrow-purple)"/>
      <text x="577.5" y="380" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold" text-anchor="middle">Khí sạch nóng</text>

      <!-- Nhiệt làm nóng khí (Cam) từ Lò đốt chỉ lên đường khí sạch -->
      <line x1="455" y1="320" x2="455" y2="237" stroke="#ea580c" stroke-width="4" marker-end="url(#arrow-orange)"/>
      <text x="495" y="270" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold">Nhiệt làm</text>
      <text x="495" y="286" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold">nóng khí</text>

      <!-- Nhiệt dư (Cam đứt nét) từ Lò đốt lên Bộ HTHE -->
      <line x1="415" y1="320" x2="415" y2="163" stroke="#ea580c" stroke-width="4" stroke-dasharray="6,4" marker-end="url(#arrow-orange)"/>
      <text x="375" y="278" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold">Nhiệt dư</text>

      <!-- Đường dòng điện (Trắng) từ Tuabin lên Output -->
      <line x1="577.5" y1="190" x2="577.5" y2="83" stroke="#ffffff" stroke-width="3" marker-end="url(#arrow-white)"/>
      <text x="585" y="140" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold">Động năng sang Điện năng</text>

      <!-- Đường dòng điện (Trắng) từ Output vòng về Máy nén khí -->
      <path d="M 520 45 L 267.5 45 L 267.5 182" fill="none" stroke="#ffffff" stroke-width="3" marker-end="url(#arrow-white)"/>

      <!-- Đường dòng điện (Trắng) từ HTHE nối vào tuyến điện Máy nén -->
      <path d="M 330 122.5 L 267.5 122.5" fill="none" stroke="#ffffff" stroke-width="3"/>

      <!-- Khói thải lò (Xanh lá) từ Lò đốt sang Hệ thống lọc -->
      <line x1="340" y1="355" x2="193" y2="355" stroke="#bef264" stroke-width="4" marker-end="url(#arrow-green)"/>
      <text x="260" y="345" fill="#f8fafc" font-family="sans-serif" font-size="11" font-weight="bold" text-anchor="middle">Khói thải lò</text>
    </svg>
    """
    return svg

col_left, col_right = st.columns([1, 1])

svg_fuel = st.session_state.y_fuel[-1] if (st.session_state.running and st.session_state.y_fuel) else st.session_state.base_fuel

with col_left:
    st.markdown("<p style='font-size: 13px; font-weight: bold; color: #cbd5e1; margin-bottom: 2px;'>⚙️ SƠ ĐỒ HỆ THỐNG EFGT</p>", unsafe_allow_html=True)
    svg_code = tao_so_do_svg_moi(st.session_state.running, svg_fuel)
    st.markdown(svg_code, unsafe_allow_html=True)

def render_chart():
    if not st.session_state.x_data:
        return None
    
    x_vis = st.session_state.x_data[-20:]
    y_fuel_vis = st.session_state.y_fuel[-20:]
    y_power_vis = st.session_state.y_power[-20:]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)

    fig.add_trace(go.Scatter(
        x=x_vis,
        y=y_fuel_vis,
        mode='lines+markers',
        name='Tải Rác',
        line=dict(color='#f43f5e', width=2),
        marker=dict(size=5, color='#f43f5e'),
        hovertemplate="⏱ <b>T gian:</b> %{x}s<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x_vis,
        y=y_power_vis,
        mode='lines+markers',
        name='Điện Lưới',
        line=dict(color='#38bdf8', width=2),
        marker=dict(size=5, color='#38bdf8'),
        hovertemplate="⏱ <b>T gian:</b> %{x}s<extra></extra>"
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
    fig.update_yaxes(title_text="Điện (kWh)", title_font=dict(color="#38bdf8", size=10), row=2, col=1)
    fig.update_xaxes(title_text="Thời gian (s)", title_font=dict(color="#cbd5e1", size=10), row=2, col=1)

    return fig

with col_right:
    st.markdown("<p style='font-size: 13px; font-weight: bold; color: #cbd5e1; margin-bottom: 2px;'>📊 BIỂU ĐỒ REAL-TIME</p>", unsafe_allow_html=True)
    fig = render_chart()
    
    selected_idx = None
    if fig:
        event_data = st.plotly_chart(fig, on_select="rerun", selection_mode="points", use_container_width=True)
        if event_data and "selection" in event_data:
            pts = event_data["selection"].get("points", [])
            if pts:
                target_x = pts[0].get("x")
                if target_x in st.session_state.x_data:
                    selected_idx = st.session_state.x_data.index(target_x)

    if selected_idx is not None:
        current_fuel = st.session_state.y_fuel[selected_idx]
        current_power = st.session_state.y_power[selected_idx]
        current_t4 = st.session_state.y_t4[selected_idx]
        current_energy = st.session_state.y_energy[selected_idx]

    elif len(st.session_state.x_data) > 0:
        current_fuel = st.session_state.y_fuel[-1]
        current_power = st.session_state.y_power[-1]
        current_t4 = st.session_state.y_t4[-1]
        current_energy = st.session_state.y_energy[-1]

    else:
        current_fuel = st.session_state.base_fuel
        p_calc, t4_calc, _ = tinh_toan_nguoc_efgt(current_fuel / 1000.0)
        current_power = p_calc
        current_t4 = t4_calc
        current_energy = st.session_state.total_energy_kwh

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔥 Rác Nạp", f"{current_fuel:.1f} g/s")
    m2.metric("⚡ Điện Lưới", f"{current_power:.2f} kWh")
    m3.metric("🌡️ Nhiệt Độ Khí", f"{current_t4:.1f} °C")
    m4.metric("🔋 Tích Lũy", f"{current_energy:.4f} kW")

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
