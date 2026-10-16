import time
import random
import math
import streamlit as st
import matplotlib.pyplot as plt

# Cấu hình trang
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

st.title("⚡ GIÁM SÁT ĐỒNG BỘ TOÀN DIỆN NHÀ MÁY ĐIỆN RÁC EFGT")

# Thanh điều khiển ở thanh bên (Sidebar)
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

# Thẻ hiển thị chỉ số LED
m1, m2, m3, m4 = st.columns(4)

current_fuel = st.session_state.y_fuel[-1] if st.session_state.y_fuel else 0.0
current_power = st.session_state.y_power[-1] if st.session_state.y_power else 0.0
current_t4 = st.session_state.y_t4[-1] if st.session_state.y_t4 else 0.0
current_energy = st.session_state.total_energy_kwh

m1.metric("🔥 Rác Nạp Vào", f"{current_fuel:.1f} g/s")
m2.metric("⚡ Công Suất Thực Lưới", f"{current_power:.2f} kW")
m3.metric("🌡️ Khí Hoàn Lưu (T4)", f"{current_t4:.1f} °C")
m4.metric("🔋 Điện Tích Lũy", f"{current_energy:.4f} kWh")

# Khu vực vẽ biểu đồ
chart_placeholder = st.empty()

def draw_chart():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.patch.set_facecolor('#0f172a')
    
    for ax in (ax1, ax2):
        ax.set_facecolor('#1e293b')
        ax.tick_params(colors='#cbd5e1', labelsize=9)
        ax.grid(True, linestyle=":", alpha=0.3)
        for spine in ax.spines.values():
            spine.set_color('#475569')

    # Lấy 20 điểm dữ liệu gần nhất để hiển thị
    x_vis = st.session_state.x_data[-20:]
    y_fuel_vis = st.session_state.y_fuel[-20:]
    y_power_vis = st.session_state.y_power[-20:]

    ax1.set_ylabel("Tải Rác (g/s)", color="#f43f5e", fontweight="bold")
    ax1.plot(x_vis, y_fuel_vis, color="#f43f5e", marker="o", linewidth=2)

    ax2.set_ylabel("Điện lưới (kW)", color="#38bdf8", fontweight="bold")
    ax2.set_xlabel("Thời gian (giây)", color="#cbd5e1")
    ax2.plot(x_vis, y_power_vis, color="#38bdf8", marker="o", linewidth=2)

    plt.tight_layout()
    return fig

# Vòng lập cập nhật dữ liệu tự động
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

    chart_placeholder.pyplot(draw_chart())
    time.sleep(1)
    st.rerun()
else:
    if st.session_state.x_data:
        chart_placeholder.pyplot(draw_chart())