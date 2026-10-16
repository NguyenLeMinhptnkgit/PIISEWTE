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
    initial_sidebar_state="expanded"
)

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

st.markdown("<h2 style='text-align: center; color: #38bdf8; font-family: sans-serif; margin-bottom: 20px;'>HỆ THỐNG GIÁM SÁT ĐỒNG BỘ TOÀN DIỆN NHÀ MÁY ĐIỆN RÁC EFGT</h2>", unsafe_allow_html=True)

# Bảng điều khiển Sidebar
st.sidebar.header("🕹️ Bảng Điều Khiển")
col_btn1, col_btn2 = st.sidebar.columns(2)

with col_btn1:
    if st.button("🚀 Bắt đầu / Dừng"):
        st.session_state.running = not st.session_state.running

with col_btn2:
    if st.button("🔄 Reset"):
        st.session_state.x_data.clear()
        st.session_state.y_fuel.clear()
        st.session_state.y_power.clear()
        st.session_state.y_t4.clear()
        st.session_state.y_energy.clear()
        st.session_state.time_elapsed = 0
        st.session_state.total_energy_kwh = 0.0
        st.session_state.running = False

# HÀM TẠO SƠ ĐỒ HỆ THỐNG SVG DẠNG ĐỘNG
def tao_so_do_svg(is_running=False, fuel_grams=85.0):
    mau_t4 = "#f97316" if fuel_grams > 90 else "#fba51a"
    fan_class = "fan-spinning" if is_running else ""
    flame_size = int(fuel_grams * 0.3) + 12 if is_running else 0
    
    flame_svg = f"""
    <polygon points="290,{325 - flame_size} 265,325 315,325" fill="#f97316" stroke="#ef4444" stroke-width="1.5">
        <animate attributeName="opacity" values="0.8;1;0.8" dur="0.3s" repeatCount="indefinite" />
    </polygon>
    """ if is_running else ""

    svg = f"""
    <svg viewBox="0 0 580 360" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" style="background-color: #1e293b; border-radius: 8px; border: 1px solid #334155; margin-bottom: 10px;">
      <defs>
        <marker id="arrow-cyan" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8"/>
        </marker>
        <marker id="arrow-red" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444"/>
        </marker>
        <marker id="arrow-orange" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="{mau_t4}"/>
        </marker>
        <marker id="arrow-gray" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8"/>
        </marker>
        <style>
          @keyframes spin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
          }}
          .fan-spinning {{
            animation: spin 0.6s linear infinite;
          }}
        </style>
      </defs>

      <!-- Trục quay liên kết -->
      <line x1="80" y1="180" x2="500" y2="180" stroke="#64748b" stroke-width="5"/>

      <!-- Máy nén khí -->
      <polygon points="80,120 170,135 170,225 80,240" fill="#334155" stroke="#475569" stroke-width="2"/>
      <text x="125" y="255" fill="#cbd5e1" font-family="sans-serif" font-size="11" font-weight="bold" text-anchor="middle">MÁY NÉN KHÍ</text>
      <line x1="20" y1="180" x2="70" y2="180" stroke="#38bdf8" stroke-width="3" marker-end="url(#arrow-cyan)"/>

      <!-- Tuabin khí -->
      <polygon points="410,135 500,120 500,240 410,225" fill="#334155" stroke="#475569" stroke-width="2"/>
      <text x="455" y="255" fill="#cbd5e1" font-family="sans-serif" font-size="11" font-weight="bold" text-anchor="middle">TUABIN KHÍ</text>

      <!-- Bộ HTHE Gián tiếp -->
      <rect x="230" y="30" width="120" height="70" fill="#1e293b" stroke="#f43f5e" stroke-width="2" rx="4"/>
      <text x="290" y="60" fill="#f43f5e" font-family="sans-serif" font-size="11" font-weight="bold" text-anchor="middle">BỘ HTHE</text>
      <text x="290" y="76" fill="#f43f5e" font-family="sans-serif" font-size="11" font-weight="bold" text-anchor="middle">GIÁN TIẾP</text>

      <!-- Lò đốt rác ngoài -->
      <rect x="230" y="260" width="120" height="70" fill="#27272a" stroke="#ea580c" stroke-width="2" rx="4"/>
      <text x="290" y="298" fill="#ea580c" font-family="sans-serif" font-size="11" font-weight="bold" text-anchor="middle">LÒ ĐỐT RÁC NGOÀI</text>

      <!-- Đường ống Máy nén -> HTHE -->
      <polyline points="150,135 150,50 230,50" fill="none" stroke="#38bdf8" stroke-width="4" marker-end="url(#arrow-cyan)"/>

      <!-- Đường ống HTHE -> Tuabin -->
      <polyline points="350,50 430,50 430,135" fill="none" stroke="#ef4444" stroke-width="5" marker-end="url(#arrow-red)"/>

      <!-- Đường ống T4 Hoàn lưu -->
      <polyline points="500,180 550,180 550,295 350,295" fill="none" stroke="{mau_t4}" stroke-width="4" marker-end="url(#arrow-orange)"/>
      <text x="540" y="280" fill="#fbbf24" font-family="sans-serif" font-size="10" font-weight="bold" text-anchor="end">Khí sạch nóng (T4)</text>

      <!-- Dòng nhiệt truyền lò -> HTHE -->
      <line x1="290" y1="260" x2="290" y2="100" stroke="#ea580c" stroke-width="3" stroke-dasharray="4,4"/>

      <!-- Đường ống Khói thải lò -->
      <polyline points="290,30 290,10 200,10" fill="none" stroke="#94a3b8" stroke-width="3" marker-end="url(#arrow-gray)"/>
      <text x="220" y="22" fill="#94a3b8" font-family="sans-serif" font-size="10" text-anchor="middle">Khói thải lò</text>

      <!-- Cánh quạt máy nén -->
      <g transform="translate(125, 180)">
        <g class="{fan_class}" style="transform-origin: 0px 0px;">
          <line x1="-30" y1="0" x2="30" y2="0" stroke="#e2e8f0" stroke-width="4"/>
          <line x1="0" y1="-30" x2="0" y2="30" stroke="#e2e8f0" stroke-width="4"/>
        </g>
      </g>

      <!-- Cánh quạt tuabin -->
      <g transform="translate(455, 180)">
        <g class="{fan_class}" style="transform-origin: 0px 0px;">
          <line x1="-30" y1="0" x2="30" y2="0" stroke="#e2e8f0" stroke-width="4"/>
          <line x1="0" y1="-30" x2="0" y2="30" stroke="#e2e8f0" stroke-width="4"/>
        </g>
      </g>

      <!-- Ngọn lửa mô phỏng -->
      {flame_svg}
    </svg>
    """
    return svg

