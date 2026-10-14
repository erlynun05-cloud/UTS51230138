import sys, os, io, json, base64, collections, math
from itertools import combinations
import pandas as pd

USERNAME, PASSWORD = "finsensia", "UT51230138"
PORT = 8765
MIN_SUPPORT = 0.01          # ambang minimum Apriori
AMBANG_DEKAT = 0.10         # support >= 10% -> "Didekatkan"
KOLOM_WAJIB = ["TransactionID", "CustomerID", "ProductID", "ProductName", "Category", "Qty", "UnitPrice",
               "TotalBeforeDiscount", "DiscountPct", "DiscountAmount", "NetSales"]
STATE = {"xlsx": None}


def rp(x): return "Rp " + f"{round(x):,}".replace(",", ".")
def pc(x, d=1): return f"{x * 100:.{d}f}%".replace(".", ",")
def nf(x): return f"{round(x):,}".replace(",", ".")
def f2(x): return f"{x:.2f}".replace(".", ",")


# ---------------------------------------------------------------- BACA FILE
def baca(isi, nama):
    if nama.lower().endswith(".csv"):
        kandidat = [("csv", pd.read_csv(io.BytesIO(isi)))]
    else:
        try:
            xl = pd.ExcelFile(io.BytesIO(isi))
        except Exception:
            raise ValueError("File tidak dapat dibaca sebagai Excel (.xlsx). Pastikan file tidak rusak dan formatnya benar.")
        urut = sorted(xl.sheet_names, key=lambda s: s != "DATA_TRANSAKSI")
        kandidat = [(s, xl.parse(s)) for s in urut]
    for s, d in kandidat:
        if all(k in d.columns for k in KOLOM_WAJIB):
            return d
    d = kandidat[0][1]
    hilang = [k for k in KOLOM_WAJIB if k not in d.columns]
    raise ValueError("Kolom wajib tidak ditemukan: " + ", ".join(hilang) +
                     ". Pastikan ada sheet DATA_TRANSAKSI dengan kolom standar.")


# ---------------------------------------------------------------- CLEANING (Soal 1-3)
def bersihkan(raw):
    n_raw = len(raw)
    dup_sebelum = int(raw.duplicated().sum())
    miss_c = int(raw["CustomerID"].isna().sum())
    miss_d = int(raw["DiscountPct"].isna().sum())
    df = raw.drop_duplicates().copy()
    dup_sesudah = int(df.duplicated().sum())
    df["CustomerID"] = df["CustomerID"].fillna("UNKNOWN")
    kosong = df["DiscountPct"].isna()
    dari_nominal = int((kosong & (df["DiscountAmount"] > 0)).sum())
    turunan = (df["DiscountAmount"] / df["TotalBeforeDiscount"]).round(2).fillna(0)
    df.loc[kosong, "DiscountPct"] = turunan[kosong]
    nol = int(kosong.sum()) - dari_nominal
    df = df.reset_index(drop=True)

    def cek(nama, rumus, hitung, tercatat, selisih):
        return {"nama": nama, "rumus": rumus, "dicek": len(df), "selisih": int(selisih),
                "hitung": float(hitung.sum()), "tercatat": float(tercatat.sum()),
                "status": "Valid" if selisih == 0 else "Perlu dicek"}
    h1 = df["Qty"] * df["UnitPrice"]
    h2 = df["TotalBeforeDiscount"] * df["DiscountPct"]
    h3 = df["TotalBeforeDiscount"] - df["DiscountAmount"]
    validasi = [
        cek("TotalBeforeDiscount", "Qty × UnitPrice", h1, df["TotalBeforeDiscount"], (h1 != df["TotalBeforeDiscount"]).sum()),
        cek("DiscountAmount", "TotalBeforeDiscount × DiscountPct", h2, df["DiscountAmount"], ((h2 - df["DiscountAmount"]).abs() > 0.5).sum()),
        cek("NetSales", "TotalBeforeDiscount − DiscountAmount", h3, df["NetSales"], ((h3 - df["NetSales"]).abs() > 0.5).sum())]
    info = {"baris_awal": n_raw, "baris_bersih": len(df), "trx": int(df["TransactionID"].nunique()),
            "dup_sebelum": dup_sebelum, "dup_sesudah": dup_sesudah, "miss_c": miss_c, "miss_d": miss_d,
            "dari_nominal": dari_nominal, "nol": nol, "validasi": validasi}
    return df, info


