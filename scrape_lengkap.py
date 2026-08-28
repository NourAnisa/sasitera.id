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

def scrape_multi_keyword():
    base_url = "https://satudata.banjarmasinkota.go.id/dataIndustri/search_"
    
    # Kata kunci terkait industri tekstil, sasirangan, bordir, kerajinan, fashion di Banjarmasin
    search_keywords = [
        "sasirangan",
        "13134",  # Industri Batik & Sasirangan
        "13132",  # Industri Penyempurnaan Kain
        "13133",  # Industri Pencetakan Kain
        "14111",  # Industri Pakaian Jadi Konveksi Tekstil
        "14120",  # Penjahitan & Pembuatan Pakaian
        "74113",  # Aktivitas Desain Tekstil, Fashion dan Apparel
        "kain",
        "tekstil",
        "kerajinan",
        "bordir"
    ]
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    all_records = []
    seen_identifiers = set()
    
    print("[*] MEMULAI SCRAPING MENYELURUH INDUSTRI SASIRANGAN & EKONOMI KREATIF TEKSTIL BANJARMASIN...")
    
    for kw in search_keywords:
        print(f"\n=======================================================")
        print(f"[*] Mencari Kata Kunci: '{kw}'")
        print(f"=======================================================")
        page = 1
        
        while True:
            url = f"{base_url}?k={urllib.parse.quote(kw)}&page={page}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, context=ctx, timeout=20) as response:
                    html = response.read().decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"[!] Gagal halaman {page} (kw: {kw}): {e}")
                break
                
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table')
            if not table:
                break
                
            rows = table.find_all('tr')
            if len(rows) <= 1:
                break
                
            new_in_page = 0
            for tr in rows[1:]:
                cols = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if len(cols) >= 8:
                    nama_industri = cols[1]
                    nama_pemilik = cols[2]
                    nama_penanggung_jawab = cols[3]
                    kecamatan_raw = cols[4]
                    kelurahan_raw = cols[5]
                    alamat = cols[6]
                    kbli_raw = cols[7]
                    
                    # Buat unique ID untuk deduplikasi data
                    uid = f"{nama_industri.lower()}_{nama_pemilik.lower()}_{alamat.lower()}"
                    
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
                    
                    # Klasifikasi kategori spesifik
                    is_sasirangan = "sasirangan" in nama_industri.lower() or "13134" in kbli_raw or "13132" in kbli_raw or "sasirangan" in alamat.lower()
                    
                    if uid not in seen_identifiers:
                        seen_identifiers.add(uid)
                        all_records.append({
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
                            "Kategori": "Sasirangan & Batik" if is_sasirangan else "Tekstil / Fashion / Kerajinan Lain",
                            "Keyword Asal": kw
                        })
                        new_in_page += 1
                        
            print(f"[>] Kw '{kw}' Hal {page}: +{new_in_page} data baru unik (Total Unik: {len(all_records)})")
            
            # Cek pagination
            pagination_links = [a['href'] for a in soup.find_all('a', href=True) if f'page={page+1}' in a['href']]
            if not pagination_links:
                break
                
            page += 1
            time.sleep(0.3)
            
    print(f"\n[SUCCESS] Total seluruh data unik industri tekstil & kreatif sasirangan: {len(all_records)}")
    
    if all_records:
        df = pd.DataFrame(all_records)
        df.insert(0, 'No', range(1, len(df) + 1))
        
        # Simpan CSV & Excel
        csv_file = "data_industri_sasirangan_ekraf_lengkap.csv"
        excel_file = "data_industri_sasirangan_ekraf_lengkap.xlsx"
        
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        try:
            df.to_excel(excel_file, index=False)
            print(f"[SUCCESS] Tersimpan ke Excel: {excel_file}")
        except Exception as e:
            print(f"[WARNING] Gagal simpan Excel: {e}")
            
        print(f"[SUCCESS] Tersimpan ke CSV: {csv_file}")
        
        print("\n=== RINGKASAN DATA BERDASARKAN KATEGORI ===")
        print(df['Kategori'].value_counts())
        
        print("\n=== SEBARAN INDUSTRI SASIRANGAN & EKRAF PER KECAMATAN ===")
        print(df.groupby(['Kecamatan', 'Kategori']).size().unstack(fill_value=0))
        
        print("\n=== SEBARAN BERDASARKAN KODE KBLI ===")
        print(df['Deskripsi KBLI'].value_counts().head(10))

if __name__ == "__main__":
    scrape_multi_keyword()
