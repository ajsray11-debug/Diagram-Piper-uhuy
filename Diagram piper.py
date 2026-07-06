import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

def bersihkan_dataframe(df):
    """
    Fungsi untuk membersihkan struktur data Excel/CSV,
    membuang baris kosong di atas, dan memastikan format numerik.
    """
    for i in range(min(5, len(df))):
        row_str = df.iloc[i].astype(str).str.upper().str.strip().tolist()
        if any('CA' in s or 'NO SAMPEL' in s or 'HCO3' in s for s in row_str):
            new_columns = df.iloc[i].astype(str).str.strip().tolist()
            df.columns = new_columns
            df = df.iloc[i+1:].reset_index(drop=True)
            break
            
    df.columns = df.columns.str.strip()
    df = df.loc[:, df.columns.notna() & (df.columns != 'nan') & (df.columns != '')]
    
    kolom_ion = ['Ca', 'Mg', 'Na', 'K', 'HCO3', 'SO4', 'Cl']
    for col in kolom_ion:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    df = df.dropna(subset=[c for c in kolom_ion if c in df.columns], how='any')
    return df

def kalkulasi_koordinat_piper(ca, mg, na_k, hco3_co3, so4, cl, shift_factor=0.82):
    """
    Kalkulasi koordinat titik dengan shift_factor yang disinkronkan.
    """
    sin60 = np.sin(np.pi / 3)
    dy = 100 * sin60
    sh_y = shift_factor * dy
    
    cat_x = na_k + 0.5 * mg
    cat_y = (mg * sin60) + sh_y
    
    offset_anion = 120
    an_x = offset_anion + cl + 0.5 * so4
    an_y = (so4 * sin60) + sh_y
    
    x_dia = 110 + 0.5 * na_k - 0.5 * hco3_co3
    y_dia = dy * (3 - (na_k + hco3_co3) / 100)
    
    return cat_x, cat_y, an_x, an_y, x_dia, y_dia

def interpretasi_hydrochemical(ca_pct, mg_pct, na_k_pct, hco3_pct, so4_pct, cl_pct):
    """
    Logika matematika untuk menentukan tipe kation, anion, dan fasies diamond
    yang disinkronkan secara geometris dengan pembagian zona grafik.
    """
    # 1. Interpretasi Tipe Kation
    if ca_pct > 50:
        kation = 'Calcium type'
    elif mg_pct > 50:
        kation = 'Magnesium type'
    elif na_k_pct > 50:
        kation = 'Sodium and potassium type'
    else:
        kation = 'No dominant type'
        
    # 2. Interpretasi Tipe Anion
    if hco3_pct > 50:
        anion = 'Bicarbonate type'
    elif so4_pct > 50:
        anion = 'Sulphate type'
    elif cl_pct > 50:
        anion = 'Chloride type'
    else:
        anion = 'No dominant type'
        
    # 3. Interpretasi Fasies Air (Diamond Zone)
    sum_na_hco3 = na_k_pct + hco3_pct
    if sum_na_hco3 < 50:
        fasies = 'Calcium chloride type'
    elif sum_na_hco3 > 150:
        fasies = 'Sodium bicarbonate type'
    elif na_k_pct > 50 and hco3_pct < 50:
        fasies = 'Sodium chloride type'
    elif na_k_pct < 50 and hco3_pct > 50:
        fasies = 'Magnesium bicarbonate type'
    else:
        fasies = 'Mixed type'
        
    return kation, anion, fasies

