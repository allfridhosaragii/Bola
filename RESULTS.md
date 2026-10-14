# Hasil audit dan pengujian Bola

Kode dan perintah tersedia di [README.md](README.md). Hasil probabilitas 1X2 di bawah berbasis **skor akhir historis**; audit StatsBomb memakai event pertandingan setelah laga. Ini bukan laporan taruhan atau analisis Feyenoord–Como. Sumber skor: [OpenFootball football.json](https://github.com/openfootball/football.json), commit `e6744429ee395bc86f247348c6184bb08d4eb361`.

## Audit StatsBomb seluruh Piala Dunia 2022

Pada 64 pertandingan, pemeriksa membaca 234.637 event dan mencocokkan 128 starting XI dengan dua struktur data sumber. Ada 1.453 tembakan sebelum adu penalti, 169 gol dari event tembakan, total xG 155,8987 termasuk penalti dan 137,8782 tanpa penalti. Sebanyak 41 tembakan adu penalti dikecualikan. Pemeriksaan deskriptif kalibrasi xG tingkat tembakan menghasilkan Brier 0,0781, log loss 0,2715, dan ECE 10 bin 0,0131; Brier prediktor konstan dengan frekuensi gol sampel ini 0,1028. Hasil ini berasal dari satu turnamen; riwayat pelatihan model xG StatsBomb tidak diketahui di sini, sehingga bukan validasi holdout independen. Rincian ada di `reports/worldcup.json` setelah skrip dijalankan.

## Kualitas data

| Liga dan musim | Skor `score.ft` | Skor array | Total |
| --- | ---: | ---: | ---: |
| Premier League 2020/21–2024/25 | 1.900 | 0 | 1.900 |
| Premier League 2025/26 | 353 | 27 | 380 |
| Bundesliga 2020/21–2024/25 | 1.530 | 0 | 1.530 |
| Bundesliga 2025/26 | 294 | 12 | 306 |
| Eredivisie 2020/21–2024/25 | 1.530 | 0 | 1.530 |

Setiap musim di atas memiliki seluruh pasangan kandang–tandang unik dan skor final. Klaim lama tentang 2.253 hasil Premier League dalam enam musim dan 733 laga uji melewatkan 27 hasil berformat array. Jumlah yang benar di snapshot ini adalah **2.280 hasil** dan **760 laga uji**. Snapshot tidak mencatat kapan tiap hasil pertama kali diterbitkan.

## Protokol dan hasil model

Riwayat awal: 2020/21–2022/23. Bobot Elo–Poisson dipilih dari log loss validasi 2023/24 **hanya pada Premier League**; bobot Poisson terpilih **0,5**. Semua laga pada tanggal yang sama diprediksi sebelum hasil tanggal itu ditambahkan. Uji: Premier League dan Bundesliga 2024/25–2025/26; Eredivisie 2024/25 saja karena snapshot 2025/26 kehilangan satu skor. Bobot 0,5 dibekukan pada liga lain.

Uji Bundesliga awal mengungkap cacat rumus Elo lama: tim lemah bisa mendapat probabilitas mendekati nol. Rumus 1X2 diperbaiki agar peluang menang dibagi dari massa non-seri. Karena perubahan dibuat setelah melihat Bundesliga, hasil Bundesliga kini **eksplorasi**. Eredivisie 2024/25 digunakan sebagai uji tambahan sesudah perbaikan.

| Liga, N uji | Model | Akurasi 1X2 | Brier ↓ | Log loss ↓ |
| --- | --- | ---: | ---: | ---: |
| Premier League, 760 | Frekuensi dasar | 41,71% | 0,65569 | 1,08265 |
|  | Elo | **50,79%** | **0,60689** | **1,01474** |
|  | Poisson | 47,76% | 0,61799 | 1,02953 |
|  | Campuran | 49,08% | 0,60895 | 1,01667 |
| Bundesliga, 612 | Frekuensi dasar | 41,18% | 0,65596 | 1,08193 |
|  | Elo | 51,14% | 0,59758 | 1,00197 |
|  | Poisson | 50,49% | 0,59377 | 0,99780 |
|  | Campuran | **52,45%** | **0,59311** | **0,99623** |
| Eredivisie, 306 | Frekuensi dasar | 45,42% | 0,64601 | 1,06887 |
|  | Elo | 52,29% | 0,58216 | 0,97990 |
|  | Poisson | **54,90%** | **0,56522** | **0,95003** |
|  | Campuran | **54,90%** | 0,56954 | 0,95943 |

Selisih log loss Elo dikurangi campuran dan interval bootstrap berpasangan menurut tanggal (95%, 1.000 pengambilan ulang): Premier League **−0,00193 [−0,00899; 0,00492]**; Bundesliga **0,00574 [−0,00100; 0,01272]**; Eredivisie **0,02046 [0,00863; 0,03132]**. Hasil antar liga berbeda; satu campuran universal belum terbukti lebih baik di semua kompetisi. RPS, ECE, dan hasil per musim ada di `reports/backtest*.json`.

## Data taktik aktual

Sumber: [Metrica Sports sample-data](https://github.com/metrica-sports/sample-data), commit `e706dd506b360d69d9d123d5b8026e7294b13996`. Dua game anonim memuat **3.680 event** (Game 1: 1.745; Game 2: 1.935). Tracking 25 Hz dibaca dengan satu sampel setiap 25 frame. Arah serangan disimpulkan terpisah per tim dan babak dari tujuan tembakan. Tabel berikut menampilkan Game 1.

| Tim | Babak | Operan | Operan maju ≥10 m (proksi) | Tembakan | Pemulihan bola di area lawan |
| --- | ---: | ---: | ---: | ---: | ---: |
| Home | 1 | 187 | 32 | 11 | 24 |
| Home | 2 | 250 | 58 | 7 | 18 |
| Away | 1 | 182 | 39 | 2 | 17 |
| Away | 2 | 180 | 47 | 4 | 14 |

Tracking Game 1 menghasilkan 2.851 frame sampel babak pertama dan 2.950 babak kedua per tim. Bola terdeteksi pada 1.617 dan 1.819 frame tersebut. Game 2 juga berhasil diproses, dengan 2.718 dan 2.929 frame sampel per babak. Detail ada di `reports/tactics.json` dan `reports/tactics_game2.json`. Operan maju dan rentang posisi adalah **proksi deskriptif**, bukan bukti pressing, xT, pitch control, atau perubahan formasi. Sampel tidak mengidentifikasi klub dan belum divalidasi terhadap hasil pertandingan nyata yang bernama.

Sumber tambahan: [StatsBomb open-data](https://github.com/statsbomb/open-data), commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`, pertandingan Argentina–Prancis, 18 Desember 2022. Pengolah membaca **4.407 event**, mencocokkan 11 pemain awal tiap tim antara event `Starting XI` dan berkas lineup, serta **mengecualikan 8 tembakan adu penalti** dari statistik pertandingan 3–3. Argentina tercatat 20 tembakan dan xG 2,7583 (1,9748 tanpa penalti); Prancis 10 tembakan dan xG 2,2726 (0,7056 tanpa penalti). Ini data setelah laga, bukan bukti lineup tersedia sebelum kick-off. Ringkasan ada di `reports/statsbomb.json`.

## Kondisi skuad dan batasan

`bola.squad` sekarang menolak timestamp tanpa zona waktu, mengeluarkan bukti setelah waktu analisis, serta menandai lineup resmi kurang dari 11 pemain dan konflik status. Tesnya memakai **data sintetis**. Sembilan kandidat pertandingan pengguna diperiksa oleh `bola.fixtures`: dua telah melewati waktu mulai yang dilaporkan pada 14 Oktober 2026 pukul 23.47 WIB, tujuh belum. Jadwal, status aktual, dan URL sumber belum terverifikasi, sehingga belum ada pertandingan target yang layak disebut siap untuk analisis pra-laga. Kondisi skuad pertandingan nyata **belum tervalidasi**.

Belum ada odds historis bertimestamp, xG lintas musim, berita skuad lengkap, atau video. Nilai taruhan dan dampak pemain absen belum diukur. Target 95% adalah tujuan kelengkapan proses; belum ada bukti bahwa setiap bagian sudah mencapainya atau bahwa prediksi dapat akurat 95%.