# CHIA BỐ CỤC 2 CỘT CHÍNH (TRÁI / PHẢI)
col_left, col_right = st.columns([1, 1])

current_fuel = st.session_state.y_fuel[-1] if st.session_state.y_fuel else 0.0
current_power = st.session_state.y_power[-1] if st.session_state.y_power else 0.0
current_t4 = st.session_state.y_t4[-1] if st.session_state.y_t4 else 0.0
current_energy = st.session_state.total_energy_kwh

# --- CỘT TRÁI: SƠ ĐỒ ĐỘNG CƠ + THẺ CHỈ SỐ ---
with col_left:
    st.markdown("##### ⚙️ SƠ ĐỒ HỆ THỐNG ĐỘNG CƠ EFGT")
    svg_code = tao_so_do_svg(st.session_state.running, current_fuel)
    st.markdown(svg_code, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔥 Rác Nạp", f"{current_fuel:.1f} g/s")
    m2.metric("⚡ Điện Lưới", f"{current_power:.2f} kW")
    m3.metric("🌡️ Khí T4", f"{current_t4:.1f} °C")
    m4.metric("🔋 Tích Lũy", f"{current_energy:.4f} kWh")

# --- CỘT PHẢI: BIỂU ĐỒ HOẠT ĐỘNG REAL-TIME ---
with col_right:
    st.markdown("##### 📊 BIỂU ĐỒ GIÁM SÁT THỜI GIAN THỰC")
    chart_placeholder = st.empty()

def render_chart():
    if not st.session_state.x_data:
        return None
    
    x_vis = st.session_state.x_data[-20:]
    y_fuel_vis = st.session_state.y_fuel[-20:]
    y_power_vis = st.session_state.y_power[-20:]
    y_t4_vis = st.session_state.y_t4[-20:]
    y_energy_vis = st.session_state.y_energy[-20:]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12)

    # Đồ thị 1: Tải Rác
    custom_data_1 = list(zip(y_power_vis, y_t4_vis, y_energy_vis))
    fig.add_trace(go.Scatter(
        x=x_vis,
        y=y_fuel_vis,
        mode='lines+markers',
        name='Tải Rác',
        line=dict(color='#f43f5e', width=2),
        marker=dict(size=6, color='#f43f5e'),
        customdata=custom_data_1,
        hovertemplate="⏱ <b>T gian:</b> %{x}s<br>" +
                      "🔥 <b>Rác nạp:</b> %{y:.1f} g/s<br>" +
                      "⚡ <b>Điện lưới:</b> %{customdata[0]:.2f} kW<br>" +
                      "🌡 <b>Khí T4:</b> %{customdata[1]:.1f} °C<br>" +
                      "🔋 <b>Tích lũy:</b> %{customdata[2]:.4f} kWh<extra></extra>"
    ), row=1, col=1)

    # Đồ thị 2: Điện Lưới
    custom_data_2 = list(zip(y_fuel_vis, y_t4_vis, y_energy_vis))
    fig.add_trace(go.Scatter(
        x=x_vis,
        y=y_power_vis,
        mode='lines+markers',
        name='Điện Lưới',
        line=dict(color='#38bdf8', width=2),
        marker=dict(size=6, color='#38bdf8'),
        customdata=custom_data_2,
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
        margin=dict(l=20, r=20, t=10, b=20),
        height=380,
        showlegend=False,
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#1e293b",
            bordercolor="#38bdf8",
            font_size=12,
            font_family="monospace"
        )
    )

    fig.update_xaxes(gridcolor='#334155', showgrid=True, zeroline=False)
    fig.update_yaxes(gridcolor='#334155', showgrid=True, zeroline=False)
    fig.update_yaxes(title_text="Tải Rác (g/s)", title_font=dict(color="#f43f5e", size=11), row=1, col=1)
    fig.update_yaxes(title_text="Điện lưới (kW)", title_font=dict(color="#38bdf8", size=11), row=2, col=1)
    fig.update_xaxes(title_text="Thời gian (giây)", title_font=dict(color="#cbd5e1", size=11), row=2, col=1)

    return fig

fig = render_chart()
if fig:
    chart_placeholder.plotly_chart(fig, use_container_width=True)

# VÒNG LẶP CẬP NHẬT MÔ PHỎNG DỮ LIỆU
if st.session_state.running:
    st.session_state.time_elapsed += 1
    fuel_g = random.uniform(80.0, 95.0)
    if random.random() < 0.15:
        fuel_g = random.choice([75.5, 99.0])
    
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