# ==============================================================================
# --- FUNGSI TAMBAHAN: INTERPRETASI GENESA & LITOLOGI ---
# ==============================================================================
def hitung_genesa_litologi(df):
    interpretasi_list = []
    
    # Deteksi nama kolom sampel
    kolom_label = 'Sample_ID'
    for col in df.columns:
        if col.upper() in ['NO SAMPEL', 'SAMPEL', 'SAMPLE', 'SAMPLE_ID', 'ID', 'NO_SAMPEL']:
            kolom_label = col
            break
            
    for idx, row in df.iterrows():
        # Konversi mg/L ke meq/L agar konsisten & akurat secara hidrokimia
        ca_meq = row['Ca'] / 20.04
        mg_meq = row['Mg'] / 12.15
        na_meq = row['Na'] / 22.99
        k_meq = row['K'] / 39.10
        hco3_meq = row['HCO3'] / 61.02
        so4_meq = row['SO4'] / 48.03
        cl_meq = row['Cl'] / 35.45
        
        t_cat = ca_meq + mg_meq + na_meq + k_meq
        t_an = hco3_meq + so4_meq + cl_meq
        
        ca_pct = (ca_meq / t_cat) * 100
        mg_pct = (mg_meq / t_cat) * 100
        na_k_pct = ((na_meq + k_meq) / t_cat) * 100
        
        hco3_pct = (hco3_meq / t_an) * 100
        so4_pct = (so4_meq / t_an) * 100
        cl_pct = (cl_meq / t_an) * 100
        
        # Klasifikasi Genesa berdasarkan dominasi kuadran hidrogeokimia
        if (ca_pct + mg_pct > 50) and (hco3_pct > 50):
            fasies = "Ca-Mg-HCO3"
            genesa = "Air tawar dangkal (Fluvial/Meteorik). Kontrol utama berasal dari pelapukan batuan permukaan."
            litologi = "Batu gamping (Limestone), Dolomit, atau pelapukan batuan beku/metamorf kaya kalsium."
        elif (na_k_pct > 50) and (cl_pct > 50):
            fasies = "Na-Cl"
            genesa = "Air tanah salin akibat pengaruh laut, intrusi air asin pesisir, atau sisa air formasi purba (Connate water)."
            litologi = "Formasi batuan sedimen marin, endapan pantai, atau zona evaporit lapisan garam (Halit)."
        elif (na_k_pct > 50) and (hco3_pct > 50):
            fasies = "Na-HCO3"
            genesa = "Air tanah dalam (Deep Groundwater) dengan sirkulasi lambat. Mengalami proses pertukaran ion alami."
            litologi = "Batuan pasir (Sandstone) dalam atau formasi lempung/shale (Ion exchange mineral lempung)."
        elif (ca_pct + mg_pct > 50) and (so4_pct + cl_pct > 50) and (so4_pct > cl_pct):
            fasies = "Ca-Mg-SO4"
            genesa = "Pelarutan mineral evaporit sekunder atau pengaruh air asam tambang/vulkanik."
            litologi = "Lapisan batuan sedimen kaya Gipsum, Anhidrit, atau batuan dengan oksidasi Pirit."
        else:
            fasies = "Campuran (Mixed)"
            genesa = "Zona transisi dinamis akibat pencampuran (mixing) dua jenis sumber air tanah yang berbeda."
            litologi = "Aluvium campuran berselang-seling atau batas kontak antar formasi akuifer."
            
        label_sampel = row[kolom_label] if kolom_label in df.columns else f'S-{idx}'
        
        interpretasi_list.append({
            "ID Sampel": label_sampel,
            "Fasies Utama": fasies,
            "Genesa Pembentukan Air Tanah": genesa,
            "Indikasi Batuan/Litologi Utama": litologi
        })
        
    return pd.DataFrame(interpretasi_list)

