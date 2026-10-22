# Serigala Bergerak dan Bersuara (Python)

Tugas Multimedia: mengubah gambar diam hewan serigala menjadi video yang
bergerak dan bersuara, dibuat dengan Python (Pillow, NumPy, SciPy, FFmpeg).

**Halaman tugas (GitHub Pages):** https://aaronabil.github.io/serigala-bergerak/

Halamannya interaktif: serigala berjalan terus di panggung (walk cycle),
klik serigalanya atau tekan Spasi untuk mengaum, ada slider kecepatan
dan volume, dan equalizer yang bergerak mengikuti suara (Web Audio API).
Di halaman yang sama ada juga versi video MP4 hasil program Python.

Isi repo:
- `index.html` - halaman GitHub Pages interaktif
- `rig.js` - data poros putar kaki untuk walk cycle
- `badan.png`, `kaki1-4.png` - lapisan gambar pose berjalan
- `serigala_aung.png` - gambar pose melolong transparan
- `aungan.mp3` - suara aungan untuk halaman interaktif
- `serigala_bergerak.mp4` - video hasil program Python (14 detik, 720p)
- `buat_serigala_bergerak.py` - program Python pembuat video
- `serigala_jalan.png`, `serigala.png` - gambar sumber kedua pose
- `lolongan_serigala.mp3` - audio video (angin malam + lolongan)
- `poster.jpg` - gambar sampul pemutar video

Menjalankan ulang program video:
```
pip install pillow numpy scipy
python buat_serigala_bergerak.py
```
(FFmpeg harus terinstall.)

Suara lolongan: rekaman "Wolf howls", Wikimedia Commons.

Muhamad Nabil Faiz Amrullah - NIM 242502040042 - Kelas 3TI01
