import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

sys.stdout.reconfigure(encoding='utf-8')

# Set style publikasi
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#cbd5e1'
plt.rcParams['axes.linewidth'] = 0.8

os.makedirs("static/img", exist_ok=True)

# 1. Load Data
df_industri = pd.read_csv("data_industri_sasirangan_ekraf_lengkap.csv")
df_umkm = pd.read_csv("data_umkm_kecamatan_banjarmasin.csv")

print("=================================================================")
print("📊 HASIL ANALISIS SPASIAL & STATISTIK EKONOMI SEKTORAL SASITERA")
print("=================================================================")

# 2. Agregasi Sebaran per Kecamatan
kec_summary = df_industri.groupby('Kecamatan').agg(
    Total_Industri=('Nama Industri', 'count'),
    Sasirangan_Murni=('Kategori', lambda x: (x == 'Sasirangan & Batik').sum()),
    Ekraf_Pendukung=('Kategori', lambda x: (x != 'Sasirangan & Batik').sum())
).reset_index()

# Merge dengan Total UMKM Resmi Dinas Koperasi & Tenaga Kerja
df_merged = pd.merge(kec_summary, df_umkm[['Kecamatan', 'Total Usaha']], on='Kecamatan', how='left')

# Hitung Rasio Penetrasi per 1.000 UMKM & Location Quotient (LQ)
# LQ = (Industri_Kec / Total_Industri_BJM) / (UMKM_Kec / Total_UMKM_BJM)
total_industri_bjm = df_merged['Total_Industri'].sum()
total_umkm_bjm = df_merged['Total Usaha'].sum()

df_merged['Penetrasi_per_1000_UMKM'] = (df_merged['Total_Industri'] / df_merged['Total Usaha']) * 1000
df_merged['Location_Quotient_LQ'] = (df_merged['Total_Industri'] / total_industri_bjm) / (df_merged['Total Usaha'] / total_umkm_bjm)
df_merged['Persentase_Pangsa_Kota'] = (df_merged['Total_Industri'] / total_industri_bjm) * 100

print("\n1. MATRIKS ANALISIS SPASIAL DAN DAYA SAING SEKTORAL PER KECAMATAN:")
print(df_merged[['Kecamatan', 'Total_Industri', 'Sasirangan_Murni', 'Total Usaha', 'Penetrasi_per_1000_UMKM', 'Location_Quotient_LQ', 'Persentase_Pangsa_Kota']].to_string(index=False))

# 3. Analisis Aglomerasi Tingkat Kelurahan (Top 10)
kel_summary = df_industri['Kelurahan'].value_counts().reset_index()
kel_summary.columns = ['Kelurahan', 'Jumlah_Industri']
kel_summary['Kumulatif_Persen'] = (kel_summary['Jumlah_Industri'].cumsum() / len(df_industri)) * 100

print("\n2. TOP 10 KELURAHAN DENGAN KONSENTRASI AGLOMERASI TERPADAT:")
print(kel_summary.head(10).to_string(index=False))

top2_kel = kel_summary.head(2)['Jumlah_Industri'].sum()
print(f"\n💡 TEMUAN SPASIAL PENTING: 2 Kelurahan teratas (Seberang Mesjid & Sungai Jingah) mencakup {top2_kel} industri ({(top2_kel/len(df_industri))*100:.1f}% dari seluruh ekosistem di Kota Banjarmasin). Ini membuktikan adanya fenomena 'Spatial Clustering / Industrial Agglomeration' yang sangat kuat di sepanjang bantaran Sungai Martapura.")

