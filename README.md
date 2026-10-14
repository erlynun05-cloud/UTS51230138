# Sistem Market Basket Analysis (Algoritma Apriori) — Universitas Timor

Finsensia Erlinda Un · NPM 51230138 · Teknologi Informasi

Situs ini **statis**, sehingga bisa dihosting gratis di **GitHub Pages**. Analisis (cleaning, Apriori, layout etalase) tetap dijalankan dengan Python yang sama, tetapi di dalam browser pengunjung (memakai Pyodide). Tidak ada server yang perlu dijalankan.

## Isi folder
| File | Fungsi |
|---|---|
| `index.html` | Halaman utama (cover, login, seluruh tampilan) |
| `analisis.py` | Kode analisis Python yang dijalankan di browser |
| `data-contoh.json`, `hasil-contoh.xlsx` | Hasil contoh agar situs langsung bisa dicoba |
| `.nojekyll` | Opsional (boleh dilewati bila sulit diunggah) |

## Cara hosting di GitHub (gratis)
1. Buat akun di https://github.com (jika belum punya).
2. Klik **+** (kanan atas) → **New repository**. Isi nama, misalnya `market-basket-unimor`, pilih **Public**, lalu **Create repository**.
3. Klik **uploading an existing file**, lalu seret **semua file di dalam folder ini** (bukan foldernya) ke halaman tersebut. Klik **Commit changes**.
4. Buka **Settings → Pages**. Pada *Build and deployment*, pilih **Source: Deploy from a branch**, **Branch: main** dan folder **/ (root)**, lalu **Save**.
5. Tunggu 1–2 menit. Alamat situs muncul di halaman yang sama:
   `https://NAMA-GITHUB-ANDA.github.io/market-basket-unimor/`

## Cara pakai situs
- Login: `finsensia` / `UT51230138`
- Klik **Lihat hasil data contoh** untuk hasil langsung, atau unggah file Excel transaksi sendiri.
- Saat mengunggah pertama kali, browser memuat mesin Python (sekitar 20 MB, 30–60 detik) dan perlu internet. Sesudahnya lebih cepat karena tersimpan di cache.
- File yang diunggah diproses di browser dan tidak dikirim ke server mana pun.

## Mencoba di komputer sebelum diunggah
Jangan klik dua kali `index.html`, karena browser memblokir pembacaan file lain. Jalankan di folder ini:
```
python -m http.server 8000
```
lalu buka http://localhost:8000

## Catatan penting
- **Login hanya penghalang tampilan.** Di situs statis, nama pengguna dan kata sandi diperiksa di browser, dan data contoh bisa dilihat oleh siapa pun yang membuka kode sumber. Jangan pakai kata sandi yang sama dengan akun penting, dan jangan taruh data rahasia di repositori.
- GitHub Pages gratis untuk repositori **Public**.
- Batas file GitHub 100 MB per file; file di sini jauh di bawahnya.
