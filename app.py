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

# --- CSS GIAO DIỆN NỀN TRẮNG, CHỮ ĐEN, ĐỒNG BỘ PHÔNG CHỮ TOÀN DIỆN ---
st.markdown("""
<style>
    /* Đồng bộ phông chữ tiếng Việt chuẩn nét, nền trắng, chữ đen */
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
    }
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 0.8rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        background-color: #ffffff !important;
    }
    p, span, label, div, h1, h2, h3, h4, li, b, strong, i, em {
        color: #000000 !important;
        font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
    }
    .main-title {
        text-align: center;
        color: #000000 !important;
        font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
        font-size: 20px !important;
        font-weight: 800 !important;
        margin-bottom: 10px !important;
        padding-bottom: 6px !important;
        border-bottom: 2px solid #000000 !important;
    }
    
    /* THẺ HIỂN THỊ THÔNG SỐ ĐỒNG BỘ, KHÔNG RỚT CHỮ */
    .metric-card {
        background-color: #ffffff;
        border: 1.5px solid #000000;
        border-radius: 10px;
        padding: 10px 8px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
        text-align: center;
        min-height: 98px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
    }
    .metric-card-label {
        font-size: 11.5px;
        font-weight: 700;
        color: #000000 !important;
        line-height: 1.3;
        text-align: center;
        word-break: keep-all;
    }
    .metric-card-sub {
        display: block;
        font-size: 10.5px;
        font-weight: 600;
        color: #000000 !important;
        margin-top: 2px;
        white-space: nowrap;
    }
    .metric-card-value {
        font-size: 16px;
        font-weight: 800;
        color: #000000 !important;
        margin-top: 6px;
        white-space: nowrap;
    }
    
    /* Nút bấm & Ô nhập liệu nền trắng, viền đen, chữ đen */
    div.stButton > button {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1.5px solid #000000 !important;
        border-radius: 8px !important;
        padding: 4px 12px !important;
        font-size: 13px !important;
        font-weight: 700 !important;
    }
    div.stButton > button:hover {
        background-color: #f1f5f9 !important;
        border-color: #000000 !important;
    }
    [data-testid="stNumberInput"] input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1.5px solid #000000 !important;
        font-weight: 600 !important;
    }
    [data-testid="stNumberInput"] button {
        background-color: #f8fafc !important;
        color: #000000 !important;
        border-color: #000000 !important;
    }

    /* Hộp hướng dẫn sử dụng */
    .guide-box {
        background-color: #ffffff;
        border: 1.5px solid #000000;
        border-radius: 10px;
        padding: 14px 18px;
        margin-top: 12px;
        color: #000000 !important;
        font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
        font-size: 13.5px;
        line-height: 1.65;
    }
    .guide-title {
        font-size: 15px;
        font-weight: 800;
        color: #000000 !important;
        margin-bottom: 8px;
    }
    .guide-section {
        font-size: 13.5px;
        font-weight: 700;
        color: #000000 !important;
        margin-top: 8px;
        margin-bottom: 4px;
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
st.markdown("<div class='main-title'>GIÁM SÁT ĐỒNG BỘ TOÀN DIỆN NHÀ MÁY ĐIỆN RÁC EFGT</div>", unsafe_allow_html=True)

# BẢNG ĐIỀU KHIỂN & Ô NHẬP TẢI RÁC
col_ctrl1, col_ctrl2, col_input = st.columns([1, 1, 3])

with col_ctrl1:
    if st.button("Bắt đầu / Dừng", use_container_width=True):
        st.session_state.running = not st.session_state.running

with col_ctrl2:
    if st.button("Reset", use_container_width=True):
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
        "Nhập lượng rác nạp (g/s):",
        min_value=10.0,
        max_value=500.0,
        value=float(st.session_state.base_fuel),
        step=1.0,
        disabled=st.session_state.running,
        help="Nhập số từ 10.0 đến 500.0 g/s khi hệ thống đang dừng"
    )
    if not st.session_state.running:
        st.session_state.base_fuel = fuel_input

# --- HÀM VẼ SƠ ĐỒ HỆ THỐNG SVG (NỀN TRẮNG, CHỮ ĐEN) ---
def tao_so_do_svg_moi(is_running=False, fuel_grams=85.0):
    fan_class = "fan-spinning" if is_running else ""

    svg_lines = [
        '<svg viewBox="0 0 880 540" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" style="background-color: #ffffff; border-radius: 10px; border: 1.5px solid #000000; padding: 5px;">',
        '<defs>',
        '<marker id="arr-black" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#000000"/></marker>',
        '<marker id="arr-purple" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse"><path d="M 0 1.2 L 7.5 5 L 0 8.8 z" fill="#d59bf6"/></marker>',
        '<marker id="arr-orange" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto-start-reverse"><path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#df6d27"/></marker>',
        '<marker id="arr-green" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#9be15d"/></marker>',
        '<marker id="arr-blue" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#0b6399"/></marker>',
        '<style>',
        '@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }',
        f'.fan-spinning {{ transform-origin: center; transform-box: fill-box; animation: spin 0.6s linear infinite; }}',
        '.text-node { font-family: "Segoe UI", Roboto, Arial, sans-serif; font-size: 13.5px; font-weight: 700; }',
        '.legend-text { font-family: "Segoe UI", Roboto, Arial, sans-serif; font-size: 11.5px; font-weight: 700; fill: #000000; }',
        '</style>',
        '</defs>',

        '<!-- 1. KHỐI HTHE XANH LÁ (GÓC TRÊN TRÁI) -->',
        '<rect x="145" y="105" width="105" height="54" fill="#2ea44f" rx="10"/>',
        '<text x="197.5" y="137" fill="#ffffff" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="15" font-weight="bold" text-anchor="middle">HTHE</text>',

        '<!-- 2. KHỐI OUTPUT (GÓC TRÊN PHẢI) -->',
        '<rect x="570" y="20" width="155" height="58" fill="#b23a3a" rx="10"/>',
        '<text x="647.5" y="56" fill="#ffffff" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="22" font-weight="bold" text-anchor="middle">Output</text>',
        '<line x1="725" y1="49" x2="805" y2="49" stroke="#000000" stroke-width="3.5" marker-end="url(#arr-black)"/>',

        '<!-- 3. BỘ HTHE GIÁN TIẾP (ĐỘNG CƠ STIRLING) -->',
        '<text x="457.5" y="73" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="11.5" font-weight="bold" text-anchor="middle">Nhiệt năng &#8594; Điện năng</text>',
        '<rect x="375" y="80" width="165" height="52" fill="#b23a3a" rx="10"/>',
        '<text x="457.5" y="102" fill="#ffffff" class="text-node" text-anchor="middle">Bộ HTHE Gián tiếp</text>',
        '<text x="457.5" y="120" fill="#ffffff" class="text-node" text-anchor="middle">(Động cơ Stirling)</text>',

        '<!-- 4. NHÃN KHÔNG KHÍ & LUỒNG KHÍ SẠCH (MÀU TÍM NHẠT) -->',
        '<text x="102" y="242" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle">Không khí</text>',
        '<line x1="158" y1="236" x2="258" y2="236" stroke="#d59bf6" stroke-width="9" marker-end="url(#arr-purple)"/>',
        '<line x1="352" y1="236" x2="603" y2="236" stroke="#d59bf6" stroke-width="9" marker-end="url(#arr-purple)"/>',
        '<path d="M 656 277 L 656 384 L 562 384" fill="none" stroke="#d59bf6" stroke-width="9" marker-end="url(#arr-purple)"/>',
        '<text x="615" y="407" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle">Khí sạch nóng</text>',

        '<!-- 5. MÁY NÉN KHÍ (BÊN TRÁI) -->',
        '<rect x="270" y="195" width="82" height="82" fill="#000000" rx="18"/>',
        f'<g transform="translate(311, 236)"><g class="{fan_class}">',
        '<line x1="-20" y1="0" x2="20" y2="0" stroke="#ffffff" stroke-width="6" stroke-linecap="round"/>',
        '<line x1="0" y1="-20" x2="0" y2="20" stroke="#ffffff" stroke-width="6" stroke-linecap="round"/>',
        '</g></g>',
        '<text x="311" y="298" fill="#000000" class="text-node" text-anchor="middle">Máy nén khí</text>',

        '<!-- 6. TUABIN KHÍ (BÊN PHẢI) -->',
        '<rect x="615" y="195" width="82" height="82" fill="#000000" rx="18"/>',
        f'<g transform="translate(656, 236)"><g class="{fan_class}">',
        '<line x1="-20" y1="0" x2="20" y2="0" stroke="#ffffff" stroke-width="6" stroke-linecap="round"/>',
        '<line x1="0" y1="-20" x2="0" y2="20" stroke="#ffffff" stroke-width="6" stroke-linecap="round"/>',
        '</g></g>',
        '<text x="708" y="241" fill="#000000" class="text-node" text-anchor="start">Tuabin khí</text>',

        '<!-- 7. DÒNG ĐIỆN (MÀU ĐEN) -->',
        '<line x1="656" y1="195" x2="656" y2="86" stroke="#000000" stroke-width="3.5" marker-end="url(#arr-black)"/>',
        '<text x="666" y="145" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="11.5" font-weight="bold">Động năng &#8594; Điện năng</text>',

        '<path d="M 570 49 L 298 49 L 298 187" fill="none" stroke="#000000" stroke-width="3.5" marker-end="url(#arr-black)"/>',
        '<path d="M 375 106 L 324 106 L 324 187" fill="none" stroke="#000000" stroke-width="3.5" marker-end="url(#arr-black)"/>',

        '<!-- 8. NHIỆT TỪ LÒ ĐỐT (MÀU CAM NÉT ĐỨT) -->',
        '<line x1="422" y1="350" x2="422" y2="250" stroke="#df6d27" stroke-width="4" stroke-dasharray="9,5" marker-end="url(#arr-orange)"/>',
        '<text x="456" y="275" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle">Nhiệt</text>',
        '<text x="456" y="291" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle">làm</text>',
        '<text x="456" y="307" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle">nóng</text>',
        '<text x="456" y="323" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle">khí</text>',

        '<line x1="490" y1="350" x2="490" y2="140" stroke="#df6d27" stroke-width="4" stroke-dasharray="9,5" marker-end="url(#arr-orange)"/>',
        '<text x="526" y="280" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle">Nhiệt</text>',
        '<text x="526" y="297" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle">dư</text>',

        '<!-- 9. LÒ ĐỐT RÁC NGOÀI (GIỮA DƯỚI) -->',
        '<rect x="385" y="350" width="165" height="68" fill="#df6d27" rx="12"/>',
        '<text x="467.5" y="380" fill="#000000" class="text-node" text-anchor="middle">Lò đốt</text>',
        '<text x="467.5" y="400" fill="#000000" class="text-node" text-anchor="middle">rác ngoài</text>',

        '<!-- 10. HỆ THỐNG LỌC KHÍ THẢI & KHÓI THẢI LÒ (XANH LÁ NHẠT) -->',
        '<rect x="50" y="350" width="185" height="68" fill="#bcf569" rx="12"/>',
        '<text x="142.5" y="371" fill="#000000" class="text-node" text-anchor="middle">Hệ thống</text>',
        '<text x="142.5" y="389" fill="#000000" class="text-node" text-anchor="middle">lọc, thu giữ</text>',
        '<text x="142.5" y="407" fill="#000000" class="text-node" text-anchor="middle">khí thải</text>',

        '<line x1="385" y1="384" x2="243" y2="384" stroke="#9be15d" stroke-width="4" marker-end="url(#arr-green)"/>',
        '<text x="312" y="372" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle">Khói thải lò</text>',

        '<!-- 11. RÁC THẢI ĐẦU VÀO & SẤY KHÔ RÁC -->',
        '<text x="172" y="468" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="17" font-weight="bold" text-anchor="middle">Rác thải</text>',
        '<text x="172" y="490" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="17" font-weight="bold" text-anchor="middle">đầu vào</text>',

        '<line x1="232" y1="482" x2="437" y2="482" stroke="#0b6399" stroke-width="3.5" marker-end="url(#arr-blue)"/>',
        '<text x="335" y="458" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle">Loại bỏ rác không</text>',
        '<text x="335" y="474" fill="#000000" font-family="Segoe UI, Roboto, Arial, sans-serif" font-size="12" font-weight="bold" text-anchor="middle">cháy được</text>',

        '<rect x="445" y="455" width="140" height="50" fill="#b23a3a" rx="10"/>',
        '<text x="515" y="485" fill="#ffffff" class="text-node" text-anchor="middle">Sấy khô rác</text>',

        '<!-- MŨI TÊN NỐI GIỮA LÒ ĐỐT VÀ SẤY KHÔ RÁC -->',
        '<line x1="462" y1="455" x2="462" y2="425" stroke="#0b6399" stroke-width="3.5" marker-end="url(#arr-blue)"/>',
        '<line x1="515" y1="418" x2="515" y2="448" stroke="#df6d27" stroke-width="4" stroke-dasharray="7,4" marker-end="url(#arr-orange)"/>',

        '<!-- 12. BẢNG CHÚ GIẢI GÓC DƯỚI PHẢI -->',
        '<g transform="translate(610, 442)">',
        '<line x1="0" y1="10" x2="32" y2="10" stroke="#000000" stroke-width="3.5" marker-end="url(#arr-black)"/>',
        '<text x="42" y="14" class="legend-text">Hướng đi của dòng điện</text>',
        '<line x1="0" y1="30" x2="32" y2="30" stroke="#9be15d" stroke-width="3.5" marker-end="url(#arr-green)"/>',
        '<text x="42" y="34" class="legend-text">Hướng đi của luồng khí thải</text>',
        '<line x1="0" y1="50" x2="32" y2="50" stroke="#d59bf6" stroke-width="4.5" marker-end="url(#arr-purple)"/>',
        '<text x="42" y="54" class="legend-text">Hướng đi của luồng khí sạch</text>',
        '<line x1="0" y1="70" x2="32" y2="70" stroke="#df6d27" stroke-width="3.5" marker-end="url(#arr-orange)"/>',
        '<text x="42" y="74" class="legend-text">Hướng đi của nhiệt từ lò đốt</text>',
        '</g>',

        '</svg>'
    ]

    return "".join(svg_lines)

# CHIA BỐ CỤC 2 CỘT
col_left, col_right = st.columns([1, 1])

svg_fuel = st.session_state.y_fuel[-1] if (st.session_state.running and st.session_state.y_fuel) else st.session_state.base_fuel

# --- CỘT TRÁI: SƠ ĐỒ HỆ THỐNG ---
with col_left:
    st.markdown("<p style='font-size: 13px; font-weight: 800; color: #000000; margin-bottom: 4px;'>SƠ ĐỒ HỆ THỐNG EFGT</p>", unsafe_allow_html=True)
    svg_code = tao_so_do_svg_moi(st.session_state.running, svg_fuel)
    st.markdown(svg_code, unsafe_allow_html=True)

def render_chart():
    if not st.session_state.x_data:
        return None
    
    # Giữ toàn bộ dữ liệu từ 1s để không bị mất khi kéo/pan lại biểu đồ
    x_all = st.session_state.x_data
    y_fuel_all = st.session_state.y_fuel
    y_power_all = st.session_state.y_power

    # Khung nhìn mặc định hiển thị 20 giây gần nhất
    x_max = x_all[-1]
    x_min = max(1, x_max - 19)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12)

    fig.add_trace(go.Scatter(
        x=x_all,
        y=y_fuel_all,
        mode='lines+markers',
        name='Tải Rác',
        line=dict(color='#dc2626', width=2.5),
        marker=dict(size=6, color='#dc2626'),
        hovertemplate="<b>Thời gian:</b> %{x}s<br><b>Lượng rác đưa vào hệ thống:</b> %{y:.1f} g/s<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x_all,
        y=y_power_all,
        mode='lines+markers',
        name='Điện Lưới',
        line=dict(color='#0284c7', width=2.5),
        marker=dict(size=6, color='#0284c7'),
        hovertemplate="<b>Thời gian:</b> %{x}s<br><b>Lượng điện tạo ra trong 1 giờ:</b> %{y:.2f} kWh<extra></extra>"
    ), row=2, col=1)

    fig.update_layout(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#000000', family="Segoe UI, Roboto, Arial, sans-serif"),
        margin=dict(l=15, r=15, t=10, b=45),
        height=335,
        showlegend=False,
        dragmode="pan",
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#ffffff",
            bordercolor="#000000",
            font=dict(color="#000000", size=11, family="Segoe UI, Roboto, Arial, sans-serif")
        )
    )

    fig.update_xaxes(
        range=[x_min - 0.5, x_max + 0.5],
        gridcolor='#e2e8f0',
        linecolor='#000000',
        linewidth=1,
        showgrid=True,
        zeroline=False,
        tickfont=dict(color='#000000', size=10)
    )
    fig.update_yaxes(
        gridcolor='#e2e8f0',
        linecolor='#000000',
        linewidth=1,
        showgrid=True,
        zeroline=False,
        tickfont=dict(color='#000000', size=10)
    )
    fig.update_yaxes(title_text="Rác (g/s)", title_font=dict(color="#000000", size=11), row=1, col=1)
    fig.update_yaxes(title_text="Điện (kWh)", title_font=dict(color="#000000", size=11), row=2, col=1)
    fig.update_xaxes(title_text="Thời gian (s)", title_font=dict(color="#000000", size=11), row=2, col=1)

    return fig

# --- CỘT PHẢI: BIỂU ĐỒ REAL-TIME & METRIC ---
with col_right:
    st.markdown("<p style='font-size: 13px; font-weight: 800; color: #000000; margin-bottom: 4px;'>BIỂU ĐỒ REAL-TIME</p>", unsafe_allow_html=True)
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
    else:
        st.markdown(
            "<div style='height: 335px; background-color: #ffffff; border: 1.5px solid #000000; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #000000; font-size: 13px; font-weight: 600;'>Nhấn «Bắt đầu / Dừng» để hiển thị biểu đồ thời gian thực</div>",
            unsafe_allow_html=True
        )

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

    st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns([1.05, 1.45, 0.85, 1.35])
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-label">Lượng rác đưa vào<br>hệ thống</div>
            <div class="metric-card-value">{current_fuel:.1f} g/s</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-label">
                Lượng điện tạo ra trong 1 giờ
                <span class="metric-card-sub">(Tính từ lượng rác đưa vào hệ thống)</span>
            </div>
            <div class="metric-card-value">{current_power:.2f} kWh</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-label">Nhiệt Độ Khí</div>
            <div class="metric-card-value">{current_t4:.1f} °C</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-label">Tổng lượng điện tạo ra<br>tính từ lúc khởi động hệ thống</div>
            <div class="metric-card-value">{current_energy:.4f} kW</div>
        </div>
        """, unsafe_allow_html=True)

