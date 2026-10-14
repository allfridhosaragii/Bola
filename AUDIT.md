# Gerbang bukti menuju target 95% kelengkapan proses

Angka 95% di sini berarti **proses pada suatu bagian memenuhi rubrik bukti yang disepakati**, bukan peluang prediksi benar. Tidak ada bobot atau skor numerik yang diberikan sebelum semua gerbang wajib mempunyai definisi dan data uji. Status berikut didasarkan pada artefak yang benar-benar dijalankan dalam checkout ini.

| Bagian | Bukti yang sudah ada | Gerbang wajib yang belum lulus |
| --- | --- | --- |
| Statistik | Audit skor final penuh dalam enam musim Premier League/Bundesliga dan lima musim Eredivisie; 234.637 event dan 1.453 tembakan StatsBomb dari 64 pertandingan Piala Dunia 2022, dengan pemeriksaan kalibrasi xG. | Rekonsiliasi xG antarprovider/kompetisi dan ketersediaan data historis menurut waktu prediksi; kalibrasi ini belum merupakan holdout independen. |
| Taktik berbasis data | 3.680 event dan tracking dua game Metrica anonim; 16.554 event tekanan tercatat dalam 64 game StatsBomb. | Tag video atau event taktik yang divalidasi antar analis; bukti bahwa metrik taktik meningkatkan keputusan/prediksi. Jumlah tekanan sendiri belum membuktikan intensi atau hasil pressing. |
| Kondisi skuad | Pemeriksa waktu bukti, konflik status, serta 128 starting XI StatsBomb yang cocok dari dua struktur sumber historis. | Sumber resmi sebelum kick-off untuk pertandingan target, cedera/skorsing aktual, audit kelengkapan roster, validasi dampak absensi. |
| Probabilitas | Elo, Poisson, campuran, peluang 1X2, log loss/Brier/RPS/ECE, uji sensitivitas antar liga. | Kalibrasi yang stabil lintas waktu/liga, benchmark odds bertimestamp, uji yang belum tersentuh setelah pemilihan model. |
| Validasi historis | 760 + 612 + 306 = **1.678** prediksi uji lintas tiga liga; bootstrap berpasangan dan pemeriksaan hasil satu hari. | Audit timestamp publikasi sumber, benchmark pasar, pengujian prospektif, dan evaluasi fitur skuad/taktik di luar baseline. Bundesliga termasuk eksplorasi karena cacat model ditemukan saat mengujinya. |
| Riset dan rancangan | Protokol, sumber data, versi commit, checksum, batasan, dan langkah reproduksi terdokumentasi. | Verifikasi kurikulum/metode yang dikutip dalam percakapan lama dari sumber resmi serta pembuktian manfaatnya dalam workflow ini. |

**Hambatan eksternal saat ini:** akses HTTP langsung ke `www.football-data.co.uk` dan `www.uefa.com` mendapat respons proxy `CONNECT 403`. Domain `football-data.co.uk`, `www.football-data.co.uk`, `uefa.com`, dan `www.uefa.com` telah ditambahkan dalam draft konfigurasi lingkungan; draft belum diterapkan/publikasi. Pengguna telah memberi sembilan kandidat laga 14–15 Oktober 2026 WIB, tetapi belum ada yang terverifikasi terhadap jadwal pertandingan resmi. Dua kandidat pukul 23.45 WIB sudah melewati waktu mulai yang dilaporkan saat pemeriksaan pukul 23.47 WIB; tujuh kandidat pukul 02.00 WIB belum. Tidak ada kredensial feed premium di lingkungan yang ditemukan melalui nama variabel yang relevan.

Skor 95% untuk keenam bagian tidak boleh dideklarasikan sampai gerbang wajib di atas lulus. Dua game anonim, 64 pertandingan dari satu turnamen, atau 1.678 prediksi uji tidak dapat dijadikan pengganti bukti tersebut.