def plot_piper(df):
    fig, ax = plt.subplots(figsize=(11, 11))
    ax.set_aspect('equal')
    
    sin60 = np.sin(np.pi / 3)
    dy = 100 * sin60
    
    shift_factor = 0.82
    sh_cx, sh_cy = 0, shift_factor * dy   
    sh_ax, sh_ay = 0, shift_factor * dy   
    
    # =========================================================
    # 1. PEWARNAAN ZONA FASIES (DIAMOND)
    # =========================================================
    ax.fill([110, 85, 135], [3*dy, 2.5*dy, 2.5*dy], color='#fff3ad', alpha=0.9, zorder=1) 
    ax.fill([85, 135, 110], [2.5*dy, 2.5*dy, 2*dy], color='#c8f299', alpha=0.9, zorder=1)
    ax.fill([85, 135, 110], [1.5*dy, 1.5*dy, 2*dy], color='#f29999', alpha=0.9, zorder=1)
    ax.fill([110, 85, 135], [dy, 1.5*dy, 1.5*dy], color='#9adaff', alpha=0.9, zorder=1) 
    ax.fill([60, 85, 110, 85], [2*dy, 2.5*dy, 2*dy, 1.5*dy], color='#dfb2f4', alpha=0.9, zorder=1)
    ax.fill([160, 135, 110, 135], [2*dy, 2.5*dy, 2*dy, 1.5*dy], color='#fec9e3', alpha=0.9, zorder=1)

    # =========================================================
    # 2. PEWARNAAN ZONA FASIES (SEGITIGA KATION)
    # =========================================================
    A = [0 + sh_cx, 0 + sh_cy]
    B = [100 + sh_cx, 0 + sh_cy]
    C = [50 + sh_cx, dy + sh_cy]
    M_AB = [50 + sh_cx, 0 + sh_cy]
    M_AC = [25 + sh_cx, 0.5 * dy + sh_cy]
    M_BC = [75 + sh_cx, 0.5 * dy + sh_cy]

    ax.add_patch(Polygon([A, M_AB, M_AC], facecolor="#5a746eff", edgecolor='darkgray', lw=0.5, alpha=0.85, zorder=1))
    ax.add_patch(Polygon([C, M_AC, M_BC], facecolor="#97c8bd", edgecolor='darkgray', lw=0.5, alpha=0.85, zorder=1))
    ax.add_patch(Polygon([B, M_BC, M_AB], facecolor="#beffdee3", edgecolor='darkgray', lw=0.5, alpha=0.85, zorder=1))
    ax.add_patch(Polygon([M_AB, M_AC, M_BC], facecolor='#ffffff', edgecolor='darkgray', lw=0.5, alpha=0.85, zorder=1))

    ax.text(25 + sh_cx, 0.16 * dy + sh_cy, 'Calcium\ntype', ha='center', va='center', fontsize=8, color='#2c3e50', weight='bold', zorder=4)
    ax.text(50 + sh_cx, 0.68 * dy + sh_cy, 'Magnesium\ntype', ha='center', va='center', fontsize=8, color='#2c3e50', weight='bold', zorder=4)
    ax.text(75 + sh_cx, 0.16 * dy + sh_cy, 'Sodium and\npotassium\ntype', ha='center', va='center', fontsize=8, color='#2c3e50', weight='bold', zorder=4)
    ax.text(50 + sh_cx, 0.33 * dy + sh_cy, 'No\ndominant\ntype', ha='center', va='center', fontsize=8, color='#7f8c8d', style='italic', zorder=4)

    # =========================================================
    # 3. PEWARNAAN ZONA FASIES (SEGITIGA ANION)
    # =========================================================
    offset_anion = 120
    P1 = [offset_anion + sh_ax, 0 + sh_ay]
    P2 = [offset_anion + 100 + sh_ax, 0 + sh_ay]
    P3 = [offset_anion + 50 + sh_ax, dy + sh_ay]        
    M_P1_P2 = [offset_anion + 50 + sh_ax, 0 + sh_ay]
    M_P1_P3 = [offset_anion + 25 + sh_ax, 0.5 * dy + sh_ay]
    M_P2_P3 = [offset_anion + 75 + sh_ax, 0.5 * dy + sh_ay]   

    ax.add_patch(Polygon([P3, M_P1_P3, M_P2_P3], facecolor='#f48fb1', edgecolor='darkgray', lw=0.5, alpha=0.85, zorder=1))
    ax.add_patch(Polygon([P1, M_P1_P2, M_P1_P3], facecolor='#fbcfe8', edgecolor='darkgray', lw=0.5, alpha=0.85, zorder=1))
    ax.add_patch(Polygon([P2, M_P2_P3, M_P1_P2], facecolor='#ff8a80', edgecolor='darkgray', lw=0.5, alpha=0.85, zorder=1))
    ax.add_patch(Polygon([M_P1_P2, M_P1_P3, M_P2_P3], facecolor='#ffffff', edgecolor='darkgray', lw=0.5, alpha=0.85, zorder=1))

    ax.text(offset_anion + 50 + sh_ax, 0.68 * dy + sh_ay, 'Sulphate\ntype', ha='center', va='center', fontsize=8, color='#2c3e50', weight='bold', zorder=4)
    ax.text(offset_anion + 25 + sh_ax, 0.16 * dy + sh_ay, 'Bicarbonate\ntype', ha='center', va='center', fontsize=8, color='#2c3e50', weight='bold', zorder=4)
    ax.text(offset_anion + 75 + sh_ax, 0.16 * dy + sh_ay, 'Chloride\ntype', ha='center', va='center', fontsize=8, color='#2c3e50', weight='bold', zorder=4)
    ax.text(offset_anion + 50 + sh_ax, 0.33 * dy + sh_ay, 'No\ndominant\ntype', ha='center', va='center', fontsize=8, color='#7f8c8d', style='italic', zorder=4)

    # =========================================================
    # 4. GRID LINES & INTERNAL LABELS
    # =========================================================
    for i in range(20, 100, 20):
        ax.plot([i + sh_cx, i/2 + sh_cx], [0 + sh_cy, i*sin60 + sh_cy], 'k--', lw=0.5, alpha=0.3, zorder=2)
        ax.plot([100-i + sh_cx, 100-i/2 + sh_cx], [0 + sh_cy, i*sin60 + sh_cy], 'k--', lw=0.5, alpha=0.3, zorder=2)
        ax.plot([i/2 + sh_cx, 100-i/2 + sh_cx], [i*sin60 + sh_cy, i*sin60 + sh_cy], 'k--', lw=0.5, alpha=0.3, zorder=2)
        
        ax.text(i/2 - 2 + sh_cx, i*sin60 + sh_cy, f"{i}", fontsize=8, ha='right', va='center', color='#333333', zorder=4)
        ax.text(100 - i + sh_cx, -3 + sh_cy, f"{i}", fontsize=8, ha='center', va='top', color='#333333', zorder=4)
        ax.text(50 + i/2 + 2 + sh_cx, (100 - i)*sin60 + sh_cy, f"{i}", fontsize=8, ha='left', va='center', color='#333333', zorder=4)

        ax.plot([offset_anion + i + sh_ax, offset_anion + i/2 + sh_ax], [0 + sh_ay, i*sin60 + sh_ay], 'k--', lw=0.5, alpha=0.3, zorder=2)
        ax.plot([offset_anion + 100-i + sh_ax, offset_anion + 100-i/2 + sh_ax], [0 + sh_ay, i*sin60 + sh_ay], 'k--', lw=0.5, alpha=0.3, zorder=2)
        ax.plot([offset_anion + i/2 + sh_ax, offset_anion + 100-i/2 + sh_ax], [i*sin60 + sh_ay, i*sin60 + sh_ay], 'k--', lw=0.5, alpha=0.3, zorder=2)
        
        ax.text(offset_anion + i/2 - 2 + sh_ax, i*sin60 + sh_ay, f"{100 - i}", fontsize=8, ha='right', va='center', color='#333333', zorder=4)
        ax.text(offset_anion + i + sh_ax, -3 + sh_ay, f"{i}", fontsize=8, ha='center', va='top', color='#333333', zorder=4)
        ax.text(offset_anion + 100 - i/2 + 2 + sh_ax, i*sin60 + sh_ay, f"{i}", fontsize=8, ha='left', va='center', color='#333333', zorder=4)

    for i in range(20, 100, 20):
        ax.plot([110-i/2, 160-i/2], [dy+i*sin60, 2*dy+i*sin60], 'k--', lw=0.4, alpha=0.2, zorder=2)
        ax.plot([110+i/2, 60+i/2], [dy+i*sin60, 2*dy+i*sin60], 'k--', lw=0.4, alpha=0.2, zorder=2)

    ax.plot([0 + sh_cx, 100 + sh_cx, 50 + sh_cx, 0 + sh_cx], [0 + sh_cy, 0 + sh_cy, dy + sh_cy, 0 + sh_cy], 'k-', lw=1.5, zorder=3)
    ax.plot([offset_anion + sh_ax, offset_anion + 100 + sh_ax, offset_anion + 50 + sh_ax, offset_anion + sh_ax], [0 + sh_ay, 0 + sh_ay, dy + sh_ay, 0 + sh_ay], 'k-', lw=1.5, zorder=3)
    ax.plot([110, 60, 110, 160, 110], [dy, 2*dy, 3*dy, 2*dy, dy], 'k-', lw=1.5, zorder=3)
    
    ax.plot([85, 135], [2.5*dy, 2.5*dy], 'k-', lw=1.2, zorder=3) 
    ax.plot([85, 135], [1.5*dy, 1.5*dy], 'k-', lw=1.2, zorder=3) 
    ax.plot([85, 110, 135], [2.5*dy, 2*dy, 2.5*dy], 'k-', lw=1.2, zorder=3) 
    ax.plot([85, 110, 135], [1.5*dy, 2*dy, 1.5*dy], 'k-', lw=1.2, zorder=3) 

    ax.text(110, 2.68*dy, 'Calcium\nchloride\ntype', ha='center', va='center', fontsize=9, color='#735c00', weight='bold', zorder=4)
    ax.text(110, 2.30*dy, 'Mixed\ntype', ha='center', va='center', fontsize=9, color='#406618', weight='bold', zorder=4)
    ax.text(110, 1.68*dy, 'Mixed\ntype', ha='center', va='center', fontsize=9, color='#8c2323', weight='bold', zorder=4)
    ax.text(110, 1.32*dy, 'Sodium\nbicarbonate\ntype', ha='center', va='center', fontsize=9, color='#004b73', weight='bold', zorder=4)
    ax.text(85, 2.0*dy, 'Magnesium\nbicarbonate\ntype', ha='center', va='center', fontsize=9, color='#521c61', weight='bold', zorder=4)
    ax.text(135, 2.0*dy, 'Sodium\nchloride\ntype', ha='center', va='center', fontsize=9, color='#82194d', weight='bold', zorder=4)

    ax.text(50 + sh_cx, -8 + sh_cy, 'Ca²⁺', ha='center', va='top', fontweight='bold', fontsize=12, zorder=4)
    ax.text(13 + sh_cx, (dy/2) + sh_cy, 'Mg²⁺', ha='right', va='center', fontweight='bold', fontsize=12, zorder=4)
    ax.text(offset_anion + 50 + sh_ax, -8 + sh_ay, 'Cl⁻', ha='center', va='top', fontweight='bold', fontsize=12, zorder=4)
    ax.text(offset_anion + 90 + sh_ax, (dy/2) + sh_ay, 'SO₄²⁻', ha='left', va='center', fontweight='bold', fontsize=12, zorder=4)
    
    ax.text(50 + sh_cx, -18 + sh_cy, 'CATION', ha='center', va='top', fontweight='bold', fontsize=14, color='black', zorder=4)
    ax.text(offset_anion + 50 + sh_ax, -18 + sh_ay, 'ANION', ha='center', va='top', fontweight='bold', fontsize=14, color='black', zorder=4)

    ax.text(90 - 14, 2.3*dy + 2, 'Sulfate (SO₄) + Chloride (Cl)', rotation=60, ha='center', va='bottom', fontsize=9, style='italic', zorder=4)
    ax.text(130 + 15, 2.2*dy + 2, 'Calcium (Ca) + Magnesium (Mg)', rotation=-60, ha='center', va='bottom', fontsize=9, style='italic', zorder=4)
    ax.text(95 - 14, 1.7*dy + 2, 'Sodium (Na) + Potassium (K)', rotation=-60, ha='center', va='top', fontsize=9, style='italic', zorder=4)
    ax.text(125 + 14, 1.8*dy + 2, 'Carbonate (CO₃) + Bicarbonate (HCO₃)', rotation=60, ha='center', va='top', fontsize=9, style='italic', zorder=4)

    # =========================================================
    # 5. PLOTTING TITIK SAMPEL DATA & EKSTRAKSI INTERPRETASI
    # =========================================================
    kolom_label = 'Sample_ID'
    for col in df.columns:
        if col.upper() in ['NO SAMPEL', 'SAMPEL', 'SAMPLE', 'SAMPLE_ID', 'ID', 'NO_SAMPEL']:
            kolom_label = col
            break

    data_interpretasi = []

    for idx, row in df.iterrows():
        ca_meq = row['Ca'] / 20.04
        mg_meq = row['Mg'] / 12.15
        na_meq = row['Na'] / 22.99
        k_meq = row['K'] / 39.10
        
        hco3_meq = row['HCO3'] / 61.02
        so4_meq = row['SO4'] / 48.03
        cl_meq = row['Cl'] / 35.45
        
        total_cat = ca_meq + mg_meq + na_meq + k_meq
        total_an = hco3_meq + so4_meq + cl_meq
        
        ca_pct = (ca_meq / total_cat) * 100
        mg_pct = (mg_meq / total_cat) * 100
        na_k_pct = ((na_meq + k_meq) / total_cat) * 100
        
        hco3_pct = (hco3_meq / total_an) * 100
        so4_pct = (so4_meq / total_an) * 100
        cl_pct = (cl_meq / total_an) * 100
        
        cx, cy, ax_pos, ay, dx, dy_pos = kalkulasi_koordinat_piper(
            ca_pct, mg_pct, na_k_pct, hco3_pct, so4_pct, cl_pct, shift_factor=shift_factor
        )
        
        label_sampel = row[kolom_label] if kolom_label in df.columns else f'S-{idx}'
        
        # Plotting Titik Sampel Air (SUDAH DIKECILKAN & BULAT BIRU)
        ax.scatter(cx, cy, c="#fffb00", edgecolors='k', s=50, zorder=5) 
        ax.scatter(ax_pos, ay, c='#1890ff', edgecolors='k', s=50, zorder=5) 
        ax.scatter(dx, dy_pos, c="#98ff92", edgecolors='k', s=50, marker='o', zorder=5) # Bulat Biru Kecil
        
        ax.text(dx + 3, dy_pos + 1, str(label_sampel), fontsize=8, c='black', weight='bold', zorder=6)
        
        # Panggil logika klasifikasi hidrokimia
        tipe_kat, tipe_an, tipe_fasies = interpretasi_hydrochemical(
            ca_pct, mg_pct, na_k_pct, hco3_pct, so4_pct, cl_pct
        )
        
        data_interpretasi.append({
            'No Sampel': label_sampel,
            'Cation Type': tipe_kat,
            'Anion Type': tipe_an,
            'Water Facies (Diamond)': tipe_fasies
        })
        
    ax.axis('off')
    df_hasil_interpretasi = pd.DataFrame(data_interpretasi)
    return fig, df_hasil_interpretasi