# --- HƯỚNG DẪN SỬ DỤNG MÔ PHỎNG ---
st.markdown("""
<div class="guide-box">
    <div class="guide-title">HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH MÔ PHỎNG MÔ HÌNH EFGT</div>
    <div class="guide-section">Tính toán năng lượng tạo ra trong 1 giây từ lượng rác đầu vào được cố định</div>
    <ul style="margin: 0 0 8px 0; padding-left: 20px; color: #000000;">
        <li><b>Thiết lập lưu lượng rác nạp:</b> Nhập giá trị lượng rác đầu vào (từ <b>10.0</b> đến <b>500.0 g/s</b>) vào ô <i>«Nhập lượng rác nạp (g/s)»</i>. Lưu ý: Chỉ điều chỉnh được thông số này khi hệ thống đang ở trạng thái <b>Dừng</b>.</li>
    </ul>
    <div class="guide-section">Mô phỏng quá trình giả lập sử dụng chương trình mô phỏng mô hình EFGT</div>
    <ul style="margin: 0; padding-left: 20px; color: #000000;">
        <li><b>Bước 1: Vận hành mô phỏng:</b> Nhấn nút <b>«Bắt đầu / Dừng»</b> để khởi chạy hoặc tạm dừng quá trình mô phỏng theo thời gian thực (cập nhật mỗi 1 giây, cánh quạt máy nén khí và tuabin khí sẽ xoay đồng bộ).</li>
        <li><b>Bước 2: Quan sát sơ đồ &amp; biểu đồ:</b> Theo dõi hướng dịch chuyển của dòng khí, nhiệt, rác thải và dòng điện trên <b>Sơ đồ hệ thống EFGT</b> (bên trái) cùng đồ thị biến thiên <b>Tải Rác</b> và <b>Điện Lưới</b> (bên phải).</li>
        <li><b>Bước 3: Tra cứu dữ liệu tại từng thời điểm:</b> Nhấp chuột trực tiếp vào bất kỳ điểm nào trên <b>Biểu đồ Real-time</b> để xem lại chính xác các chỉ số <i>Lượng rác đưa vào hệ thống</i>, <i>Lượng điện tạo ra trong 1 giờ</i>, <i>Nhiệt Độ Khí</i> và <i>Tổng lượng điện tạo ra tính từ lúc khởi động hệ thống</i> tại giây đó.</li>
        <li><b>Bước 4: Khởi tạo lại (Reset):</b> Nhấn nút <b>«Reset»</b> để xóa toàn bộ lịch sử biểu đồ, đưa thời gian và điện năng tích lũy về <b>0</b> trước khi chạy kịch bản mới.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

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