# ---------------------------------------------------------------- APRIORI
def apriori(baskets, min_sup, max_len=3):
    n = len(baskets); hasil = {}; cnt = {}
    for b in baskets:
        for i in b:
            k = frozenset([i]); cnt[k] = cnt.get(k, 0) + 1
    level = {k: v for k, v in cnt.items() if v / n >= min_sup}; hasil.update(level); k = 2
    while level and k <= max_len:
        items = sorted({i for s in level for i in s})
        kand = [frozenset(c) for c in combinations(items, k)
                if all(frozenset(x) in level for x in combinations(c, k - 1))]
        cnt = dict.fromkeys(kand, 0)
        for b in baskets:
            for c in kand:
                if c <= b: cnt[c] += 1
        level = {c: v for c, v in cnt.items() if v / n >= min_sup}; hasil.update(level); k += 1
    return hasil


# ---------------------------------------------------------------- ANALISIS (Soal 4-11)
def analisis(raw):
    df, info = bersihkan(raw)
    n = info["trx"]
    g = df.groupby("ProductName").agg(cat=("Category", "first"), qty=("Qty", "sum"), gross=("TotalBeforeDiscount", "sum"),
                                      disc=("DiscountAmount", "sum"), net=("NetSales", "sum"),
                                      tx=("TransactionID", "nunique")).reset_index()
    price = df.groupby("ProductName")["UnitPrice"].mean().to_dict()
    cat_of = dict(zip(g.ProductName, g.cat)); net_of = dict(zip(g.ProductName, g.net))
    baskets = [frozenset(x) for x in df.groupby("TransactionID")["ProductName"].apply(set)]
    its = apriori(baskets, MIN_SUPPORT)
    sup = {s: v / n for s, v in its.items()}
    tx = {next(iter(s)): v for s, v in its.items() if len(s) == 1}

    raw_pairs, tot = [], collections.Counter()
    for s, v in its.items():
        if len(s) == 2:
            a, b = sorted(s)
            raw_pairs.append((a, b, v)); tot[a] += v; tot[b] += v
    raw_pairs.sort(key=lambda x: -x[2])
    pairs = []
    for i, (a, b, v) in enumerate(raw_pairs, 1):
        sp = v / n
        lift = sp / ((tx[a] / n) * (tx[b] / n))
        ket = "Didekatkan" if sp >= AMBANG_DEKAT else ("Prioritas evaluasi" if i <= 10 else "Evaluasi")
        pairs.append([i, a, b, v, round(sp, 4), tx[a], tx[b], round(v / tx[a], 3), round(v / tx[b], 3), round(lift, 2), ket])

    rules = []
    for s, sp in sup.items():
        if len(s) < 2: continue
        for r in range(1, len(s)):
            for a in combinations(sorted(s), r):
                a = frozenset(a); c = s - a; conf = sp / sup[a]
                if conf >= 0.1:
                    rules.append([", ".join(sorted(a)), ", ".join(sorted(c)), its[s], round(sp, 4), round(conf, 3), round(conf / sup[c], 2)])
    rules.sort(key=lambda x: (-x[5], -x[3]))

    prods = g.to_dict("records")
    byqty = sorted(prods, key=lambda r: -r["qty"]); bynet = sorted(prods, key=lambda r: -r["net"])
    row = lambda i, r: [i, r["ProductName"], r["cat"], int(r["qty"]), int(r["tx"]), int(r["net"])]
    top_qty = [row(i, r) for i, r in enumerate(byqty[:10], 1)]
    top_net = [row(i, r) for i, r in enumerate(bynet[:10], 1)]
    kat = df.groupby("Category")["NetSales"].sum().sort_values(ascending=False)
    kategori = [[k, int(v)] for k, v in kat.items()]

    # ---- anchor (rumus template: 0,6 x Transaksi + 0,4 x Total co-occurrence)
    partner = {}
    for a, b, v in raw_pairs:
        for x, y in ((a, b), (b, a)):
            if x not in partner: partner[x] = (y, v)
    np_ = max(len(prods) - 1, 1)
    anc = sorted(prods, key=lambda r: -(0.6 * r["tx"] + 0.4 * tot[r["ProductName"]]))
    anchors = []
    for i, r in enumerate(anc, 1):
        nm = r["ProductName"]; sc = 0.6 * r["tx"] + 0.4 * tot[nm]
        alasan = (f"Ada di {nf(r['tx'])} transaksi ({pc(r['tx'] / n)}) dan berpasangan dengan produk lain "
                  f"{nf(tot[nm])} kali; pasangan terkuat: {partner[nm][0]} ({nf(partner[nm][1])} transaksi).") if nm in partner else "-"
        anchors.append([i, nm, int(r["tx"]), int(tot[nm]), round(tot[nm] / np_, 2), round(sc, 1),
                        "Anchor utama" if i <= 5 else "Pendukung", alasan])
    top5 = [a[1] for a in anchors[:5]]

    layout = buat_layout(pairs, anchors, top5, tot, net_of, cat_of, price, n, tx)
    kes = buat_kesimpulan(info, df, top_qty, top_net, pairs, anchors, kategori, layout, n)

    data = dict(info=info, ringkas=dict(prod=len(prods), net=int(df["NetSales"].sum()), gross=int(df["TotalBeforeDiscount"].sum()),
                                        disc=int(df["DiscountAmount"].sum()), item_rata=round(len(df) / n, 2),
                                        keranjang_rata=round(df["NetSales"].sum() / n)),
                top_qty=top_qty, top_net=top_net, kategori=kategori, pairs=pairs, rules=rules,
                anchors=anchors, layout=layout, kesimpulan=kes, ambang=AMBANG_DEKAT)
    return df, data