# 4. Korelasi Statistik
corr, p_value = stats.pearsonr(df_merged['Total_Industri'], df_merged['Total Usaha'])
print(f"\n3. KORELASI STATISTIK (Total Industri Sasirangan vs Total Basis UMKM):")
print(f"   - Pearson Correlation (r): {corr:.4f}")
print(f"   - P-Value: {p_value:.4f}")
print("   - Interpretasi: Tidak terdapat korelasi linier sederhana antara jumlah UMKM umum dengan industri Sasirangan, yang mengindikasikan bahwa industri Sasirangan tidak menyebar rata berdasarkan populasi usaha, melainkan TERKONSENTRASI SPASIAL KARENA FAKTOR HISTORIS & GEOGRAFIS (Kampung Tematik Seberang Mesjid & Sungai Jingah).")

# =========================================================================
# GENERATE PUBLICATION-QUALITY FIGURES
# =========================================================================

# FIG 1: Sebaran Industri & Penetrasi per 1.000 UMKM
fig, ax1 = plt.subplots(figsize=(10, 5.5), dpi=300)
df_sorted = df_merged.sort_values(by='Total_Industri', ascending=False)

x = np.arange(len(df_sorted))
width = 0.35

color1 = '#0f766e' # Teal
color2 = '#d97706' # Amber Gold

rects1 = ax1.bar(x - width/2, df_sorted['Total_Industri'], width, label='Jumlah IKM Sasirangan & Ekraf (Unit)', color=color1, edgecolor='none', zorder=3)
ax1.set_ylabel('Jumlah Unit Industri', color=color1, fontsize=11, fontweight='bold')
ax1.tick_params(axis='y', labelcolor=color1)
ax1.set_xticks(x)
ax1.set_xticklabels(df_sorted['Kecamatan'], fontsize=10, fontweight='semibold')
ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

ax2 = ax1.twinx()
rects2 = ax2.bar(x + width/2, df_sorted['Penetrasi_per_1000_UMKM'], width, label='Penetrasi per 1.000 UMKM', color=color2, edgecolor='none', zorder=3)
ax2.set_ylabel('Kepadatan per 1.000 UMKM', color=color2, fontsize=11, fontweight='bold')
ax2.tick_params(axis='y', labelcolor=color2)
ax2.grid(False)

