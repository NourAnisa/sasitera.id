import os
import sys
import json
import random
import re
import pandas as pd
import numpy as np
from PIL import Image
from flask import Flask, render_template, request, jsonify, send_from_directory
import torch
import torch.nn as nn
from torchvision import transforms, models

sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# -------------------------------------------------------------
# 1. LOAD MODEL & LABELS
# -------------------------------------------------------------
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
classes = ['GELOMBANG', 'HIRIS PUDAK', 'KEMBANG KACANG', 'TURUN DAYANG']

# Inisialisasi arsitektur MobileNetV2
model = models.mobilenet_v2(weights=None)
model.classifier[1] = nn.Sequential(
    nn.Linear(model.last_channel, 128),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(128, len(classes))
)

model_path = os.path.join('models', 'sasirangan_mobilenetv2.pth')
if os.path.exists(model_path):
    checkpoint = torch.load(model_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    classes = checkpoint.get('classes', classes)
    print(f"[*] Model CNN berhasil dimuat dari {model_path}")
else:
    print(f"[!] Warning: Model file {model_path} tidak ditemukan, menggunakan arsitektur default.")

model = model.to(device)
model.eval()

# Transformasi inferensi
inference_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# -------------------------------------------------------------
# 2. METADATA & FILOSOFI MOTIF SASIRANGAN
# -------------------------------------------------------------
MOTIF_INFO = {
    "GELOMBANG": {
        "nama": "Motif Gelombang (Ombak Seribu Sungai)",
        "filosofi": "Menggambarkan riak dan dinamika gelombang sungai Martapura yang senantiasa mengalir. Melambangkan perjuangan hidup yang gigih, ketabahan menghadapi pasang-surut dinamika zaman, dan fleksibilitas beradaptasi.",
        "makna_simbolik": "Ketabahan, Adaptabilitas, dan Dinamika Kehidupan",
        "penggunaan_tradisional": "Kain seragam adat, busana pria/wanita untuk upacara dan perayaan kegembiraan.",
        "warna_khas": ["Kuning Kunyit", "Biru Indigo", "Hijau Daun", "Merah Terang"],
        "teknik_jelujur": "Jahitan jelujur bergelombang zig-zag dinamis (tali banyum)"
    },
    "HIRIS PUDAK": {
        "nama": "Motif Hiris Pudak (Irisan Daun Pandan)",
        "filosofi": "Terinspirasi dari irisan daun pandan wangi (pudak). Melambangkan keharuman budi pekerti, kepribadian yang luhur, tutur kata yang sopan, serta membawa ketenteraman dan kebahagiaan bagi lingkungan sekitar.",
        "makna_simbolik": "Keharuman Budi Pekerti, Kesopanan, dan Kedamaian Jiwa",
        "penggunaan_tradisional": "Pakaian adat pengantin Banjar, selendang perempuan, dan acara resmi keagamaan/kebudayaan.",
        "warna_khas": ["Hijau Pupus", "Kuning Raja", "Cokelat Terakota"],
        "teknik_jelujur": "Jelujur geometris menyerupai irisan belah ketupat segitiga lancip berulang"
    },
    "KEMBANG KACANG": {
        "nama": "Motif Kembang Kacang (Bunga Kacang Panjang)",
        "filosofi": "Terinspirasi dari tanaman kacang yang merambat dan bunganya yang mekar. Melambangkan kesuburan tanah Banjar, keakraban sosial, tali silaturahmi yang kokoh, dan gotong royong antar warga.",
        "makna_simbolik": "Kesuburan, Silaturahmi Erat, dan Keharmonisan Sosial",
        "penggunaan_tradisional": "Kain sarung harian, busana kerja, dan cendera mata tamu kehormatan.",
        "warna_khas": ["Merah Muda", "Ungu Terong", "Kuning Muda", "Toska"],
        "teknik_jelujur": "Jelujur melengkung melingkar menyerupai kelopak bunga dan sulur daun"
    },
    "TURUN DAYANG": {
        "nama": "Motif Turun Dayang (Putri Kahyangan)",
        "filosofi": "Mengangkat legenda putri dayang yang turun ke bumi. Melambangkan keanggunan, martabat kemuliaan, kesucian, dan kecantikan perempuan Banjar yang bersahaja serta penuh pesona wibawa.",
        "makna_simbolik": "Keanggunan, Martabat Tinggi, dan Kemuliaan",
        "penggunaan_tradisional": "Kain kemben bangsawan Banjar, selendang pengantin, dan busana upacara sakral Batimbang/Bapalas.",
        "warna_khas": ["Ungu Kerajaan", "Merah Marun", "Kuning Emas", "Hitam Elegan"],
        "teknik_jelujur": "Jelujur berderet vertikal menjuntai ke bawah dengan hiasan titik kancing"
    }
}

# -------------------------------------------------------------
# 3. LOAD DATASET SATU DATA BANJARMASIN & GEO-MAPPING
# -------------------------------------------------------------
KELURAHAN_GEO = {
    # Banjarmasin Tengah
    "Seberang Mesjid": [-3.3142, 114.5985],
    "Pasar Lama": [-3.3175, 114.5920],
    "Mawar": [-3.3220, 114.5940],
    "Teluk Dalam": [-3.3180, 114.5800],
    "Kertak Baru Ilir": [-3.3245, 114.5910],
    "Kertak Baru Ulu": [-3.3210, 114.5880],
    "Antasan Besar": [-3.3160, 114.5890],
    "Gadang": [-3.3260, 114.5990],
    "Melayu": [-3.3240, 114.6030],
    "Pekapuran Laut": [-3.3290, 114.6010],
    "Sungai Baru": [-3.3250, 114.5960],
    "Kelayan Luar": [-3.3310, 114.5950],
    
    # Banjarmasin Utara
    "Sungai Jingah": [-3.3051, 114.6052],
    "Sungai Andai": [-3.2920, 114.6110],
    "Alalak Utara": [-3.2840, 114.5820],
    "Alalak Tengah": [-3.2910, 114.5790],
    "Alalak Selatan": [-3.2980, 114.5780],
    "Kuin Utara": [-3.2990, 114.5730],
    "Antasan Kecil Timur": [-3.3080, 114.5940],
    "Surgi Mufti": [-3.3090, 114.6010],
    "Sungai Miai": [-3.3020, 114.5920],
    "Pangeran": [-3.3060, 114.5850],
    
    # Banjarmasin Timur
    "Sungai Lulut": [-3.3310, 114.6350],
    "Banua Anyar": [-3.3120, 114.6210],
    "Karang Mekar": [-3.3320, 114.6120],
    "Kuripan": [-3.3280, 114.6080],
    "Kebun Bunga": [-3.3350, 114.6180],
    "Pekapuran Raya": [-3.3380, 114.6150],
    "Pemurus Luar": [-3.3420, 114.6250],
    "Pengambangan": [-3.3190, 114.6150],
    "Benua Anyar": [-3.3120, 114.6210],
    
    # Banjarmasin Barat
    "Pelambuan": [-3.3275, 114.5750],
    "Belitung Utara": [-3.3110, 114.5740],
    "Belitung Selatan": [-3.3160, 114.5760],
    "Kuin Selatan": [-3.3080, 114.5710],
    "Teluk Tiram": [-3.3320, 114.5680],
    "Telaga Biru": [-3.3210, 114.5710],
    "Kuin Cerucuk": [-3.3140, 114.5680],
    "Basirih": [-3.3480, 114.5650],
    
    # Banjarmasin Selatan
    "Kelayan Barat": [-3.3380, 114.5890],
    "Kelayan Dalam": [-3.3410, 114.5940],
    "Kelayan Tengah": [-3.3440, 114.5960],
    "Kelayan Timur": [-3.3460, 114.6010],
    "Kelayan Selatan": [-3.3510, 114.5980],
    "Murung Raya": [-3.3420, 114.6010],
    "Pekauman": [-3.3360, 114.5830],
    "Pemurus Baru": [-3.3450, 114.6090],
    "Pemurus Dalam": [-3.3480, 114.6120],
    "Tanjung Pagar": [-3.3550, 114.6050],
    "Basirih Selatan": [-3.3620, 114.5780],
    "Mantuil": [-3.3710, 114.5840]
}

def load_industry_dataset():
    csv_file = "data_industri_sasirangan_ekraf_lengkap.csv"
    if not os.path.exists(csv_file):
        csv_file = "data_industri_sasirangan.csv"
    
    df = pd.read_csv(csv_file)
    industries = []
    
    for idx, row in df.iterrows():
        kec = str(row.get('Kecamatan', '')).strip()
        kel = str(row.get('Kelurahan', '')).strip()
        
        # Cari koordinat base
        coords = KELURAHAN_GEO.get(kel, [-3.3194, 114.5908])
        # Tambahkan sedikit jitter agar titik pada kelurahan yang sama menyebar cantik di peta
        random.seed(idx + 100)
        lat = coords[0] + (random.random() - 0.5) * 0.0035
        lng = coords[1] + (random.random() - 0.5) * 0.0035
        
        industries.append({
            "id": int(row.get('No', idx + 1)),
            "nama": str(row.get('Nama Industri', '')),
            "pemilik": str(row.get('Nama Pemilik', '')),
            "penanggung_jawab": str(row.get('Nama Penanggung Jawab', '')),
            "kecamatan": kec,
            "kelurahan": kel,
            "alamat": str(row.get('Alamat', '')),
            "kbli_kode": str(row.get('Kode KBLI', '')),
            "kbli_nama": str(row.get('Deskripsi KBLI', '')),
            "kategori": str(row.get('Kategori', 'Sasirangan & Batik')),
            "lat": round(lat, 6),
            "lng": round(lng, 6)
        })
        
    return industries

INDUSTRIES_DATA = load_industry_dataset()
print(f"[*] Berhasil memuat {len(INDUSTRIES_DATA)} data industri geospasial.")

# -------------------------------------------------------------
# 4. FLASK ROUTES
# -------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    df = pd.DataFrame(INDUSTRIES_DATA)
    
    # Sebaran per Kecamatan
    kec_counts = df['kecamatan'].value_counts().to_dict()
    
    # Sebaran per Kelurahan Top 10
    kel_counts = df['kelurahan'].value_counts().head(10).to_dict()
    
    # Sebaran per Kategori KBLI Top 6
    kbli_counts = df['kbli_nama'].value_counts().head(6).to_dict()
    
    # Total
    total_industries = len(df)
    total_sasirangan = len(df[df['kategori'] == 'Sasirangan & Batik'])
    total_pendukung = total_industries - total_sasirangan
    
    return jsonify({
        "total_industries": total_industries,
        "total_sasirangan": total_sasirangan,
        "total_pendukung": total_pendukung,
        "kecamatan_distribution": kec_counts,
        "kelurahan_top10": kel_counts,
        "kbli_distribution": kbli_counts,
        "macro_umkm": {
            "Banjarmasin Tengah": 5646,
            "Banjarmasin Barat": 5608,
            "Banjarmasin Selatan": 5584,
            "Banjarmasin Timur": 5344,
            "Banjarmasin Utara": 4642
        }
    })

@app.route('/api/industries')
def get_industries():
    kec = request.args.get('kecamatan', '')
    kategori = request.args.get('kategori', '')
    query = request.args.get('q', '').lower()
    
    filtered = INDUSTRIES_DATA
    if kec and kec != 'all':
        filtered = [item for item in filtered if item['kecamatan'] == kec]
    if kategori and kategori != 'all':
        filtered = [item for item in filtered if item['kategori'] == kategori]
    if query:
        filtered = [item for item in filtered if (
            query in item['nama'].lower() or 
            query in item['pemilik'].lower() or 
            query in item['kelurahan'].lower() or
            query in item['alamat'].lower()
        )]
        
    return jsonify({
        "total": len(filtered),
        "data": filtered
    })

@app.route('/api/samples')
def get_samples():
    sample_dir = os.path.join('static', 'samples')
    samples = []
    if os.path.exists(sample_dir):
        for f in os.listdir(sample_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                label = "GELOMBANG" if "gelombang" in f.lower() else \
                        "HIRIS PUDAK" if "hiris" in f.lower() else \
                        "KEMBANG KACANG" if "kembang" in f.lower() else "TURUN DAYANG"
                samples.append({
                    "filename": f,
                    "url": f"/static/samples/{f}",
                    "label": label
                })
    return jsonify(samples)

@app.route('/api/classify', methods=['POST'])
def classify_motif():
    try:
        image_path = None
        
        # Opsi 1: File Upload
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            filename = f"upload_{random.randint(1000, 9999)}_{file.filename}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(image_path)
            image_url = f"/static/uploads/{filename}"
            
        # Opsi 2: Sample Path
        elif request.is_json and 'sample_url' in request.json:
            sample_url = request.json['sample_url']
            rel_path = sample_url.lstrip('/')
            image_path = rel_path
            image_url = sample_url
            
        if not image_path or not os.path.exists(image_path):
            return jsonify({"error": "Gambar tidak ditemukan atau gagal diunggah."}), 400
            
        # Buka dan Proses Citra
        img = Image.open(image_path).convert('RGB')
        input_tensor = inference_transform(img).unsqueeze(0).to(device)
        
        with torch.no_grad():
            outputs = model(input_tensor)
            probabilities = torch.softmax(outputs, dim=1)[0].cpu().numpy()
            predicted_idx = int(np.argmax(probabilities))
            
        pred_class = classes[predicted_idx]
        confidence = float(probabilities[predicted_idx])
        
        # Probabilitas Semua Kelas
        all_probs = {
            classes[i]: round(float(probabilities[i]) * 100, 2)
            for i in range(len(classes))
        }
        
        motif_details = MOTIF_INFO.get(pred_class, {})
        
        return jsonify({
            "success": True,
            "predicted_motif": pred_class,
            "confidence": round(confidence * 100, 2),
            "probabilities": all_probs,
            "details": motif_details,
            "image_url": image_url
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("[*] Aplikasi Web SASIRANGAN-AI Siap Dijalankan!")
    print("[*] Buka browser di http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