def buat_layout(pairs, anchors, top5, tot, net_of, cat_of, price, n, tx):
    top10 = pairs[:10]
    par = {}
    def find(x):
        while par.setdefault(x, x) != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for p in top10:
        par[find(p[1])] = find(p[2])
    comps = collections.defaultdict(set)
    for p in top10:
        comps[find(p[1])].update([p[1], p[2]])
    comps = list(comps.values())
    pdict = {(p[1], p[2]): p for p in pairs}

    def best(c):
        return max([p[3] for p in top10 if p[1] in c and p[2] in c] or [0])
    def alasan_pairs(c):
        ps = [p for p in top10 if p[1] in c and p[2] in c][:3]
        return "; ".join(f"{p[1]} + {p[2]}: co-occurrence {nf(p[3])}, support {pc(p[4])}, lift {f2(p[9])}" for p in ps)

    pakai = []
    def ambil(c):
        comps.remove(c); pakai.append(c); return sorted(c)

    zona = []
    if comps:
        cA = max(comps, key=lambda c: (len(c & set(top5)), best(c)))
        ia = sorted(cA & set(top5))
        zona.append(["Zona A - Entry", "Rak 1", ambil(cA),
                     f"Berisi {len(ia)} dari 5 anchor product ({', '.join(ia)}). Barang paling sering dicari dan saling berpasangan, "
                     f"ditempatkan di depan untuk menarik pembeli masuk. {alasan_pairs(cA)}.", "Tinggi"])
    if comps:
        cB = max(comps, key=best)
        zona.append(["Zona B - Tengah", "Rak 2", ambil(cB),
                     f"Pasangan dengan support tertinggi di luar Zona A, jadi harus berdekatan agar cross selling terjadi. {alasan_pairs(cB)}.", "Tinggi"])
    dipakai = set().union(*pakai) if pakai else set()
    sisa_comp_items = set().union(*comps) if comps else set()
    bebas = [p for p in net_of if p not in dipakai and p not in sisa_comp_items]
    netcat = collections.Counter()
    for p in bebas: netcat[cat_of[p]] += net_of[p]
    if netcat:
        kat = netcat.most_common(1)[0][0]
        items = sorted([p for p in bebas if cat_of[p] == kat], key=lambda p: -net_of[p])
        zona.append(["Zona C - Kebutuhan Harian", "Rak 3", items,
                     f"Kategori {kat} memberi NetSales terbesar ({rp(netcat[kat])}) di antara produk yang belum masuk zona lain. "
                     f"Kebutuhan pokok dibeli rutin; pasangan antaritem saling menguatkan ({', '.join(a[1] for a in anchors[:5] if a[1] in items) or 'tanpa anchor utama'}).", "Sedang"])
        for p in items: dipakai.add(p)
    comps.sort(key=lambda c: -sum(net_of[p] for p in c))
    if comps:
        k = max(len(comps) - 1, 1) if len(comps) > 1 else 1
        D_items, E_items, d_al, e_al = [], [], [], []
        for c in comps[:k]:
            D_items += sorted(c); d_al.append(alasan_pairs(c))
        zona.append(["Zona D - Cross Selling", "Rak 4", D_items,
                     "Kelompok bernilai penjualan tinggi dan saling berpasangan, untuk mendorong pembelian tambahan. " + " | ".join(d_al) + ".", "Sedang"])
        for c in comps[k:]:
            E_items += sorted(c); e_al.append(alasan_pairs(c))
        if E_items:
            zona.append(["Zona E - Kasir", "Rak 5", E_items,
                         "Produk impuls bernilai satuan kecil, cocok dekat kasir karena sering menyertai belanja utama. " + " | ".join(e_al) + ".", "Sedang"])
    out = []
    for z in zona:
        ia = [p for p in z[2] if p in top5]
        out.append({"zona": z[0], "rak": z[1], "produk": z[2], "alasan": z[3],
                    "anchor": ("Ya (" + ", ".join(ia) + ")") if ia else "Tidak", "prioritas": z[4]})
    return out