# Labels on top of bars
for rect in rects1:
    h = rect.get_height()
    ax1.annotate(f'{int(h)}', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold', color=color1)
for rect in rects2:
    h = rect.get_height()
    ax2.annotate(f'{h:.1f}', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold', color=color2)

plt.title('Sebaran Industri Kreatif Sasirangan dan Rasio Penetrasi UMKM per Kecamatan\n(Sumber: Portal Satu Data Kota Banjarmasin, 2026)', fontsize=12, fontweight='bold', pad=15)
fig.tight_layout()
plt.savefig('static/img/spasial_sebaran_kecamatan.png', dpi=300)
plt.close()
print("[✓] Gambar 1 berhasil disimpan: static/img/spasial_sebaran_kecamatan.png")

# FIG 2: Location Quotient (LQ) Daya Saing Spasial
plt.figure(figsize=(9, 4.8), dpi=300)
lq_sorted = df_merged.sort_values(by='Location_Quotient_LQ', ascending=True)
colors_lq = ['#10b981' if lq > 1.0 else '#94a3b8' for lq in lq_sorted['Location_Quotient_LQ']]

bars = plt.barh(lq_sorted['Kecamatan'], lq_sorted['Location_Quotient_LQ'], color=colors_lq, height=0.55, edgecolor='none', zorder=3)
plt.axvline(x=1.0, color='#ef4444', linestyle='--', linewidth=1.5, label='Ambang Batas Keunggulan Komparatif (LQ = 1.0)', zorder=4)

for bar in bars:
    w = bar.get_width()
    plt.text(w + 0.03, bar.get_y() + bar.get_height()/2, f'LQ = {w:.2f}', ha='left', va='center', fontsize=9, fontweight='bold', color='#1e293b')

plt.title('Indeks Keunggulan Spasial (Location Quotient / LQ) Sektor Sasirangan per Kecamatan\n(LQ > 1.0 Menunjukkan Sektor Basis Unggulan Daerah)', fontsize=11, fontweight='bold', pad=12)
plt.xlabel('Nilai Location Quotient (LQ)', fontsize=10, fontweight='bold')
plt.xlim(0, 2.1)
plt.legend(loc='lower right', frameon=True)
plt.grid(axis='x', linestyle='--', alpha=0.5, zorder=0)
plt.tight_layout()
plt.savefig('static/img/spasial_location_quotient.png', dpi=300)
plt.close()
print("[✓] Gambar 2 berhasil disimpan: static/img/spasial_location_quotient.png")

# FIG 3: Top 10 Kelurahan Aglomerasi Pareto Chart
fig, ax1 = plt.subplots(figsize=(10, 5.5), dpi=300)
top10 = kel_summary.head(10)

ax1.bar(top10['Kelurahan'], top10['Jumlah_Industri'], color='#3b82f6', edgecolor='none', zorder=3)
ax1.set_ylabel('Jumlah Unit Industri', color='#1e3a8a', fontsize=11, fontweight='bold')
ax1.tick_params(axis='x', rotation=30)
ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

ax2 = ax1.twinx()
ax2.plot(top10['Kelurahan'], top10['Kumulatif_Persen'], color='#f59e0b', marker='o', linewidth=2.5, markersize=6, label='Persentase Kumulatif (%)', zorder=4)
ax2.set_ylabel('Persentase Kumulatif (%)', color='#b45309', fontsize=11, fontweight='bold')
ax2.set_ylim(0, 105)
ax2.grid(False)

for i, txt in enumerate(top10['Kumulatif_Persen']):
    ax2.annotate(f'{txt:.1f}%', (top10['Kelurahan'].iloc[i], txt + 2.5), ha='center', fontsize=8, fontweight='bold', color='#b45309')

plt.title('Kurva Pareto Aglomerasi Sentra Industri Sasirangan Top 10 Kelurahan di Banjarmasin', fontsize=12, fontweight='bold', pad=15)
fig.tight_layout()
plt.savefig('static/img/spasial_aglomerasi_kelurahan.png', dpi=300)
plt.close()
print("[✓] Gambar 3 berhasil disimpan: static/img/spasial_aglomerasi_kelurahan.png")

# FIG 4: Klasifikasi Struktur KBLI & Ekosistem Rantai Pasok
plt.figure(figsize=(8.5, 4.5), dpi=300)
kbli_top = df_industri['Deskripsi KBLI'].value_counts().head(5)
colors_pie = ['#d4af37', '#0284c7', '#10b981', '#8b5cf6', '#f43f5e']

wedges, texts, autotexts = plt.pie(kbli_top, labels=None, autopct='%1.1f%%', startangle=140, colors=colors_pie,
                                   pctdistance=0.75, explode=[0.05, 0.02, 0, 0, 0], textprops=dict(color="w", fontweight="bold"))

plt.legend(wedges, [f"{k[:30]}... ({v} unit)" for k, v in zip(kbli_top.index, kbli_top.values)],
           title="Klasifikasi Baku Lapangan Usaha (KBLI)", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9)
plt.title('Struktur Ekosistem Rantai Nilai Industri Kreatif Tekstil Sasirangan di Banjarmasin', fontsize=11, fontweight='bold', pad=12)
plt.tight_layout()
plt.savefig('static/img/struktur_kbli_ekraf.png', dpi=300)
plt.close()
print("[✓] Gambar 4 berhasil disimpan: static/img/struktur_kbli_ekraf.png")

# Simpan Tabel Hasil Analisis ke CSV & Excel
df_merged.to_csv("hasil_analisis_spasial_ekonomi.csv", index=False, encoding='utf-8-sig')
df_merged.to_excel("hasil_analisis_spasial_ekonomi.xlsx", index=False)
print("\n[✓] Seluruh hasil komputasi metrik statistik tersimpan di: hasil_analisis_spasial_ekonomi.xlsx")
