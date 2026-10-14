# Gerbang bukti menuju target 95% kelengkapan proses

Angka 95% di sini berarti **proses pada suatu bagian memenuhi rubrik bukti yang disepakati**, bukan peluang prediksi benar. Tidak ada bobot atau skor numerik yang diberikan sebelum semua gerbang wajib mempunyai definisi dan data uji. Status berikut didasarkan pada artefak yang benar-benar dijalankan dalam checkout ini.

| Bagian | Bukti yang sudah ada | Gerbang wajib yang belum lulus |
| --- | --- | --- |
| Statistik | Audit skor final penuh dalam enam musim Premier League/Bundesliga dan lima musim Eredivisie; 234.637 event dan 1.453 tembakan StatsBomb dari 64 pertandingan Piala Dunia 2022, dengan pemeriksaan kalibrasi xG. | Rekonsiliasi xG antarprovider/kompetisi dan ketersediaan data historis menurut waktu prediksi; kalibrasi ini belum merupakan holdout independen. |
| Taktik berbasis data | 3.680 event dan tracking dua game Metrica anonim; 16.554 event tekanan tercatat dalam 64 game StatsBomb. | Tag video atau event taktik yang divalidasi antar analis; bukti bahwa metrik taktik meningkatkan keputusan/prediksi. Jumlah tekanan sendiri belum membuktikan intensi atau hasil pressing. |
| Kondisi skuad | Pemeriksa waktu bukti, konflik status, 128 starting XI historis StatsBomb; daftar skuad dan badge UEFA untuk 14 tim mendatang. | Timestamp publikasi badge, starting XI resmi sebelum kick-off, audit kelengkapan roster dan cedera/skorsing aktual, validasi dampak absensi. |
| Probabilitas | Elo, Poisson, campuran, peluang 1X2, log loss/Brier/RPS/ECE, uji sensitivitas antar liga; pembanding odds rata-rata untuk 760 laga EPL. | Kalibrasi yang stabil lintas waktu/liga, odds bertimestamp per kutipan, uji yang belum tersentuh setelah pemilihan model. Pasar unggul atas model pada sampel EPL ini. |
| Validasi historis | 760 + 612 + 306 = **1.678** prediksi uji lintas tiga liga; bootstrap berpasangan; hasil EPL cocok sepenuhnya dengan 760 baris odds pasar. | Audit timestamp publikasi sumber, pengujian prospektif, dan evaluasi fitur skuad/taktik di luar baseline. Bundesliga termasuk eksplorasi karena cacat model ditemukan saat mengujinya. |
| Riset dan rancangan | Protokol, sumber data, versi commit, checksum, batasan, langkah reproduksi; sembilan jadwal dan status UEFA terverifikasi, empat label matchday pengguna dikoreksi. | Verifikasi kurikulum/metode yang dikutip dalam percakapan lama dari sumber resmi serta pembuktian manfaatnya dalam workflow ini. |

**Akses saat audit:** `www.football-data.co.uk`, `www.uefa.com`, dan `match.uefa.com` berhasil diakses pada 14 Oktober 2026 UTC. Domain tersebut telah dicatat dalam draft konfigurasi lingkungan. Jadwal sembilan kandidat laga 14–15 Oktober WIB telah cocok dengan halaman UEFA; dua berstatus Live dan tujuh Upcoming saat diambil. Ketersediaan pemain dan odds spesifik pertandingan belum mempunyai bukti bertimestamp yang cukup. Tidak ada kredensial feed premium di lingkungan yang ditemukan melalui nama variabel yang relevan.

Skor 95% untuk keenam bagian tidak boleh dideklarasikan sampai gerbang wajib di atas lulus. Dua game anonim, 64 pertandingan dari satu turnamen, atau 1.678 prediksi uji tidak dapat dijadikan pengganti bukti tersebut.