# --- LAYOUT UTAMA STREAMLIT ---
st.set_page_config(page_title="Piper Diagram Generator v6", layout="wide")
st.title("📊 Plot Diagram Piper & Interpretasi Hidrokimia")

# --- CODING NOTE / PANDUAN PENGGUNA (HALAMAN UTAMA) ---
st.info("""
ℹ️ **PERSYARATAN SATUAN DATA DATA INPUT:**
Sistem ini menggunakan algoritma konversi otomatis berat ekuivalen kimia air. 
Oleh karena itu, seluruh nilai konsentrasi ion pada file template Excel/CSV yang diunggah **WAJIB DALAM SATUAN mg/L** (Miligram per Liter).
""")

st.sidebar.header("Pengaturan Data")

# --- CODING NOTE (SIDEBAR) ---
st.sidebar.warning("⚠️ **PENTING:** Pastikan kolom Ca, Mg, Na, K, HCO3, SO4, Cl Anda diisi dengan angka berbasis satuan **mg/L**.")

uploaded_file = st.sidebar.file_uploader("Unggah file Excel atau CSV", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        df_raw = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df = bersihkan_dataframe(df_raw)
        
        st.success("Data Berhasil Dimuat!")
        st.subheader("📋 Preview Data Air Groundwater (Satuan Terdeteksi: mg/L)")
        st.dataframe(df.head(20))
        
        if st.sidebar.button("Generate Diagram Piper"):
            col1, col2 = st.columns([4, 4])
            
            # Panggil fungsi yang ada
            fig, df_interp = plot_piper(df)
            
            # Panggil fungsi Genesa & Litologi (Baru)
            df_genesa = hitung_genesa_litologi(df)
            
            with col1:
                st.subheader("📐 Hasil Plotting Diagram Piper")
                st.pyplot(fig)
                
            with col2:
                # Menampilkan Tabel Interpretasi Tipe Ion
                st.subheader("📝 Laporan Hasil Interpretasi Fasies")
                st.dataframe(df_interp, use_container_width=True)
                
                csv_data_interp = df_interp.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Unduh Tabel Interpretasi Fasies (CSV)",
                    data=csv_data_interp,
                    file_name='Hasil_Interpretasi_Fasies_Piper.csv',
                    mime='text/csv'
                )
                
                st.markdown("---")
                
                # Menampilkan Tabel Genesa dan Litologi (Baru)
                st.subheader("🌍 Interpretasi Genesa & Litologi")
                st.dataframe(df_genesa, use_container_width=True)
                
                csv_data_genesa = df_genesa.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Unduh Tabel Genesa & Litologi (CSV)",
                    data=csv_data_genesa,
                    file_name='Hasil_Interpretasi_Genesa_Litologi.csv',
                    mime='text/csv'
                )
            
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses data: {e}")
else:
    st.info("Silakan unggah file Excel Anda yang memiliki kolom ion utama (Ca, Mg, Na, K, HCO3, SO4, Cl).")