def buat_kesimpulan(info, df, top_qty, top_net, pairs, anchors, kategori, layout, n):
    net = df["NetSales"].sum(); p1 = pairs[0]
    n_dekat = sum(1 for p in pairs if p[4] >= AMBANG_DEKAT)
    top10net = sum(r[5] for r in top_net)
    lifts = sorted([p for p in pairs if p[4] >= 0.04], key=lambda p: -p[9])[:1]
    L = lifts[0] if lifts else None
    zona_txt = "; ".join(f"{z['zona'].split(' - ')[0]}: {', '.join(z['produk'][:4])}{'...' if len(z['produk']) > 4 else ''}" for z in layout)
    return [
        {"judul": "1. Data Cleaning",
         "teks": f"Dari {nf(info['baris_awal'])} baris mentah ditemukan {nf(info['dup_sebelum'])} duplikat persis yang dihapus, sehingga tersisa "
                 f"{nf(info['baris_bersih'])} baris untuk {nf(info['trx'])} transaksi unik. CustomerID kosong ({nf(info['miss_c'])} baris) diberi label UNKNOWN "
                 f"dan DiscountPct kosong ({nf(info['miss_d'])} baris) dipulihkan dari nominal diskon bila ada. Validasi Qty × UnitPrice, diskon, dan NetSales "
                 f"menunjukkan {sum(v['selisih'] for v in info['validasi'])} selisih, sehingga data layak dipakai."},
        {"judul": "2. Produk Terlaris",
         "teks": f"Berdasarkan jumlah terjual, {top_qty[0][1]} paling laris ({nf(top_qty[0][3])} unit), disusul {top_qty[1][1]} dan {top_qty[2][1]}. "
                 f"Produk yang laris belum tentu bernilai terbesar, sehingga keputusan etalase tidak boleh hanya melihat Qty."},
        {"judul": "3. Kombinasi Barang",
         "teks": f"Pasangan teratas adalah {p1[1]} + {p1[2]} dengan co-occurrence {nf(p1[3])} transaksi (support {pc(p1[4])}, lift {f2(p1[9])}). "
                 f"{n_dekat} pasangan mencapai support ≥ {pc(AMBANG_DEKAT, 0)} dan langsung didekatkan; sisanya di top 10 menjadi prioritas evaluasi. "
                 + (f"Pasangan {L[1]} + {L[2]} punya lift tertinggi ({f2(L[9])}) walau supportnya {pc(L[4])}, sehingga layak dipertimbangkan untuk cross selling." if L else "")},
        {"judul": "4. NetSales",
         "teks": f"Total NetSales {rp(net)}. {top_net[0][1]} memberi NetSales terbesar ({rp(top_net[0][5])}), dan 10 produk teratas menyumbang {pc(top10net / net)} dari total. "
                 f"Kategori terbesar adalah {kategori[0][0]} ({rp(kategori[0][1])}). Produk bernilai tinggi perlu mendapat tempat yang mudah dilihat dan aman."},
        {"judul": "5. Keputusan Penempatan Etalase",
         "teks": f"Anchor utama: {', '.join(a[1] for a in anchors[:5])}. Susunan zona: {zona_txt}. "
                 f"Anchor di zona depan menarik pembeli ke dalam toko, pasangan bersupport tinggi didekatkan, dan produk impuls ditaruh dekat kasir."}]


