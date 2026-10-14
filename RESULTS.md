# Hasil audit dan pengujian Bola

Kode dan perintah tersedia di [README.md](README.md). Hasil probabilitas 1X2 di bawah berbasis **skor akhir historis**; audit StatsBomb memakai event pertandingan setelah laga. Ini bukan laporan taruhan atau analisis Feyenoord–Como. Sumber skor: [OpenFootball football.json](https://github.com/openfootball/football.json), commit `e6744429ee395bc86f247348c6184bb08d4eb361`.

## Audit StatsBomb seluruh Piala Dunia 2022

Pada 64 pertandingan, pemeriksa membaca 234.637 event dan mencocokkan 128 starting XI dengan dua struktur data sumber. Ada 1.453 tembakan sebelum adu penalti, 169 gol dari event tembakan, total xG 155,8987 termasuk penalti dan 137,8782 tanpa penalti. Sebanyak 41 tembakan adu penalti dikecualikan. Pemeriksaan deskriptif kalibrasi xG tingkat tembakan menghasilkan Brier 0,0781, log loss 0,2715, dan ECE 10 bin 0,0131; Brier prediktor konstan dengan frekuensi gol sampel ini 0,1028. Hasil ini berasal dari satu turnamen; riwayat pelatihan model xG StatsBomb tidak diketahui di sini, sehingga bukan validasi holdout independen. Rincian ada di `reports/worldcup.json` setelah skrip dijalankan.

Rincian menurut label asal penguasaan bola StatsBomb, setelah memisahkan penalti: `From Corner` **223 tembakan, 17 gol, 22,7609 xG**; `From Free Kick` **285 tembakan, 29 gol, 23,1375 xG**; `Regular Play` **446 tembakan, 51 gol, 43,5295 xG**. Label ini mencakup peluang dalam rangkaian penguasaan bola setelah restart, bukan hanya tendangan langsung. Angka tersebut memperluas pemeriksaan bola mati, tetapi belum menyediakan post-shot xG untuk menilai keterampilan penjaga gawang atau rekonsiliasi antarprovider.

### Pemeriksaan xG antarturnamen 2018–2022

Tambahan 64 pertandingan Piala Dunia putra 2018 dari commit StatsBomb yang sama menghasilkan **1.667 tembakan** sebelum adu penalti, 157 gol, Brier xG 0,0660, dan ECE 10 bin 0,0140. Pada 2022 terdapat 1.453 tembakan, 169 gol, dan Brier xG 0,0781. Frekuensi gol 2018 sebesar 0,094181 dipakai sebagai pembanding konstan pada data 2022: selisih Brier xG dikurangi pembanding **−0,025204**, interval bootstrap menurut pertandingan 95% **[−0,033783; −0,017188]**. Tanpa penalti, selisihnya **−0,019374 [−0,026145; −0,012936]**. Artinya xG membedakan tembakan lebih baik daripada satu frekuensi konstan pada sampel 2022 ini. Kedua sampel berasal dari Piala Dunia dan riwayat pelatihan xG StatsBomb tidak diketahui, sehingga ini belum merupakan validasi independen lintas kompetisi atau bukti kecocokan untuk klub UEFA. Berkas sumber 2018 diperiksa dengan checksum tetap; rincian ada di `reports/xg_transfer.json`.

### Pemeriksaan xG pada musim klub penuh

Seluruh **380 laga Premier League 2015/16** dari StatsBomb yang sama memuat **9.908 tembakan** sebelum adu penalti, 988 gol, Brier xG 0,0712, dan ECE 10 bin 0,0034. Frekuensi gol dari 190 laga hingga 31 Desember 2015 dibekukan sebagai pembanding konstan untuk 190 laga mulai 1 Januari 2016. Pada **5.011 tembakan** di separuh musim kedua, selisih Brier xG dikurangi pembanding adalah **−0,017389**, interval bootstrap menurut pertandingan 95% **[−0,020854; −0,013988]**. Tanpa penalti, selisihnya **−0,013355 [−0,016519; −0,010529]**. Ini menambah sampel klub yang lengkap, tetapi tetap satu musim lama dan satu penyedia; riwayat pelatihan model xG StatsBomb tidak tersedia. Total tiga sampel kini **508 laga dan 13.028 tembakan**. Semua berkas klub dicocokkan dengan checksum tetap; detail di `reports/xg_transfer.json`.

## Pembanding odds historis

Untuk **760** laga Premier League 2024/25–2025/26, hasil, tanggal, dan pasangan tim OpenFootball cocok dengan CSV Football-Data. Odds rata-rata penutupan yang dinormalisasi menghasilkan akurasi 1X2 **52,50%** dan log loss **0,98925**; Elo berbasis skor menghasilkan **50,79%** dan **1,01474**. Selisih log loss Elo dikurangi pasar adalah **0,02549**, interval bootstrap berpasangan menurut tanggal 95% **[0,01144; 0,03863]**. Odds pembukaan menghasilkan log loss **0,99290**. Pasar lebih baik pada kedua musim uji: log loss pasar/Elo **0,96673/0,99770** pada 2024/25 dan **1,01177/1,03177** pada 2025/26. CSV tidak memberi waktu publikasi tiap harga, jadi pembanding penutupan tidak membuktikan peluang transaksi yang bisa diambil sebelum laga. Rincian ada di `reports/odds_benchmark.json`.

Pencocokan ketat yang sama juga berhasil untuk **612/612** laga Bundesliga dan **306/306** laga Eredivisie yang masuk uji. Totalnya **1.678/1.678** baris uji model memiliki pasangan odds dengan tanggal dan skor final identik.

| Liga | N | Log loss pasar pembukaan | Log loss pasar penutupan | Log loss Elo | Log loss campuran |
| --- | ---: | ---: | ---: | ---: | ---: |
| Premier League | 760 | 0,99290 | **0,98925** | 1,01474 | 1,01667 |
| Bundesliga | 612 | 0,97164 | **0,96901** | 1,00197 | 0,99623 |
| Eredivisie | 306 | 0,94788 | **0,93848** | 0,97990 | 0,95943 |

Pada Bundesliga, selisih log loss campuran dikurangi pasar penutupan **0,02722**, interval bootstrap berpasangan menurut tanggal 95% **[0,01350; 0,04070]**; pada Eredivisie **0,02096 [0,00265; 0,04080]**. Selisih positif berarti pasar lebih baik pada sampel ini. Hasil Bundesliga tetap eksplorasi karena modelnya diperbaiki setelah hasil liga itu dilihat. Ketiadaan timestamp tiap harga juga berlaku pada dua liga tambahan; angka tersebut tidak menguji keputusan taruhan yang dapat dibuat saat itu. Detail di `reports/odds_bundesliga.json` dan `reports/odds_eredivisie.json`.

## Verifikasi jadwal UEFA 14–15 Oktober 2026 WIB

Sitemap dan halaman pertandingan UEFA mengonfirmasi **sembilan** pasangan laga serta jam yang dilaporkan pengguna. Saat diambil sekitar **15 Oktober 2026 pukul 00.01 WIB**, Feyenoord–Como dan LASK–Liverpool berstatus `Live`, sedangkan tujuh laga pukul 02.00 WIB berstatus `Upcoming`. UEFA menandai **kesembilannya sebagai MD2**; empat laga yang dilaporkan sebagai MD3 ternyata MD2. “Madrid” merujuk **Real Madrid**, “VfB” merujuk **Stuttgart**, dan “PSG” ditampilkan UEFA sebagai **Paris**. URL, waktu pengambilan, dan checksum HTML ada di `reports/uefa_fixtures.json`.

| Laga menurut UEFA | Jadwal WIB | Status saat diambil |
| --- | --- | --- |
| [Feyenoord–Como](https://www.uefa.com/uefachampionsleague/match/2049584--feyenoord-vs-como/) | 14 Okt 23.45 | Live |
| [LASK–Liverpool](https://www.uefa.com/uefachampionsleague/match/2049588--lask-vs-liverpool/) | 14 Okt 23.45 | Live |
| [Shakhtar–AEK Athens](https://www.uefa.com/uefachampionsleague/match/2049586--shakhtar-vs-aek-athens/) | 15 Okt 02.00 | Upcoming |
| [Real Betis–Porto](https://www.uefa.com/uefachampionsleague/match/2049583--real-betis-vs-porto/) | 15 Okt 02.00 | Upcoming |
| [Roma–Real Madrid](https://www.uefa.com/uefachampionsleague/match/2049581--roma-vs-real-madrid/) | 15 Okt 02.00 | Upcoming |
| [S. Bratislava–Stuttgart](https://www.uefa.com/uefachampionsleague/match/2049587--s-bratislava-vs-stuttgart/) | 15 Okt 02.00 | Upcoming |
| [Aston Villa–Fenerbahçe](https://www.uefa.com/uefachampionsleague/match/2049582--aston-villa-vs-fenerbahce/) | 15 Okt 02.00 | Upcoming |
| [Man City–Paris](https://www.uefa.com/uefachampionsleague/match/2049580--man-city-vs-paris/) | 15 Okt 02.00 | Upcoming |
| [Bodø/Glimt–B. Dortmund](https://www.uefa.com/uefachampionsleague/match/2049585--bodo-glimt-vs-b-dortmund/) | 15 Okt 02.00 | Upcoming |

Halaman daftar skuad UEFA yang diambil sekitar **00.02 WIB** menampilkan badge `Injured` untuk **Irakli Azarov** (Shakhtar) dan **Thomas Strakosha** (AEK Athens), serta `Doubtful` untuk **Marlon Santos** (Shakhtar) dan **Barnabás Varga** (AEK Athens). Ini adalah label pada daftar skuad terdaftar, bukan starting XI atau konfirmasi bahwa pemain tidak tersedia pada laga tersebut. Semua 14 tim dalam tujuh laga mendatang diperiksa; rincian di `reports/uefa_squads.json`.

Endpoint lineup resmi yang digunakan halaman UEFA, `https://match.uefa.com/v5/matches/{id}/lineups`, diperiksa sekitar **00.35 WIB**. Dua laga yang sudah `Live` berstatus `TACTICAL_AVAILABLE` dan masing-masing memiliki 11 pemain awal per tim. Ketujuh laga pukul 02.00 WIB masih berstatus `NOT_AVAILABLE`, tanpa daftar pemain awal. Respons API tidak menyertakan waktu pengumuman asli; dua lineup yang baru diambil setelah kickoff **tidak diperlakukan sebagai bukti prapertandingan**. Identitas tim, kickoff, jumlah pemain, waktu pengambilan, dan checksum respons ada di `reports/uefa_lineups.json`.

**Pembaruan pukul 00.51 WIB:** ketujuh laga pukul 02.00 sudah memiliki 11 starter resmi per tim di API UEFA, diamati sebelum kickoff. Pemeriksaan silang terhadap 32 pemain yang diberi badge pada daftar skuad menemukan **25 tidak tercantum dalam daftar hari pertandingan, 6 di bangku cadangan, dan 1 starter**. Contoh konflik: **Jeff Chabot** (Stuttgart) berlabel `Doubtful` tetapi starter, sedangkan **Luca Jaquez** (Stuttgart) berlabel `Injured` tetapi berada di bangku cadangan. Keduanya menunjukkan bahwa badge daftar skuad bukan keputusan final hari pertandingan; alasan medis atau pilihan pelatih tidak dapat disimpulkan dari perbandingan ini saja. Snapshot respons dan peran pemain tercatat di `reports/uefa_lineups.json` dan `reports/prematch_dossier.json` setelah perintah penyegaran dijalankan.

Snapshot API yang diarsipkan membatasi waktu perubahan status, misalnya Real Betis–Porto masih `NOT_AVAILABLE` saat diamati **00.39.44 WIB**, lalu `TACTICAL_AVAILABLE` saat diamati **00.50.50 WIB**. Ini adalah rentang *pertama kali teramati* di lingkungan ini, bukan waktu pengumuman yang diterbitkan UEFA.

Perbandingan ID starter resmi fase liga MD1 dan MD2 untuk ketujuh laga mendatang memberikan jumlah **starter baru** berikut. Respons MD1 dan checksum disimpan terpisah di `.cache/uefa/rotation/`.

| Laga | Tuan rumah | Tamu |
| --- | ---: | ---: |
| Shakhtar–AEK Athens | 2 | 1 |
| Real Betis–Porto | 5 | 3 |
| Roma–Real Madrid | 3 | 3 |
| S. Bratislava–Stuttgart | 1 | 3 |
| Aston Villa–Fenerbahçe | 4 | 4 |
| Man City–Paris | 3 | 3 |
| Bodø/Glimt–B. Dortmund | 3 | 4 |

Ini bukan ukuran kelelahan atau bukti penyebab rotasi. Laga domestik dan piala di antara kedua matchday tidak tercakup; jumlah pemain baru dari bangku cadangan MD1 dan yang tidak terdaftar pada MD1 tersedia di `reports/uefa_rotation.json`.

## Form liga domestik sebelum laga 15 Oktober 2026

Snapshot Football-Data yang diambil sekitar **00.14 WIB** memuat hasil liga hingga 11–12 Oktober. Pemeriksa memakai cutoff eksklusif 15 Oktober WIB dan menghitung jendela 5, 10, serta 20 laga untuk **12 dari 18 tim** dalam daftar pengguna. Hasil lima laga domestik terakhir untuk tiga pasangan laga pukul 02.00 WIB yang datanya lengkap:

| Tim | W–D–L | Gol per laga | Kebobolan per laga |
| --- | ---: | ---: | ---: |
| Real Betis | 4–1–0 | 2,0 | 0,8 |
| Porto | 5–0–0 | 2,8 | 0,8 |
| Roma | 3–2–0 | 2,0 | 0,6 |
| Real Madrid | 3–0–2 | 1,8 | 1,2 |
| Man City | 5–0–0 | 2,8 | 0,8 |
| Paris SG | 3–1–1 | 1,8 | 1,2 |

Angka ini **deskriptif dan berasal dari liga yang berbeda**. Tidak ada xG, laga UEFA, atau penyesuaian kualitas antarliga dalam tabel tersebut. Surplus terhadap Elo lawan serta data tiap laga ada di `reports/current_form.json`; enam tim lain tidak tercakup oleh tujuh liga sumber. Form ini belum menghasilkan probabilitas pertandingan.

`bola.dossier` menggabungkan bukti pada **15 Oktober pukul 00.51 WIB**. Tujuh laga masih sebelum kickoff resmi pada waktu itu. Daftar skuad dan starting XI resmi UEFA tersedia untuk kedua tim pada semua tujuh laga; form domestik kedua tim hanya tersedia pada tiga laga berikut.

| Laga pukul 02.00 WIB | Form kedua tim | Skuad terdaftar UEFA kedua tim | Starting XI resmi | Odds kini bertimestamp | Model antarliga tervalidasi |
| --- | --- | --- | --- | --- | --- |
| Shakhtar–AEK Athens | Tidak | Ya | Ya | Belum | Belum |
| Real Betis–Porto | Ya | Ya | Ya | Belum | Belum |
| Roma–Real Madrid | Ya | Ya | Ya | Belum | Belum |
| S. Bratislava–Stuttgart | Tidak | Ya | Ya | Belum | Belum |
| Aston Villa–Fenerbahçe | Tidak | Ya | Ya | Belum | Belum |
| Man City–Paris | Ya | Ya | Ya | Belum | Belum |
| Bodø/Glimt–B. Dortmund | Tidak | Ya | Ya | Belum | Belum |

Semua tujuh **belum siap untuk dua prediksi yang memenuhi protokol**. Gerbang snapshot UEFA menjadi kedaluwarsa setelah 30 menit dan harus diperiksa kembali; status `Upcoming` di tabel adalah status saat snapshot, bukan feed langsung. Rincian per laga ada di `reports/prematch_dossier.json` setelah perintah di README dijalankan.

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

### Uji silang antarliga pada fase liga UEFA

API resmi UEFA menyediakan **144 laga fase liga 2024/25**, **144 laga 2025/26**, dan **18 laga MD1 2026/27**. Respons per tanggal, checksum, serta waktu pengambilan disimpan di `.cache/uefa_history/`. Model hasil skor yang sama memakai ID klub UEFA, memperbarui rating hanya setelah laga pada tanggal UTC tersebut diprediksi. Musim pertama membentuk riwayat; 2025/26 dan MD1 2026/27 diuji berurutan. Bobot campuran 0,5 dibekukan dari validasi Premier League.

| Periode uji | N | Log loss frekuensi dasar | Elo | Poisson | Campuran |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2025/26 | 144 | 1,0258 | 0,9909 | 0,9953 | **0,9870** |
| MD1 2026/27 | 18 | 0,9234 | 0,8509 | **0,8164** | 0,8301 |

Selisih log loss campuran dikurangi frekuensi dasar pada 2025/26 adalah **−0,0388**, interval bootstrap menurut tanggal 95% **[−0,0584; −0,0186]**. Pada 18 laga MD1 2026/27 selisihnya **−0,0933 [−0,1487; 0,0173]**; interval itu melintasi nol. Ini adalah bukti awal model skor bekerja lebih baik dari frekuensi dasar pada satu musim UEFA, **bukan** kalibrasi antarliga yang stabil atau pembanding odds UEFA. Tidak ada xG, skuad, atau odds dalam model ini, dan snapshot historis tidak mencatat tanggal pertama hasil dipublikasikan. Detail di `reports/uefa_backtest.json`.

Cakupan riwayat klub juga tidak seimbang untuk tujuh laga berikutnya: **Man City dan Paris masing-masing 17** laga dalam 306 hasil sumber, sedangkan **AEK Athens, Real Betis, Porto, Roma, dan Fenerbahçe masing-masing hanya 1**. Peluang yang dikeluarkan model untuk klub dengan satu laga akan sangat bergantung pada prior. Karena itu hasil uji UEFA ini belum mengubah gerbang `validated_cross_league_probability_model` pada dossier menjadi lulus.

### Arsip prediksi prospektif 15 Oktober 2026

Pada **15 Oktober pukul 01.02 WIB**, sebelum kickoff pukul 02.00 WIB, `bola.uefa_forecast` membekukan tujuh distribusi 1X2 dalam `prospective/uefa_2026-10-14T18-02-34.009581+00-00.json`. Kode model telah dicatat sebagai commit `5a4544ac984542514b7409f4be5d44532ae1a80f`. Arsip menyimpan waktu pembuatan, ID dan waktu laga, checksum hasil historis dan respons jadwal UEFA, serta jumlah penampilan UEFA tiap klub dalam sampel. Dua laga yang sudah Live dikecualikan. Model hanya memakai hasil akhir yang tersedia sebelum waktu pengambilan, tanpa odds, xG, lineup, atau berita pemain. Ini **baseline eksploratif untuk dinilai setelah hasil diketahui**, bukan dua rekomendasi taruhan atau bukti kalibrasi 95%.

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

### Uji lokasi pemulihan dan tembakan cepat

Pada **64 laga Piala Dunia 2022**, pemulihan berhasil pertama yang ditandai StatsBomb dalam setiap penguasaan bola dikelompokkan menurut paruh lapangan. Hanya tembakan tim yang sama, dalam penguasaan dan babak yang sama, serta setelah event pemulihan yang dihitung. Berkas event diverifikasi dengan SHA-256.

| Jendela setelah pemulihan | Area sendiri: penguasaan berakhir dengan tembakan | Area lawan: penguasaan berakhir dengan tembakan |
| --- | ---: | ---: |
| 10 detik | 30/2.809 = 1,07% | 340/1.626 = 20,91% |
| 15 detik | 57/2.809 = 2,03% | 374/1.626 = 23,00% |
| 30 detik | 117/2.809 = 4,17% | 409/1.626 = 25,15% |

Selisih proporsi pada jendela 15 detik adalah **20,97 poin persentase**, interval bootstrap menurut laga 95% **[18,71; 22,98] poin**. Ini menunjukkan lokasi lapangan sangat berkaitan dengan peluang tembakan cepat dalam data tersebut. Tag `Ball Recovery` tidak mencakup semua pergantian bola, dan lokasi, skor, serta situasi pertandingan dapat menjelaskan sebagian hubungan. Angka ini **bukan** ukuran keberhasilan pressing, efek sebab akibat, atau bukti bahwa fitur ini meningkatkan prediksi klub UEFA. Ringkasan mesin ada di `reports/recovery.json`.

### Pemeriksaan event taktik dan rotasi pada musim klub

Pada **380 laga Premier League 2015/16**, pendekatan pemulihan yang sama mencatat **19.932** penguasaan dengan pemulihan pertama di paruh sendiri dan **10.898** di paruh lawan. Tembakan tim yang sama dalam 15 detik terjadi pada **486/19.932 = 2,44%** versus **2.402/10.898 = 22,04%**. Selisihnya **19,60 poin persentase**, interval bootstrap menurut laga 95% **[18,77; 20,40] poin**. Hasil ini menunjukkan pola lokasi dan tembakan cepat juga ada pada sampel klub; ia tetap belum menandai semua pressing, mengendalikan situasi skor, atau menguji peningkatan prediksi.

Dari event awal pertandingan, **760 starting XI** cocok dengan dua ID tim pada setiap laga. Ada **740 penampilan tim** dengan XI laga sebelumnya untuk menghitung jumlah starter yang berubah. Dibanding baseline Elo berbasis skor sebelum tiap laga, rata-rata selisih poin aktual dikurangi ekspektasi adalah **+0,016** untuk 0–2 starter berubah (471 penampilan), **−0,127** untuk 3–4 (220), dan **+0,199** untuk 5–11 (49). Pola ini tidak monoton; rotasi besar tidak otomatis berarti hasil lebih buruk. Data tidak menyatakan penyebab perubahan XI, dan hubungan tersebut dipengaruhi lawan, jadwal, serta pilihan pelatih. Ini **bukan** estimasi dampak cedera atau rekomendasi taktik. Rincian dan checksum ada di `reports/club_audit.json`.

### Uji prospektif semu fitur pemulihan

Untuk setiap laga, rata-rata pemulihan bertanda di paruh lawan dihitung **hanya dari laga sebelumnya**, setelah kedua tim memiliki setidaknya lima laga riwayat. Koefisien penyesuaian peluang Elo dipilih pada **140 laga** sebelum 1 Januari 2016 dari grid yang telah ditetapkan; koefisien terpilih `1,0` diuji pada **190 laga** mulai tanggal itu. Log loss Elo murni **1,02748**, sedangkan Elo dengan fitur pemulihan **1,03039**; selisih **+0,00291**, interval bootstrap menurut tanggal laga 95% **[−0,01876; +0,02656]**. Brier juga naik dari **0,61558** menjadi **0,62003**. Tidak ada bukti fitur ini meningkatkan prediksi 1X2 pada uji tersebut. Feed StatsBomb historis diterbitkan setelah laga, sehingga uji kronologis dalam kode belum membuktikan data tersedia tepat waktu pada 2015/16. Detail ada di `reports/tactic_predict.json`.

## Kondisi skuad dan batasan

`bola.squad` sekarang menolak timestamp tanpa zona waktu, mengeluarkan bukti setelah waktu analisis, serta menandai lineup resmi kurang dari 11 pemain dan konflik status. Tesnya memakai **data sintetis**. Sembilan kandidat pertandingan pengguna diperiksa oleh `bola.fixtures`: dua telah melewati waktu mulai yang dilaporkan pada 14 Oktober 2026 pukul 23.47 WIB, tujuh belum. Pemeriksaan UEFA berikutnya memverifikasi kesembilan jadwal dan mendapati empat label matchday salah. Starting XI resmi untuk tujuh laga yang belum dimulai teramati sebelum kickoff dan badge pemain direkonsiliasi dengan peran matchday. Waktu publikasi tiap badge dan dampak absensi terhadap peluang belum tervalidasi.

Belum ada odds historis dengan timestamp tiap kutipan, xG lintas musim/kompetisi yang direkonsiliasi, berita skuad lengkap, atau video. Nilai taruhan dan dampak pemain absen belum diukur. Target 95% adalah tujuan kelengkapan proses; belum ada bukti bahwa setiap bagian sudah mencapainya atau bahwa prediksi dapat akurat 95%.
