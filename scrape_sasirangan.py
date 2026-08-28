import os
import sys
import re
import ssl
import time
import urllib.parse
import urllib.request
import pandas as pd
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

def scrape_sasirangan_data():
    base_url = "https://satudata.banjarmasinkota.go.id/dataIndustri/search_"
    search_keyword = "sasirangan"
    
    # Konfigurasi SSL dan Headers
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    all_records = []
    page = 1
    
    print(f"[*] Memulai proses scraping data industri kata kunci '{search_keyword}'...")
    
    while True:
        url = f"{base_url}?k={urllib.parse.quote(search_keyword)}&page={page}"
        print(f"[>] Mengambil Halaman {page}: {url}")
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=25) as response:
                html = response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"[!] Gagal mengambil halaman {page}: {e}")
            break
            
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        
        if not table:
            print(f"[*] Tabel tidak ditemukan di halaman {page}. Selesai.")
            break
            
        rows = table.find_all('tr')
        if len(rows) <= 1:
            print(f"[*] Tidak ada baris data tambahan di halaman {page}. Selesai.")
            break
            
        page_records = 0
        for tr in rows[1:]:  # Lewati header tabel
            cols = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if len(cols) >= 8:
                no = cols[0]
                nama_industri = cols[1]
                nama_pemilik = cols[2]
                nama_penanggung_jawab = cols[3]
                kecamatan_raw = cols[4]
                kelurahan_raw = cols[5]
                alamat = cols[6]
                kbli_raw = cols[7]
                
                # Ekstrak Kode dan Nama Kecamatan
                kec_match = re.search(r'^(.*?)(?:\s*\((.*?)\))?$', kecamatan_raw)
                kecamatan = kec_match.group(1).strip() if kec_match else kecamatan_raw
                kode_kecamatan = kec_match.group(2).strip() if (kec_match and kec_match.group(2)) else ""
                
                # Ekstrak Kode dan Nama Kelurahan
                kel_match = re.search(r'^(.*?)(?:\s*\((.*?)\))?$', kelurahan_raw)
                kelurahan = kel_match.group(1).strip() if kel_match else kelurahan_raw
                kode_kelurahan = kel_match.group(2).strip() if (kel_match and kel_match.group(2)) else ""
                
                # Ekstrak Kode dan Deskripsi KBLI
                kbli_match = re.search(r'^(\d+)\s*-\s*(.*)$', kbli_raw)
                kode_kbli = kbli_match.group(1).strip() if kbli_match else ""
                deskripsi_kbli = kbli_match.group(2).strip() if kbli_match else kbli_raw
                
                all_records.append({
                    "No": len(all_records) + 1,
                    "Nama Industri": nama_industri,
                    "Nama Pemilik": nama_pemilik,
                    "Nama Penanggung Jawab": nama_penanggung_jawab,
                    "Kecamatan": kecamatan,
                    "Kode Kecamatan": kode_kecamatan,
                    "Kelurahan": kelurahan,
                    "Kode Kelurahan": kode_kelurahan,
                    "Alamat": alamat,
                    "Kode KBLI": kode_kbli,
                    "Deskripsi KBLI": deskripsi_kbli,
                    "KBLI Lengkap": kbli_raw,
                    "Sumber URL": url
                })
                page_records += 1
        
        print(f"    -> Berhasil mengambil {page_records} industri dari halaman {page}.")
        
        # Cek apakah ada halaman selanjutnya (link pagination)
        pagination_links = [a['href'] for a in soup.find_all('a', href=True) if f'page={page+1}' in a['href']]
        if not pagination_links:
            print(f"[*] Halaman {page} adalah halaman terakhir.")
            break
            
        page += 1
        time.sleep(0.5)  # Jeda ramah server
        
    print(f"\n[SUCCESS] Total industri Sasirangan terkumpul: {len(all_records)} data.")
    
    if all_records:
        df = pd.DataFrame(all_records)
        
        # Simpan ke CSV
        csv_file = "data_industri_sasirangan.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"[SUCCESS] Data berhasil disimpan ke CSV: {csv_file}")
        
        # Simpan ke Excel
        excel_file = "data_industri_sasirangan.xlsx"
        try:
            df.to_excel(excel_file, index=False)
            print(f"[SUCCESS] Data berhasil disimpan ke Excel: {excel_file}")
        except Exception as e:
            print(f"[WARNING] Gagal menyimpan Excel: {e}")
            
        print("\n=== RINGKASAN SEBARAN INDUSTRI SASIRANGAN PER KECAMATAN ===")
        print(df['Kecamatan'].value_counts())
        print("\n=== TOP 5 KELURAHAN DENGAN SENTRA SASIRANGAN TERBANYAK ===")
        print(df['Kelurahan'].value_counts().head(5))

if __name__ == "__main__":
    scrape_sasirangan_data()
