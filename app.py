import streamlit as st
import fitz
import re
from collections import defaultdict
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Perbandingan Nopol", layout="wide")
st.title("📊 Perbandingan Nopol DASI vs SAM32")

def extract_nopol_sam32(files):
    plat_valid = {'B', 'D', 'E', 'F', 'T', 'Z'}
    hasil = {}
    pattern_nopol = re.compile(r'^([A-Z]{1,2})\s+(\d{1,4})\s+([A-Z]{1,3})$')
    pattern_tanggal = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    warna_patokan = {'HITAM', 'PUTIH', 'KUNING', 'MERAH'}

    for uploaded_file in files:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page in doc:
            lines = [line.strip() for line in page.get_text().splitlines() if line.strip()]
            i = 0
            while i < len(lines) - 2:
                baris1 = lines[i]
                baris3 = lines[i + 2]
                match_nopol = pattern_nopol.match(baris1)
                match_tanggal = pattern_tanggal.match(baris3)

                if match_nopol and match_tanggal:
                    kolom_sebelumnya = lines[i-3:i] if i >= 3 else []
                    awalan, angka, akhiran = match_nopol.groups()
                    if awalan in plat_valid:
                        nopol = f"{awalan} {angka} {akhiran}"
                        pokok = denda = jumlah = '-'

                        blok = lines[i+3 : min(i+50, len(lines))]
                        for idx, val in enumerate(blok):
                            if val.strip().upper() in warna_patokan and idx >= 5:
                                try:
                                    pokok = blok[idx - 5]
                                    denda = blok[idx - 4]
                                    jumlah = blok[idx - 3]
                                except IndexError:
                                    pokok = denda = jumlah = '-'
                                break

                        jika_belum_cetak = any("belum cetak" in baris.lower() for baris in kolom_sebelumnya)
                        try:
                            pokok_int = int(str(pokok).replace(",", "").replace(".", ""))
                            denda_int = int(str(denda).replace(",", "").replace(".", ""))
                        except:
                            pokok_int = denda_int = 0

                        if jika_belum_cetak and pokok_int == 0 and denda_int == 0:
                            i += 6
                            continue

                        hasil[nopol] = {
                            'pokok': pokok,
                            'denda': denda,
                            'jumlah': jumlah
                        }
                    i += 6
                else:
                    i += 1
    return hasil

def extract_nopol_lhp(files):
    hasil = defaultdict(lambda: {'pokok': 0, 'denda': 0, 'jumlah': 0})
    pattern_nopol = re.compile(r'([A-Z]{1,2})\s*-\s*(\d{1,4})\s*-\s*([A-Z]{1,3})')

    for uploaded_file in files:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page in doc:
            lines = [line.strip() for line in page.get_text().splitlines() if line.strip()]
            for idx, line in enumerate(lines):
                match = pattern_nopol.search(line)
                if match:
                    awalan, angka, akhiran = match.groups()
                    nopol = f"{awalan} {angka} {akhiran}"

                    block = lines[max(0, idx - 5):min(len(lines), idx + 6)]

                    try:
                        pokok = int(block[2].replace(",", "").replace(".", ""))
                        denda = int(block[10].replace(",", "").replace(".", ""))
                        jumlah = pokok + denda
                    except (IndexError, ValueError):
                        pokok = denda = jumlah = 0

                    hasil[nopol]['pokok'] += pokok
                    hasil[nopol]['denda'] += denda
                    hasil[nopol]['jumlah'] += jumlah
    return hasil

# === Upload UI ===
sam32_files = st.file_uploader("📁 Upload File SAM32", type="pdf", accept_multiple_files=True)
lhp_files = st.file_uploader("📁 Upload File DASI (LHP)", type="pdf", accept_multiple_files=True)

if st.button("🔍 BANDINGKAN") and sam32_files and lhp_files:
    nopol_sam32_map = extract_nopol_sam32(sam32_files)
    nopol_lhp_map = extract_nopol_lhp(lhp_files)

    nopol_sam32 = set(nopol_sam32_map.keys())
    nopol_lhp = set(nopol_lhp_map.keys())

    hanya_di_lhp = sorted(nopol_lhp - nopol_sam32)
    hanya_di_sam32 = sorted(nopol_sam32 - nopol_lhp)

    # === DASI ===
    lhp_data = []
    subtotal_lhp = 0
    for nopol in hanya_di_lhp:
        data = nopol_lhp_map.get(nopol, {})
        lhp_data.append({"nopol": nopol, **data})
        subtotal_lhp += data.get("jumlah", 0)

    st.markdown(f"### 📌 Nopol HANYA di DASI ({len(hanya_di_lhp)}) (Subtotal: {subtotal_lhp:,}):")
    for row in lhp_data:
        st.write(f"{row['nopol']} → POKOK: {row['pokok']:,}, DENDA: {row['denda']:,}, JUMLAH: {row['jumlah']:,}")

    # === SAM32 ===
    sam32_data = []
    subtotal_sam32 = 0
    for nopol in hanya_di_sam32:
        data = nopol_sam32_map.get(nopol, {})
        try:
            pokok = int(str(data.get('pokok', '0')).replace(".", "").replace(",", ""))
            denda = int(str(data.get('denda', '0')).replace(".", "").replace(",", ""))
            jumlah = int(str(data.get('jumlah', '0')).replace(".", "").replace(",", ""))
        except:
            pokok = denda = jumlah = 0
        sam32_data.append({"nopol": nopol, "pokok": pokok, "denda": denda, "jumlah": jumlah})
        subtotal_sam32 += jumlah

    st.markdown(f"### 📌 Nopol HANYA di SAM32 ({len(hanya_di_sam32)}) (Subtotal: {subtotal_sam32:,}):")
    for row in sam32_data:
        st.write(f"{row['nopol']} → POKOK: {row['pokok']:,}, DENDA: {row['denda']:,}, JUMLAH: {row['jumlah']:,}")

    # === DOWNLOAD EXCEL ===
    df_lhp = pd.DataFrame(lhp_data)
    df_sam32 = pd.DataFrame(sam32_data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_lhp.to_excel(writer, index=False, sheet_name="Hanya di DASI")
        df_sam32.to_excel(writer, index=False, sheet_name="Hanya di SAM32")
    output.seek(0)

    st.download_button(
        label="⬇️ Download Hasil ke Excel",
        data=output,
        file_name="hasil_perbandingan.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
