"""
TUGAS MULTIMEDIA - GAMBAR MENJADI BERGERAK DAN BERSUARA
========================================================
Hewan  : Serigala (Canis lupus)
Input  : serigala_jalan.png      -> gambar serigala pose berjalan
         serigala.png            -> gambar serigala pose melolong
         lolongan_serigala.mp3   -> suara angin malam + lolongan serigala
Output : serigala_bergerak.mp4   -> video gambar bergerak + bersuara

Alur cerita video (14 detik):
  1. Detik 0,0-5,2 : serigala BERJALAN masuk dari kiri layar.
     Kakinya bergerak sungguhan dengan teknik walk cycle: gambar
     dipotong menjadi badan dan 4 kaki, lalu setiap kaki diputar
     bergantian pada poros pangkal kakinya (seperti animasi 2D).
     Badan ikut naik-turun halus, latar ikut bergeser (parallax).
  2. Detik 5,2-5,55: serigala berhenti, berganti pose menjadi pose
     melolong (crossfade cepat), lalu bersiap.
  3. Detik 5,9-13,0: serigala MENGAUNG / melolong di bawah bulan.
     Gelombang suara keluar dari mulutnya tepat bersamaan dengan
     suara lolongan pada audio, badan dan cahaya bulan berdenyut.
  4. Detik 13,0-14 : fade-out, video selesai.

Teknik menghapus background putih:
  Flood-fill dari tepi gambar: piksel yang nyaris putih DAN terhubung
  ke tepi gambar dianggap background. Bulu putih di bagian dalam
  tubuh tidak ikut terhapus karena terhalang outline gambar.

Audio lolongan_serigala.mp3 dibuat dari rekaman lolongan serigala
asli "Wolf howls" (Wikimedia Commons) yang diberi jeda di awal
(supaya lolongan mulai tepat saat serigala berhenti berjalan),
dicampur suara angin malam pelan selama fase berjalan.

Kebutuhan:
  pip install pillow numpy scipy
  Program FFmpeg harus sudah terinstall (perintah: ffmpeg)

Jalankan:
  python buat_serigala_bergerak.py
"""

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
FOLDER = Path(__file__).parent
FILE_JALAN = FOLDER / "serigala_jalan.png"
FILE_LOLONG = FOLDER / "serigala.png"
FILE_SUARA = FOLDER / "lolongan_serigala.mp3"
FILE_VIDEO = FOLDER / "serigala_bergerak.mp4"

LEBAR, TINGGI = 1280, 720     # resolusi video (HD 720p)
FPS = 30                      # frame per detik
DURASI = 14                   # durasi video (detik)
TOTAL_FRAME = FPS * DURASI

# Pembagian fase animasi (detik)
AKHIR_JALAN = 5.2             # serigala berjalan sampai detik ini
AKHIR_GANTI_POSE = 5.55       # crossfade pose jalan -> pose lolong
MULAI_AUNG = 5.9              # suara lolongan mulai (sinkron dgn audio)
AKHIR_AUNG = 13.0             # lolongan selesai, mulai fade-out

# Posisi mulut pada gambar pose melolong (persen lebar/tinggi gambar)
MULUT_X, MULUT_Y = 0.90, 0.10

# Posisi akhir serigala setelah berjalan (kiri atas area tampil)
TARGET_X = 160
TANAH_Y = TINGGI - 28         # garis telapak kaki serigala
LEBAR_TAMPIL = 780            # lebar tampil serigala di video (piksel)