# ---------------------------------------------------------------- EXCEL HASIL
def excel_hasil(df, data):
    from openpyxl.styles import Font, PatternFill, Alignment
    info = data["info"]
    buf = io.BytesIO()
    soal = [
        (1, "Identifikasi dan bersihkan duplikat persis.", f"Sebelum: {info['dup_sebelum']} duplikat; sesudah: {info['dup_sesudah']}. Baris {nf(info['baris_awal'])} menjadi {nf(info['baris_bersih'])}."),
        (2, "Tangani missing CustomerID dan DiscountPct.", f"CustomerID kosong {info['miss_c']} diisi UNKNOWN; DiscountPct kosong {info['miss_d']}: {info['dari_nominal']} dihitung dari DiscountAmount/TotalBeforeDiscount, {info['nol']} diisi 0%."),
        (3, "Validasi TotalBeforeDiscount, DiscountAmount, NetSales.", "; ".join(f"{v['nama']}: {v['selisih']} selisih ({v['status']})" for v in info["validasi"])),
        (4, "Top 10 produk berdasarkan TotalQty.", "Lihat sheet TOP10_QTY."), (5, "Top 10 produk berdasarkan NetSales.", "Lihat sheet TOP10_NETSALES."),
        (6, "Pasangan co-occurrence tertinggi.", "Lihat sheet KOMBINASI_BARANG."), (7, "Support pasangan barang.", "Kolom Support dan Interpretasi pada KOMBINASI_BARANG."),
        (8, "Anchor product.", "Lihat sheet ANCHOR_PRODUCT (5 teratas = anchor utama)."),
        (9, "Barang yang ditempatkan berdekatan.", "Kolom Keputusan pada KOMBINASI_BARANG."), (10, "Layout etalase.", "Lihat sheet LAYOUT_ETALASE."),
        (11, "Kesimpulan.", "Lihat sheet KESIMPULAN.")]
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame(soal, columns=["No", "Soal/Tugas", "Jawaban"]).to_excel(w, sheet_name="JAWABAN_SOAL", index=False)
        pd.DataFrame([[v["nama"], v["rumus"], v["dicek"], v["selisih"], v["hitung"], v["tercatat"], v["status"]] for v in info["validasi"]],
                     columns=["Kolom", "Rumus", "Baris dicek", "Selisih", "Hasil hitung", "Tercatat", "Status"]).to_excel(w, sheet_name="VALIDASI", index=False)
        cols = ["Rank", "Produk", "Kategori", "TotalQty", "Transaksi", "NetSales"]
        pd.DataFrame(data["top_qty"], columns=cols).to_excel(w, sheet_name="TOP10_QTY", index=False)
        pd.DataFrame(data["top_net"], columns=cols).to_excel(w, sheet_name="TOP10_NETSALES", index=False)
        pd.DataFrame([[p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10]] for p in data["pairs"]],
                     columns=["Rank", "Barang A", "Barang B", "CoOccurrence", "Support", "A Transaksi", "B Transaksi", "Conf A→B", "Conf B→A", "Lift", "Keputusan"]
                     ).to_excel(w, sheet_name="KOMBINASI_BARANG", index=False)
        pd.DataFrame(data["anchors"], columns=["Rank", "Produk", "Transaksi", "TotalCoOccurrence", "AvgPairCoOccurrence", "AnchorScore", "Peran", "Alasan"]
                     ).to_excel(w, sheet_name="ANCHOR_PRODUCT", index=False)
        pd.DataFrame([[z["zona"], z["rak"], ", ".join(z["produk"]), z["alasan"], z["anchor"], z["prioritas"]] for z in data["layout"]],
                     columns=["Zona", "Posisi/Rak", "Product/Pair", "Alasan Penempatan", "Anchor Product?", "Prioritas"]).to_excel(w, sheet_name="LAYOUT_ETALASE", index=False)
        pd.DataFrame([[k["judul"], k["teks"]] for k in data["kesimpulan"]], columns=["Tahap", "Kesimpulan"]).to_excel(w, sheet_name="KESIMPULAN", index=False)
        pd.DataFrame(data["rules"], columns=["Jika beli (A)", "Maka beli (B)", "Transaksi", "Support", "Confidence", "Lift"]).to_excel(w, sheet_name="ATURAN_APRIORI", index=False)
        df.to_excel(w, sheet_name="DATA_BERSIH", index=False)
        for ws in w.book.worksheets:
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF", name="Arial"); c.fill = PatternFill("solid", fgColor="0F5C6E")
                c.alignment = Alignment(vertical="center", wrap_text=True)
            for col in ws.columns:
                mx = max((len(str(c.value)) for c in list(col)[:200] if c.value is not None), default=8)
                ws.column_dimensions[col[0].column_letter].width = min(max(mx + 2, 10), 70)
            ws.freeze_panes = "A2"
            if ws.title in ("LAYOUT_ETALASE", "KESIMPULAN", "JAWABAN_SOAL"):
                for r in ws.iter_rows(min_row=2):
                    for c in r: c.alignment = Alignment(wrap_text=True, vertical="top")
    return buf.getvalue()


# ---------------------------------------------------------------- SERVER


# ---------------------------------------------------------------- PINTU MASUK UNTUK BROWSER (Pyodide)
def proses(isi, nama):
    """Dipanggil dari JavaScript: byte file Excel/CSV -> JSON hasil analisis + file Excel hasil (base64)."""
    try:
        isi = bytes(isi.to_py()) if hasattr(isi, "to_py") else bytes(isi)
        raw = baca(isi, nama)
        df, data = analisis(raw)
        xlsx = excel_hasil(df, data)
        data["file"] = nama
        return json.dumps({"ok": True, "data": data, "xlsx": base64.b64encode(xlsx).decode()}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
