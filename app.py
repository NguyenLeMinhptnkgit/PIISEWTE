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

# --- HÀM VẼ SƠ ĐỒ HỆ THỐNG SVG (ĐÃ KÉO DÀI MŨI TÊN GIỮA LÒ ĐỐT VÀ SẤY KHÔ RÁC) ---
def tao_so_do_svg_moi(is_running=False, fuel_grams=85.0):
    fan_class = "fan-spinning" if is_running else ""

    svg_lines = [
        '<svg viewBox="0 0 850 560" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" style="background-color: #0f172a; border-radius: 10px; border: 1px solid #334155; padding: 5px;">',
        '<defs>',
        '<marker id="arr-black" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#f8fafc"/></marker>',
        '<marker id="arr-purple" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#c084fc"/></marker>',
        '<marker id="arr-orange" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#ea580c"/></marker>',
        '<marker id="arr-green" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#bef264"/></marker>',
        '<marker id="arr-blue" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#38bdf8"/></marker>',
        '<style>',
        '@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }',
        f'.fan-spinning {{ transform-origin: center; transform-box: fill-box; animation: spin 0.6s linear infinite; }}',
        '.text-node { font-family: sans-serif; font-size: 13px; font-weight: bold; }',
        '.legend-text { font-family: sans-serif; font-size: 11px; font-weight: 600; fill: #e2e8f0; }',
        '</style>',
        '</defs>',

        '<!-- 1. KHỐI OUTPUT (GÓC TRÊN PHẢI) -->',
        '<rect x="540" y="15" width="160" height="55" fill="#991b1b" stroke="#ef4444" stroke-width="2" rx="10"/>',
        '<text x="620" y="50" fill="#ffffff" font-family="sans-serif" font-size="22" font-weight="bold" text-anchor="middle">Output</text>',
        '<line x1="700" y1="42.5" x2="770" y2="42.5" stroke="#f8fafc" stroke-width="3" marker-end="url(#arr-black)"/>',

        '<!-- 2. ĐỘNG CƠ STIRLING (TRÊN GIỮA) -->',
        '<rect x="330" y="60" width="145" height="45" fill="#991b1b" stroke="#ef4444" stroke-width="2" rx="8"/>',
        '<text x="402.5" y="87" fill="#ffffff" class="text-node" text-anchor="middle">Động cơ Stirling</text>',

        '<!-- 3. BỘ HTHE GIÁN TIẾP (GIỮA TRÊN) -->',
        '<rect x="320" y="180" width="165" height="55" fill="#991b1b" stroke="#ef4444" stroke-width="2" rx="10"/>',
        '<text x="402.5" y="213" fill="#ffffff" class="text-node" text-anchor="middle">Bộ HTHE Gián tiếp</text>',

        '<!-- 4. KHỐI HTHE XANH LÁ (TRÊN TUYẾN DÒNG KHÍ) -->',
        '<rect x="345" y="260" width="115" height="50" fill="#16a34a" stroke="#22c55e" stroke-width="2" rx="8"/>',
        '<text x="402.5" y="291" fill="#ffffff" font-family="sans-serif" font-size="15" font-weight="bold" text-anchor="middle">HTHE</text>',

        '<!-- 5. MÁY NÉN KHÍ (BÊN TRÁI) -->',
        '<rect x="190" y="247.5" width="75" height="75" fill="#000000" stroke="#64748b" stroke-width="2" rx="15"/>',
        f'<g transform="translate(227.5, 285)"><g class="{fan_class}">',
        '<line x1="-18" y1="0" x2="18" y2="0" stroke="#ffffff" stroke-width="5" stroke-linecap="round"/>',
        '<line x1="0" y1="-18" x2="0" y2="18" stroke="#ffffff" stroke-width="5" stroke-linecap="round"/>',
        '</g></g>',
        '<text x="227.5" y="343" fill="#f8fafc" class="text-node" text-anchor="middle">Máy nén khí</text>',

        '<!-- 6. TUABIN KHÍ (BÊN PHẢI) -->',
        '<rect x="580" y="247.5" width="75" height="75" fill="#000000" stroke="#64748b" stroke-width="2" rx="15"/>',
        f'<g transform="translate(617.5, 285)"><g class="{fan_class}">',
        '<line x1="-18" y1="0" x2="18" y2="0" stroke="#ffffff" stroke-width="5" stroke-linecap="round"/>',
        '<line x1="0" y1="-18" x2="0" y2="18" stroke="#ffffff" stroke-width="5" stroke-linecap="round"/>',
        '</g></g>',
        '<text x="668" y="290" fill="#f8fafc" class="text-node" text-anchor="start">Tuabin khí</text>',

        '<!-- 7. LÒ ĐỐT RÁC NGOÀI (DƯỚI Ở GIỮA) -->',
        '<rect x="315" y="390" width="175" height="60" fill="#ea580c" stroke="#fb923c" stroke-width="2" rx="10"/>',
        '<text x="402.5" y="416" fill="#ffffff" class="text-node" text-anchor="middle">Lò đốt</text>',
        '<text x="402.5" y="434" fill="#ffffff" class="text-node" text-anchor="middle">rác ngoài</text>',

        '<!-- 8. SẤY KHÔ RÁC (BÊN DƯỚI LÒ ĐỐT) -->',
        '<rect x="420" y="475" width="120" height="45" fill="#991b1b" stroke="#ef4444" stroke-width="2" rx="8"/>',
        '<text x="480" y="502" fill="#ffffff" class="text-node" text-anchor="middle">Sấy khô rác</text>',

        '<!-- 9. HỆ THỐNG LỌC KHÍ THẢI (DƯỚI BÊN TRÁI) -->',
        '<rect x="20" y="390" width="180" height="60" fill="#bef264" stroke="#84cc16" stroke-width="2" rx="10"/>',
        '<text x="110" y="416" fill="#0f172a" class="text-node" text-anchor="middle">Hệ thống</text>',
        '<text x="110" y="434" fill="#0f172a" class="text-node" text-anchor="middle">lọc, thu giữ khí thải</text>',

        '<!-- 10. NHÃN RÁC THẢI ĐẦU VÀO -->',
        '<text x="110" y="495" fill="#38bdf8" font-family="sans-serif" font-size="16" font-weight="bold" text-anchor="middle">Rác thải đầu vào</text>',

        '<!-- 11. NHÃN KHÔNG KHÍ NẠP VÀO -->',
        '<text x="75" y="290" fill="#c084fc" font-family="sans-serif" font-size="14" font-weight="bold" text-anchor="middle">Không khí</text>',

        '<!-- A. DÒNG ĐIỆN (MÀU TRẮNG) -->',
        '<path d="M 617.5 247.5 L 617.5 80" fill="none" stroke="#f8fafc" stroke-width="3" marker-end="url(#arr-black)"/>',
        '<text x="627" y="160" fill="#f8fafc" font-size="11" font-weight="bold" font-family="sans-serif">Động năng &#8594; Điện năng</text>',

        '<path d="M 540 42.5 L 210 42.5 L 210 237.5" fill="none" stroke="#f8fafc" stroke-width="3" marker-end="url(#arr-black)"/>',

        '<path d="M 330 82.5 L 245 82.5 L 245 237.5" fill="none" stroke="#f8fafc" stroke-width="3" marker-end="url(#arr-black)"/>',

        '<path d="M 402.5 180 L 402.5 115" fill="none" stroke="#f8fafc" stroke-width="3" marker-end="url(#arr-black)"/>',
        '<text x="412" y="150" fill="#f8fafc" font-size="10" font-weight="bold" font-family="sans-serif">Nhiệt năng &#8594; Điện năng</text>',

        '<!-- B. LUỒNG KHÍ SẠCH (MÀU TÍM) -->',
        '<line x1="115" y1="285" x2="180" y2="285" stroke="#c084fc" stroke-width="6" marker-end="url(#arr-purple)"/>',
        '<line x1="265" y1="285" x2="335" y2="285" stroke="#c084fc" stroke-width="6" marker-end="url(#arr-purple)"/>',
        '<line x1="460" y1="285" x2="570" y2="285" stroke="#c084fc" stroke-width="6" marker-end="url(#arr-purple)"/>',
        '<path d="M 617.5 322.5 L 617.5 420 L 498 420" fill="none" stroke="#c084fc" stroke-width="6" marker-end="url(#arr-purple)"/>',
        '<text x="555" y="442" fill="#c084fc" font-size="11" font-weight="bold" font-family="sans-serif" text-anchor="middle">Khí sạch nóng</text>',

        '<!-- C. NHIỆT TỪ LÒ ĐỐT (MÀU CAM) -->',
        '<line x1="370" y1="390" x2="370" y2="320" stroke="#ea580c" stroke-width="3" stroke-dasharray="6,4" marker-end="url(#arr-orange)"/>',
        '<text x="365" y="355" fill="#ea580c" font-size="10" font-weight="bold" font-family="sans-serif" text-anchor="end">Nhiệt làm nóng khí</text>',

        '<line x1="435" y1="390" x2="435" y2="245" stroke="#ea580c" stroke-width="3" stroke-dasharray="6,4" marker-end="url(#arr-orange)"/>',
        '<text x="442" y="355" fill="#ea580c" font-size="10" font-weight="bold" font-family="sans-serif" text-anchor="start">Nhiệt dư</text>',

        '<!-- 3 MŨI TÊN ĐÃ ĐƯỢC KÉO DÀI NỐI LIỀN MÉP CẠNH DƯỚI LÒ ĐỐT (y=450) VÀ MÉP TRÊN SẤY KHÔ RÁC (y=475) -->',
        '<!-- Mũi tên xanh dương đi lên (Rác sấy nạp lò) -->',
        '<line x1="442" y1="475" x2="442" y2="453" stroke="#38bdf8" stroke-width="3" marker-end="url(#arr-blue)"/>',
        '<!-- Mũi tên cam đi lên (Nhiệt/Khí hoàn tuần) -->',
        '<line x1="462" y1="475" x2="462" y2="453" stroke="#ea580c" stroke-width="3" marker-end="url(#arr-orange)"/>',
        '<!-- Mũi tên cam đi xuống (Nhiệt từ Lò đốt sang Sấy khô rác) -->',
        '<line x1="482" y1="450" x2="482" y2="472" stroke="#ea580c" stroke-width="3" marker-end="url(#arr-orange)"/>',

        '<!-- D. KHÓI THẢI LÒ (MÀU XANH LÁ) -->',
        '<line x1="315" y1="420" x2="208" y2="420" stroke="#bef264" stroke-width="3" marker-end="url(#arr-green)"/>',
        '<text x="260" y="410" fill="#bef264" font-size="11" font-weight="bold" font-family="sans-serif" text-anchor="middle">Khói thải lò</text>',

        '<!-- E. DÒNG RÁC THẢI (MÀU XANH DƯƠNG) -->',
        '<line x1="185" y1="497" x2="412" y2="497" stroke="#38bdf8" stroke-width="3" marker-end="url(#arr-blue)"/>',
        '<text x="290" y="488" fill="#38bdf8" font-size="10" font-weight="bold" font-family="sans-serif" text-anchor="middle">Loại bỏ rác không cháy được</text>',

        '<!-- F. BẢNG CHÚ GIẢI GÓC DƯỚI PHẢI -->',
        '<g transform="translate(560, 465)">',
        '<line x1="0" y1="8" x2="25" y2="8" stroke="#f8fafc" stroke-width="2.5" marker-end="url(#arr-black)"/>',
        '<text x="32" y="11" class="legend-text">Hướng đi của dòng điện</text>',
        '<line x1="0" y1="24" x2="25" y2="24" stroke="#bef264" stroke-width="2.5" marker-end="url(#arr-green)"/>',
        '<text x="32" y="27" class="legend-text">Hướng đi của luồng khí thải</text>',
        '<line x1="0" y1="40" x2="25" y2="40" stroke="#c084fc" stroke-width="2.5" marker-end="url(#arr-purple)"/>',
        '<text x="32" y="43" class="legend-text">Hướng đi của luồng khí sạch</text>',
        '<line x1="0" y1="56" x2="25" y2="56" stroke="#ea580c" stroke-width="2.5" marker-end="url(#arr-orange)"/>',
        '<text x="32" y="59" class="legend-text">Hướng đi của nhiệt từ lò đốt</text>',
        '</g>',

        '</svg>'
    ]

    return "".join(svg_lines)

# CHIA BỐ CỤC 2 CỘT
col_left, col_right = st.columns([1, 1])

svg_fuel = st.session_state.y_fuel[-1] if (st.session_state.running and st.session_state.y_fuel) else st.session_state.base_fuel

# --- CỘT TRÁI: SƠ ĐỒ HỆ THỐNG ---
with col_left:
    st.markdown("<p style='font-size: 13px; font-weight: bold; color: #cbd5e1; margin-bottom: 2px;'>⚙️ SƠ ĐỒ HỆ THỐNG EFGT CHUẨN MÔ HÌNH MỚI</p>", unsafe_allow_html=True)
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

# --- CỘT PHẢI: BIỂU ĐỒ REAL-TIME & METRIC ---
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