# ---------------------------------------------------------------------------
# Langkah 1 - Hapus background putih pada gambar
# ---------------------------------------------------------------------------
def hapus_background_putih(path_gambar):
    """Mengembalikan gambar RGBA dengan background transparan."""
    gambar = Image.open(path_gambar).convert("RGB")
    piksel = np.array(gambar)

    nyaris_putih = (
        (piksel[:, :, 0] > 240)
        & (piksel[:, :, 1] > 240)
        & (piksel[:, :, 2] > 240)
    )
    # Kelompok piksel putih yang menyentuh tepi = background
    label, _ = ndimage.label(nyaris_putih)
    label_tepi = set(np.unique(np.concatenate([
        label[0, :], label[-1, :], label[:, 0], label[:, -1]
    ])))
    label_tepi.discard(0)
    background = np.isin(label, list(label_tepi))

    alpha = np.where(background, 0, 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1))

    hasil = gambar.convert("RGBA")
    hasil.putalpha(alpha_img)
    return hasil.crop(hasil.getbbox())


# ---------------------------------------------------------------------------
# Langkah 2 - Rig walk cycle: potong gambar jalan menjadi badan + 4 kaki
# ---------------------------------------------------------------------------
def buat_rig_jalan(serigala_jalan, y_potong_badan=0.64):
    """
    Memotong gambar pose berjalan menjadi:
      - badan (digambar paling atas, menutupi pangkal kaki)
      - 4 potongan kaki yang bisa diputar pada poros pangkalnya.
    Kelompok kaki dicari otomatis dari proyeksi piksel pada area
    bawah gambar. Pasangan kaki diagonal bergerak sefase (gaya trot):
    (kaki depan dekat + kaki belakang jauh) berlawanan fase dengan
    (kaki depan jauh + kaki belakang dekat).
    """
    lebar, tinggi = serigala_jalan.size
    alpha = np.array(serigala_jalan.getchannel("A"))

    # Proyeksi piksel tidak transparan pada 32% bagian bawah gambar
    proyeksi = (alpha[int(tinggi * 0.68):, :] > 30).sum(axis=0)
    kelompok = []
    awal = None
    for x, nilai in enumerate(proyeksi):
        if nilai > 5 and awal is None:
            awal = x
        elif nilai <= 5 and awal is not None:
            if x - awal > lebar * 0.02:
                kelompok.append((awal, x))
            awal = None
    if awal is not None:
        kelompok.append((awal, lebar))
    assert len(kelompok) == 4, f"Kaki terdeteksi {len(kelompok)}, harusnya 4"

    y_potong_badan = int(tinggi * y_potong_badan)   # badan menutupi sampai sini
    y_mulai_kaki = int(tinggi * 0.46)     # potongan kaki mulai dari sini
    badan = serigala_jalan.crop((0, 0, lebar, y_potong_badan))

    # Urutan kelompok dari kiri: belakang-dekat, belakang-jauh,
    # depan-dekat, depan-jauh. Fase trot: kelompok 0 & 3 sefase,
    # kelompok 1 & 2 berlawanan.
    fase_kaki = [0.0, math.pi, math.pi, 0.0]
    kaki = []
    for (x0, x1), fase in zip(kelompok, fase_kaki):
        tepi = int(lebar * 0.02)
        x_kiri = max(0, x0 - tepi)
        x_kanan = min(lebar, x1 + tepi)
        potongan = serigala_jalan.crop((x_kiri, y_mulai_kaki, x_kanan, tinggi))
        kaki.append({
            "gambar": potongan,
            "x": x_kiri,
            "y": y_mulai_kaki,
            "poros_x": (x0 + x1) // 2 - x_kiri,  # poros putar (pangkal kaki)
            "poros_y": int(tinggi * 0.06),
            "fase": fase,
        })
    return {"badan": badan, "kaki": kaki, "ukuran": (lebar, tinggi)}


