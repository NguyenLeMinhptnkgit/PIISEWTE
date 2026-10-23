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
# 2. HÀM HIỂN THỊ SƠ ĐỒ SVG ĐỘNG
# ==========================================
def render_efgt_diagram():
    svg_code = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 500" width="100%" height="100%" style="background-color: #ffffff; font-family: Arial, sans-serif;">
      <defs>
        <!-- Mũi tên đầu đường ống -->
        <marker id="arrow-black" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#000000"/>
        </marker>
        
        <!-- Hiệu ứng quay cánh quạt -->
        <style>
          @keyframes spin-cw {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          .spinning-fan-compressor {
            animation: spin-cw 2.0s linear infinite;
            transform-origin: 0px 0px;
          }
          .spinning-fan-turbine {
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
      <line x1="130" y1="310" x2="230" y2="310" stroke="#000000" stroke-width="3.5" marker-end="url(#arrow-black)" />
      
      <!-- 2. Trục kết nối thẳng giữa Máy nén khí và Tuabin khí -->
      <line x1="330" y1="310" x2="580" y2="310" stroke="#000000" stroke-width="3.5" />

      <!-- 3. Máy nén khí -> Bộ HTHE Gián tiếp (Lên rồi qua phải) -->
      <path d="M 280 260 L 280 190 L 345 190" fill="none" stroke="#000000" stroke-width="3.5" stroke-linejoin="round" marker-end="url(#arrow-black)" />

      <!-- 4. Bộ HTHE Gián tiếp -> Tuabin khí (Qua phải rồi xuống) -->
      <path d="M 515 190 L 630 190 L 630 260" fill="none" stroke="#000000" stroke-width="3.5" stroke-linejoin="round" marker-end="url(#arrow-black)" />

      <!-- 5. Tuabin khí -> Lò đốt rác ngoài (Xuống rồi qua trái) -->
      <path d="M 630 360 L 630 420 L 510 420" fill="none" stroke="#000000" stroke-width="3.5" stroke-linejoin="round" marker-end="url(#arrow-black)" />

      <!-- 6. Bộ HTHE Gián tiếp -> Hệ thống lọc (Lên rồi qua trái) -->
      <path d="M 430 150 L 430 110 L 295 110" fill="none" stroke="#000000" stroke-width="3.5" stroke-linejoin="round" marker-end="url(#arrow-black)" />

      <!-- 7. Đường nét đứt màu cam (Lò đốt rác ngoài -> Bộ HTHE Gián tiếp) -->
      <line x1="430" y1="380" x2="430" y2="230" stroke="#e06d1b" stroke-width="2.5" stroke-dasharray="6,4" />

      <!-- ==================== NHÃN CHÚ THÍCH DÒNG KHÍ ==================== -->
      <text x="362" y="128" class="bold-text" font-size="15">Khói thải lò</text>
      <text x="570" y="442" class="bold-text" font-size="15">Khí sạch nóng</text>

      <!-- ==================== MÔ-ĐUN CÁC KHỐI ==================== -->

      <!-- 1. Hệ Thống lọc, thu giữ khí thải (Góc trên trái - Xanh lá) -->
      <g>
        <rect x="125" y="70" width="170" height="80" rx="14" fill="#b5f55a" />
        <text x="210" y="98" class="bold-text" font-size="15">Hệ Thống lọc,</text>
        <text x="210" y="120" class="bold-text" font-size="15">thu giữ khí thải</text>
      </g>

      <!-- 2. Bộ HTHE Gián tiếp (Giữa trên - Đỏ nâu) -->
      <g>
        <rect x="345" y="150" width="170" height="80" rx="12" fill="#b34242" />
        <text x="430" y="190" class="bold-text" font-size="16">Bộ HTHE Gián tiếp</text>
      </g>

      <!-- 3. Lò đốt rác ngoài (Giữa dưới - Cam) -->
      <g>
        <rect x="350" y="380" width="160" height="80" rx="12" fill="#e06d1b" />
        <text x="430" y="420" class="bold-text" font-size="16">Lò đốt rác ngoài</text>
      </g>

      <!-- 4. Máy nén khí (Đen + Cánh quạt quay) -->
      <g>
        <rect x="230" y="260" width="100" height="100" rx="22" fill="#000000" />
        <!-- Cánh quạt xoay tròn -->
        <g transform="translate(280, 310)">
          <g class="spinning-fan-compressor">
            <circle cx="0" cy="0" r="7" fill="#ffffff" />
            <path d="M -5,-34 C -5,-37 5,-37 5,-34 L 4,-7 L 34,-4 C 37,-4 37,5 34,5 L 7,4 L 5,34 C 5,37 -5,37 -5,34 L -4,7 L -34,4 C -37,4 -37,-5 -34,-5 L -7,-4 Z" fill="#ffffff" />
          </g>
        </g>
        <text x="280" y="385" class="bold-text" font-size="16">Máy nén khí</text>
      </g>

      <!-- 5. Tuabin khí (Đen + Cánh quạt quay) -->
      <g>
        <rect x="580" y="260" width="100" height="100" rx="22" fill="#000000" />
        <!-- Cánh quạt xoay tròn -->
        <g transform="translate(630, 310)">
          <g class="spinning-fan-turbine">
            <circle cx="0" cy="0" r="7" fill="#ffffff" />
            <path d="M -5,-34 C -5,-37 5,-37 5,-34 L 4,-7 L 34,-4 C 37,-4 37,5 34,5 L 7,4 L 5,34 C 5,37 -5,37 -5,34 L -4,7 L -34,4 C -37,4 -37,-5 -34,-5 L -7,-4 Z" fill="#ffffff" />
          </g>
        </g>
        <text x="630" y="385" class="bold-text" font-size="16">Tuabin khí</text>
      </g>
    </svg>
    """
    components.html(svg_code, height=480)

# ==========================================
# 3. GIAO DIỆN CHÍNH STREAMLIT
# ==========================================
st.title("🔥 Hệ Thống Giám Sát & Mô Phỏng Nhà Máy Điện Rác EFGT")

# Khởi tạo SESSION STATE
if "running" not in st.session_state:
    st.session_state.running = False
if "x_data" not in st.session_state:
    st.session_state.x_data = []
if "y_fuel" not in st.session_state:
    st.session_state.y_fuel = []
if "y_power" not in st.session_state:
    st.session_state.y_power = []
if "step" not in st.session_state:
    st.session_state.step = 0

# THANH ĐIỀU KHIỂN (SIDEBAR)
st.sidebar.header("⚙️ Thông Số Vận Hành")
m_fuel_ton_h = st.sidebar.slider("Lượng rác nạp (tấn/giờ)", min_value=1.0, max_value=20.0, value=8.5, step=0.5)
lhv_val = st.sidebar.number_input("Nhiệt trị thấp LHV (kJ/kg)", value=9500, step=200)
eta_comb_val = st.sidebar.slider("Hiệu suất buồng đốt (%)", min_value=50, max_value=95, value=82) / 100.0

st.sidebar.markdown("---")
st.sidebar.header("🕹️ Bộ Điều Khuển Mô Phỏng")
col_btn1, col_btn2, col_btn3 = st.sidebar.columns(3)

if col_btn1.button("▶ Start"):
    st.session_state.running = True
if col_btn2.button("⏸ Pause"):
    st.session_state.running = False
if col_btn3.button("🔄 Reset"):
    st.session_state.running = False
    st.session_state.x_data = []
    st.session_state.y_fuel = []
    st.session_state.y_power = []
    st.session_state.step = 0
    st.rerun()

# BỐ CỤC CHÍNH (2 CỘT)
col_left, col_right = st.columns([1.1, 0.9])

with col_left:
    st.subheader("📌 Sơ Đồ Nguyên Lý Động (EFGT Cycle)")
    render_efgt_diagram()

with col_right:
    st.subheader("📊 Biểu Đồ Vận Hành Theo Thời Gian Real-time")
    chart_placeholder = st.empty()

# BẢNG CHỈ SỐ METRICS
st.markdown("---")
st.subheader("⚡ Chỉ Số Kỹ Thuật Hiện Tai")
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

# Tính toán giá trị hiện tại
m_fuel_sec = (m_fuel_ton_h * 1000) / 3600.0
res = tinh_toan_nguoc_efgt(m_fuel_sec, lhv_kjkg=lhv_val, eta_comb=eta_comb_val)

metric_col1.metric("Công suất phát điện", f"{res['P_elec'] / 1000.0:.2f} MW")
metric_col2.metric("Hiệu suất nhiệt tổng", f"{res['eta_plant']:.2f} %")
metric_col3.metric("Nhiệt độ sau máy nén (T2)", f"{res['T2_C']:.1f} °C")
metric_col4.metric("Nhiệt độ khí thải Tuabin (T4)", f"{res['T4_C']:.1f} °C")

# VÒNG LẶP CẬP NHẬT DỮ LIỆU REAL-TIME
if st.session_state.running:
    st.session_state.step += 1
    t_curr = st.session_state.step

    # Thêm độ biến động ngẫu nhiên thực tế (Noise)
    noise_fuel = random.uniform(-0.15, 0.15)
    current_fuel_sec = max(0.1, m_fuel_sec + noise_fuel)
    current_res = tinh_toan_nguoc_efgt(current_fuel_sec, lhv_kjkg=lhv_val, eta_comb=eta_comb_val)

    st.session_state.x_data.append(t_curr)
    st.session_state.y_fuel.append(current_fuel_sec * 3.6)  # Đổi ra tấn/h
    st.session_state.y_power.append(current_res["P_elec"] / 1000.0)  # MW

    # Giới hạn bộ nhớ đệm (lưu tối đa 60 điểm dữ liệu gần nhất)
    if len(st.session_state.x_data) > 60:
        st.session_state.x_data.pop(0)
        st.session_state.y_fuel.pop(0)
        st.session_state.y_power.pop(0)

# DỰNG ĐỒ THỊ PLOTLY
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=st.session_state.x_data,
    y=st.session_state.y_power,
    mode='lines+markers',
    name='Công suất (MW)',
    line=dict(color='#00CC96', width=3)
))
fig.add_trace(go.Scatter(
    x=st.session_state.x_data,
    y=st.session_state.y_fuel,
    mode='lines+markers',
    name='Lượng rác (tấn/h)',
    yaxis='y2',
    line=dict(color='#EF553B', width=2, dash='dot')
))

fig.update_layout(
    xaxis=dict(title="Thời gian (giây)"),
    yaxis=dict(title="Công suất phát (MW)", titlefont=dict(color="#00CC96"), tickfont=dict(color="#00CC96")),
    yaxis2=dict(title="Lượng rác nạp (tấn/h)", titlefont=dict(color="#EF553B"), tickfont=dict(color="#EF553B"), overlaying='y', side='right'),
    legend=dict(x=0.01, y=0.99),
    margin=dict(l=20, r=20, t=30, b=20),
    height=380
)

chart_placeholder.plotly_chart(fig, use_container_width=True)

# TỰ ĐỘNG LOAD LẠI TRANG KHI ĐANG CHẠY
if st.session_state.running:
    time.sleep(1)
    st.rerun()