def gambar_serigala_jalan(rig, fase_jalan, kekuatan=1.0):
    """
    Merakit satu frame pose berjalan.
    fase_jalan : sudut siklus langkah (radian, bertambah selama berjalan)
    kekuatan   : 1 = melangkah penuh, 0 = kaki diam (dipakai saat berhenti)
    """
    lebar, tinggi = rig["ukuran"]
    kanvas = Image.new("RGBA", (lebar, tinggi), (0, 0, 0, 0))
    for kaki in rig["kaki"]:
        sudut = 8.0 * kekuatan * math.sin(fase_jalan + kaki["fase"])
        potongan = kaki["gambar"].rotate(
            sudut, resample=Image.BICUBIC,
            center=(kaki["poros_x"], kaki["poros_y"]),
        )
        kanvas.alpha_composite(potongan, (kaki["x"], kaki["y"]))
    # Badan digambar terakhir supaya menutupi pangkal kaki
    kanvas.alpha_composite(rig["badan"], (0, 0))
    return kanvas


# ---------------------------------------------------------------------------
# Langkah 3 - Latar malam
# ---------------------------------------------------------------------------
def buat_latar():
    latar = Image.new("RGB", (LEBAR, TINGGI))
    piksel = np.zeros((TINGGI, LEBAR, 3), dtype=np.uint8)
    atas = np.array([8, 12, 38], dtype=float)
    bawah = np.array([52, 78, 128], dtype=float)
    for y in range(TINGGI):
        piksel[y, :, :] = atas + (bawah - atas) * (y / TINGGI)
    latar = Image.fromarray(piksel, "RGB").convert("RGBA")
    gambar = ImageDraw.Draw(latar, "RGBA")

    rng = np.random.default_rng(42)
    bintang = []
    for _ in range(140):
        bx, by = int(rng.integers(0, LEBAR)), int(rng.integers(0, 430))
        br = float(rng.uniform(1, 2.4))
        bintang.append((bx, by, br))
        gambar.ellipse([bx - br, by - br, bx + br, by + br],
                       fill=(255, 255, 255, 210))

    gunung = [(0, 520), (180, 400), (340, 500), (520, 390), (700, 505),
              (880, 410), (1050, 510), (1280, 430), (1280, 720), (0, 720)]
    gambar.polygon(gunung, fill=(38, 52, 86, 255))

    gambar.ellipse([-200, 560, LEBAR + 200, 900], fill=(22, 34, 30, 255))
    return latar, bintang, rng


def buat_bulan():
    ukuran = 340
    bulan = Image.new("RGBA", (ukuran, ukuran), (0, 0, 0, 0))
    d = ImageDraw.Draw(bulan)
    for r in range(150, 78, -6):
        alpha = int(70 * (150 - r) / 72)
        d.ellipse([ukuran / 2 - r, ukuran / 2 - r, ukuran / 2 + r, ukuran / 2 + r],
                  fill=(240, 240, 200, alpha))
    d.ellipse([ukuran / 2 - 78, ukuran / 2 - 78, ukuran / 2 + 78, ukuran / 2 + 78],
              fill=(245, 242, 214, 255))
    for dx, dy, r in [(-28, -18, 13), (18, 12, 17), (-6, 34, 9), (34, -30, 8)]:
        d.ellipse([ukuran / 2 + dx - r, ukuran / 2 + dy - r,
                   ukuran / 2 + dx + r, ukuran / 2 + dy + r],
                  fill=(226, 221, 192, 255))
    return bulan


def gambar_pinus(d, x, pangkal, tinggi):
    d.rectangle([x - 4, pangkal - 26, x + 4, pangkal], fill=(10, 18, 16, 255))
    for i in range(3):
        lebar_i = (tinggi * 0.42) * (1 - i * 0.26)
        y_atas = pangkal - 20 - (i + 1) * (tinggi / 3.4)
        y_bawah = pangkal - 10 - i * (tinggi / 3.4)
        d.polygon([(x - lebar_i / 2, y_bawah), (x + lebar_i / 2, y_bawah),
                   (x, y_atas)], fill=(10, 18, 16, 255))


# ---------------------------------------------------------------------------
# Langkah 4 - Animasi per frame
# ---------------------------------------------------------------------------
def muat_font(ukuran):
    for kandidat in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]:
        if Path(kandidat).exists():
            return ImageFont.truetype(kandidat, ukuran)
    return ImageFont.load_default()


def atur_opasitas(gambar_rgba, faktor):
    hasil = gambar_rgba.copy()
    a = hasil.getchannel("A").point(lambda v: int(v * faktor))
    hasil.putalpha(a)
    return hasil


def main():
    for berkas in (FILE_JALAN, FILE_LOLONG, FILE_SUARA):
        if not berkas.exists():
            sys.exit(f"File {berkas.name} tidak ditemukan di folder script.")

    print("1. Menghapus background kedua gambar serigala...")
    lolong_asli = hapus_background_putih(FILE_LOLONG)
    jalan_asli = hapus_background_putih(FILE_JALAN)

    # Samakan skala kedua pose berdasarkan lebar tampil
    def skala_ke_lebar_tampil(gambar):
        rasio = LEBAR_TAMPIL / gambar.width
        return gambar.resize((LEBAR_TAMPIL, int(gambar.height * rasio)),
                             Image.LANCZOS)

    lolong = skala_ke_lebar_tampil(lolong_asli)
    jalan_skala = skala_ke_lebar_tampil(jalan_asli)
    rig = buat_rig_jalan(jalan_skala)
    pose_diam = gambar_serigala_jalan(rig, 0.0, kekuatan=0.0)

    print("2. Menyiapkan latar malam...")
    latar, bintang, rng = buat_latar()
    bulan = buat_bulan()
    font_judul = muat_font(44)
    font_kecil = muat_font(24)
    # Titik-titik tanah untuk efek parallax saat berjalan
    titik_tanah = [(int(rng.integers(0, 400)), int(rng.integers(648, 706)),
                    float(rng.uniform(2, 4))) for _ in range(26)]

    x_awal = -520                    # posisi masuk (sebagian di luar layar kiri)
    jarak_total = TARGET_X - x_awal

    print("3. Merender", TOTAL_FRAME, "frame dan menggabungkan suara...")
    perintah = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{LEBAR}x{TINGGI}", "-r", str(FPS),
        "-i", "-",
        "-i", str(FILE_SUARA),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(FILE_VIDEO),
    ]
    proses = subprocess.Popen(perintah, stdin=subprocess.PIPE,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for frame in range(TOTAL_FRAME):
        detik = frame / FPS
        kanvas = latar.copy()
        d = ImageDraw.Draw(kanvas, "RGBA")

        # Bintang berkelip
        for i, (bx, by, br) in enumerate(bintang):
            kelip = 0.5 + 0.5 * math.sin(detik * 2 + i * 1.7)
            r = br * (0.7 + 0.5 * kelip)
            d.ellipse([bx - r, by - r, bx + r, by + r],
                      fill=(255, 255, 255, int(120 + 120 * kelip)))

        # Fase saat ini
        berjalan = detik < AKHIR_JALAN
        mengganti = AKHIR_JALAN <= detik < AKHIR_GANTI_POSE
        melolong = MULAI_AUNG <= detik <= AKHIR_AUNG
        denyut = (0.5 + 0.5 * math.sin(detik * 3.2)) if melolong else 0.0

        # Bulan (cahayanya berdenyut saat melolong)
        skala_bulan = 1.0 + 0.05 * denyut
        ukuran_bulan = int(340 * skala_bulan)
        bulan_frame = bulan.resize((ukuran_bulan, ukuran_bulan), Image.LANCZOS)
        kanvas.alpha_composite(bulan_frame, (LEBAR - ukuran_bulan - 40, 20))

        # Kemajuan perjalanan serigala (0 = di luar layar, 1 = sampai)
        if berjalan:
            p = detik / AKHIR_JALAN
            kemajuan = p * p * (3 - 2 * p)        # smoothstep
        else:
            kemajuan = 1.0
        posisi_x = int(x_awal + jarak_total * kemajuan)
        jarak_tempuh = posisi_x - x_awal

        # Parallax: pohon dan titik tanah bergeser selama serigala berjalan
        for x0, t in [(60, 190), (130, 140), (1150, 170), (1220, 130), (1085, 110)]:
            xp = (x0 - int(jarak_tempuh * 0.25)) % (LEBAR + 160) - 80
            gambar_pinus(d, xp, 640, t)
        geser_tanah = int(jarak_tempuh * 0.6) % 400
        for tx, ty, tr in titik_tanah:
            for salinan in range(4):
                d.ellipse([tx + salinan * 400 - geser_tanah - tr, ty - tr,
                           tx + salinan * 400 - geser_tanah + tr, ty + tr],
                          fill=(70, 96, 82, 255))

        # --- Serigala ---
        if berjalan:
            # Walk cycle: fase langkah + badan naik-turun mengikuti langkah
            fase = detik * (2 * math.pi / 0.85)
            serigala = gambar_serigala_jalan(rig, fase, kekuatan=1.0)
            naik = -int(5 * abs(math.sin(fase)))
            kanvas.alpha_composite(serigala, (posisi_x, TANAH_Y - serigala.height + naik))
        elif mengganti:
            # Berhenti: kaki kembali netral, pose berubah menjadi melolong
            q = (detik - AKHIR_JALAN) / (AKHIR_GANTI_POSE - AKHIR_JALAN)
            serigala_jalan_frame = gambar_serigala_jalan(rig, 0.0, kekuatan=1.0 - q)
            kanvas.alpha_composite(atur_opasitas(serigala_jalan_frame, 1.0 - q),
                                   (posisi_x, TANAH_Y - serigala_jalan_frame.height))
            lh = int(lolong.height * (1.0 + 0.0 * q))
            kanvas.alpha_composite(atur_opasitas(lolong, q),
                                   (posisi_x, TANAH_Y - lh))
        else:
            # Pose melolong: badan berdenyut halus mengikuti suara
            skala = 1.0 + 0.022 * denyut
            lw = int(LEBAR_TAMPIL * skala)
            lh = int(lolong.height * skala)
            serigala = lolong.resize((lw, lh), Image.LANCZOS)
            naik = int(7 * denyut)
            kanvas.alpha_composite(serigala, (posisi_x, TANAH_Y - lh - naik))

            # Gelombang suara dari mulut
            if melolong:
                mulut_x = posisi_x + int(lw * MULUT_X)
                mulut_y = TANAH_Y - lh - naik + int(lh * MULUT_Y)
                for gelombang in range(3):
                    fase_g = ((detik * 0.9) + gelombang / 3) % 1.0
                    radius = int(18 + fase_g * 120)
                    alpha_g = int(190 * (1 - fase_g))
                    d.ellipse([mulut_x - radius, mulut_y - radius,
                               mulut_x + radius, mulut_y + radius],
                              outline=(255, 255, 220, alpha_g), width=4)

        # Judul
        if detik >= 1.0:
            alpha_teks = min(255, int((detik - 1.0) / 1.0 * 255))
            d.text((42, 36), "SERIGALA", font=font_judul,
                   fill=(255, 255, 255, alpha_teks))
            d.text((44, 90), "Canis lupus - Berjalan, lalu Mengaung di Bawah Bulan",
                   font=font_kecil, fill=(210, 220, 240, alpha_teks))

        # Fade-out 1 detik terakhir
        if detik > DURASI - 1:
            gelap = Image.new("RGBA", (LEBAR, TINGGI),
                              (0, 0, 0, int(255 * (detik - (DURASI - 1)))))
            kanvas.alpha_composite(gelap)

        proses.stdin.write(kanvas.convert("RGBA").tobytes())

    proses.stdin.close()
    proses.wait()
    print("4. Selesai ->", FILE_VIDEO)


if __name__ == "__main__":
    main()
