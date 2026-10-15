# Hasil audit dan pengujian Bola

Kode dan perintah tersedia di [README.md](README.md). Hasil probabilitas 1X2 di bawah berbasis **skor akhir historis**; audit StatsBomb memakai event pertandingan setelah laga. Ini bukan laporan taruhan atau analisis Feyenoord–Como. Sumber skor: [OpenFootball football.json](https://github.com/openfootball/football.json), commit `e6744429ee395bc86f247348c6184bb08d4eb361`.

## Audit StatsBomb seluruh Piala Dunia 2022

Pada 64 pertandingan, pemeriksa membaca 234.637 event dan mencocokkan 128 starting XI dengan dua struktur data sumber. Ada 1.453 tembakan sebelum adu penalti, 169 gol dari event tembakan, total xG 155,8987 termasuk penalti dan 137,8782 tanpa penalti. Sebanyak 41 tembakan adu penalti dikecualikan. Pemeriksaan deskriptif kalibrasi xG tingkat tembakan menghasilkan Brier 0,0781, log loss 0,2715, dan ECE 10 bin 0,0131; Brier prediktor konstan dengan frekuensi gol sampel ini 0,1028. Hasil ini berasal dari satu turnamen; riwayat pelatihan model xG StatsBomb tidak diketahui di sini, sehingga bukan validasi holdout independen. Rincian ada di `reports/worldcup.json` setelah skrip dijalankan.

Rincian menurut label asal penguasaan bola StatsBomb, setelah memisahkan penalti: `From Corner` **223 tembakan, 17 gol, 22,7609 xG**; `From Free Kick` **285 tembakan, 29 gol, 23,1375 xG**; `Regular Play` **446 tembakan, 51 gol, 43,5295 xG**. Label ini mencakup peluang dalam rangkaian penguasaan bola setelah restart, bukan hanya tendangan langsung. Angka tersebut memperluas pemeriksaan bola mati, tetapi belum menyediakan post-shot xG untuk menilai keterampilan penjaga gawang atau rekonsiliasi antarprovider.

### Pemeriksaan xG antarturnamen 2018–2022

Tambahan 64 pertandingan Piala Dunia putra 2018 dari commit StatsBomb yang sama menghasilkan **1.667 tembakan** sebelum adu penalti, 157 gol, Brier xG 0,0660, dan ECE 10 bin 0,0140. Pada 2022 terdapat 1.453 tembakan, 169 gol, dan Brier xG 0,0781. Frekuensi gol 2018 sebesar 0,094181 dipakai sebagai pembanding konstan pada data 2022: selisih Brier xG dikurangi pembanding **−0,025204**, interval bootstrap menurut pertandingan 95% **[−0,033783; −0,017188]**. Tanpa penalti, selisihnya **−0,019374 [−0,026145; −0,012936]**. Artinya xG membedakan tembakan lebih baik daripada satu frekuensi konstan pada sampel 2022 ini. Kedua sampel berasal dari Piala Dunia dan riwayat pelatihan xG StatsBomb tidak diketahui, sehingga ini belum merupakan validasi independen lintas kompetisi atau bukti kecocokan untuk klub UEFA. Berkas sumber 2018 diperiksa dengan checksum tetap; rincian ada di `reports/xg_transfer.json`.

### Pemeriksaan xG pada musim klub penuh

Seluruh **380 laga Premier League 2015/16** dari StatsBomb yang sama memuat **9.908 tembakan** sebelum adu penalti, 988 gol, Brier xG 0,0712, dan ECE 10 bin 0,0034. Frekuensi gol dari 190 laga hingga 31 Desember 2015 dibekukan sebagai pembanding konstan untuk 190 laga mulai 1 Januari 2016. Pada **5.011 tembakan** di separuh musim kedua, selisih Brier xG dikurangi pembanding adalah **−0,017389**, interval bootstrap menurut pertandingan 95% **[−0,020854; −0,013988]**. Tanpa penalti, selisihnya **−0,013355 [−0,016519; −0,010529]**. Ini menambah sampel klub yang lengkap, tetapi tetap satu musim lama dan satu penyedia; riwayat pelatihan model xG StatsBomb tidak tersedia. Total tiga sampel kini **508 laga dan 13.028 tembakan**. Semua berkas klub dicocokkan dengan checksum tetap; detail di `reports/xg_transfer.json`.

### Pencocokan xG dua penyedia pada liga dan musim yang sama

Cermin komunitas Understat pada commit `87960c218d873b63daabdd851e93adbecab77faa` dan SHA-256 `cdde2434aa027d4cbb8e9ead6510143d219a3df3575daa0f14a18937fece8f4e` memuat seluruh **380 laga Premier League 2015/16**. Semua pasangan tuan rumah/tamu dan skor akhir cocok dengan metadata StatsBomb; **13 tanggal** berbeda tepat satu hari, sehingga tanggal sumber tidak dipakai sebagai satu-satunya kunci. Setelah 38 baris `OwnGoal` Understat dengan xG nol dikecualikan dari hitungan tembakan, StatsBomb memiliki **9.908 tembakan, 988 gol dari event tembakan, 971,38 xG**; Understat **9.781 tembakan, 988 gol dari event tembakan, 992,59 xG**. Ada **dua laga** dengan jumlah event gol yang berbeda walau skor akhir cocok.

Untuk **760 penampilan tim**, korelasi Pearson xG pertandingan kedua penyedia **0,9089**, selisih absolut rata-rata **0,2442 gol**, dan rata-rata StatsBomb dikurangi Understat **−0,0279** dengan interval bootstrap berpasangan menurut laga 95% **[−0,0521; −0,0063]**. Hanya **512 dari 760** penampilan tim memiliki jumlah tembakan yang sama. Karena definisi tembakan dan xG berbeda, ini adalah rekonsiliasi pada tingkat pertandingan, bukan validasi bahwa satu penyedia lebih benar atau penyandingan satu per satu setiap tembakan. Data historis cermin Understat tidak memberi waktu publikasi tiap baris atau riwayat pelatihan model. Laporan per laga ada di `evidence/xg_provider_compare_epl_2015.json`.

Audit kolom tembakan klub menemukan **nol kolom post-shot xG** pada 9.908 tembakan. Dari 2.209 tembakan berlabel `Saved`, **342** memiliki koordinat akhir lateral di luar interval gawang nominal 36–44 pada skala StatsBomb; dari 988 gol, **1** demikian. Penjaga gawang lawan tampak unik pada freeze frame **3.112 dari 3.197** tembakan `Saved` atau `Goal`, tetapi koordinat akhir tersebut tidak dapat langsung diperlakukan sebagai lokasi lintasan bola saat melintasi garis gawang. Oleh karena itu, penghitungan post-shot xG atau *goals prevented* dari koordinat ini tanpa definisi dan validasi tambahan berisiko menyesatkan. Rincian dan checksum ada di `reports/shot_endpoints.json`.

Pada 3.112 tembakan yang memiliki tepat satu kiper lawan di freeze frame, audit menemukan **2.198 Saved** dan **914 Goal** untuk **47 kiper**. Contoh dengan sampel terbesar: Heurelho Gomes 125/168 penyelamatan, rasio **74,4%** dengan interval Wilson 95% **[67,3%; 80,4%]**. Delapan puluh lima tembakan lain dikecualikan dari rasio per kiper karena identitas kiper tidak unik dalam freeze frame. Rasio ini ukuran deskriptif historis, bukan ukuran kualitas kiper setelah mengendalikan lokasi sepakan, kecepatan bola, atau defleksi. Laporan lengkap yang dapat diperiksa ada di `evidence/shot_endpoints_epl_2015.json`.

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

Snapshot awal Football-Data yang diambil sekitar **00.14 WIB** memuat hasil liga hingga 11–12 Oktober. Sumber tambahan Turki, Yunani, Austria, dan Norwegia kemudian diverifikasi sebelum kickoff. Pemeriksa memakai cutoff eksklusif 15 Oktober WIB dan menghitung jendela 5, 10, serta 20 laga untuk **16 dari 18 tim** dalam daftar pengguna. Hasil lima laga domestik terakhir untuk tim yang ditambahkan dan tiga pasangan awal:

| Tim | W–D–L | Gol per laga | Kebobolan per laga |
| --- | ---: | ---: | ---: |
| Real Betis | 4–1–0 | 2,0 | 0,8 |
| Porto | 5–0–0 | 2,8 | 0,8 |
| Roma | 3–2–0 | 2,0 | 0,6 |
| Real Madrid | 3–0–2 | 1,8 | 1,2 |
| Man City | 5–0–0 | 2,8 | 0,8 |
| Paris SG | 3–1–1 | 1,8 | 1,2 |
| AEK Athens | 3–2–0 | 2,4 | 0,6 |
| Fenerbahçe | 3–1–1 | 2,8 | 0,4 |
| LASK | 2–1–2 | 2,0 | 1,6 |
| Bodø/Glimt | 4–0–1 | 2,6 | 1,6 |

Angka ini **deskriptif dan berasal dari liga yang berbeda**. Tidak ada laga UEFA atau penyesuaian kualitas antarliga dalam tabel tersebut. CSV Turki dan Yunani memuat xG pada sebagian laga terkini, tetapi identitas model dan riwayat pelatihannya belum diketahui; kolom tersebut belum direkonsiliasi dengan StatsBomb. Surplus terhadap Elo lawan serta data tiap laga ada di `reports/current_form.json` dan `reports/current_form_extra.json`. Shakhtar dan Slovan Bratislava belum tercakup dalam snapshot prapertandingan tersebut. Form ini belum menghasilkan probabilitas pertandingan.

Setelah kickoff, empat halaman liga FotMob/enet 2025/26–2026/27 dibekukan untuk mengisi dua tim tersisa. Semua hasil dengan tanggal WIB **15 Oktober atau sesudahnya** dikecualikan. Shakhtar memiliki **38** hasil liga sebelum cutoff; lima terakhir **4–0–1**, rata-rata gol **2,0** dan kebobolan **0,6**. Slovan Bratislava memiliki **41** hasil; lima terakhir **1–2–2**, gol **1,4** dan kebobolan **1,8**. Jendela 5/10/20 tersedia untuk keduanya, sehingga cakupan retrospektif menjadi **18 dari 18 tim**. Halaman sumber baru diambil setelah kickoff dan tidak membuktikan informasi tersebut sudah diterbitkan sebelum pertandingan; dua laga di dossier prapertandingan tetap berstatus form belum tersedia pada waktu snapshotnya. Rincian per laga serta checksum ada di `evidence/form_fotmob_2026-10-15.json`.

Sepuluh halaman laga liga, lima per tim, kemudian diperiksa terhadap ID pertandingan, skor akhir, kickoff, dan checksum. Semua **5/5** laga untuk masing-masing tim memiliki penguasaan bola, tembakan, tembakan tepat sasaran, dan corner berikut:

| Tim | Penguasaan bola | Tembakan | Tepat sasaran | Corner |
| --- | ---: | ---: | ---: | ---: |
| Shakhtar | 63,0% | 14,0 | 6,0 | 5,4 |
| Slovan Bratislava | 66,6% | 16,8 | 4,8 | 6,4 |

Slovan juga memiliki data peluang besar **3,0/laga**, akurasi operan **85,2%**, dan penyelamatan kiper **1,6/laga** pada 5/5 halaman; statistik tiap babak tersedia. Kelima halaman Shakhtar tidak memuat metrik tambahan itu atau xG, sehingga tidak ada angka pengganti yang dihitung. Penguasaan bola Slovan yang tinggi bersamaan dengan rekor **1–2–2** menunjukkan bahwa porsi bola saja tidak menjamin hasil pada sampel ini. Semua halaman diambil setelah kickoff; ringkasan ini audit retrospektif, bukan input yang terbukti tersedia sebelum laga. Rincian dan cakupan setiap metrik ada di `evidence/fotmob_recent_stats_2026-10-15.json`.

`bola.dossier` pertama kali menggabungkan bukti pada **15 Oktober pukul 00.51 WIB**. Pada penyegaran **01.33 WIB**, tujuh laga masih sebelum kickoff resmi; daftar skuad dan starting XI resmi UEFA tersedia untuk kedua tim pada semuanya. Form domestik kedua tim kini tersedia pada lima laga berikut.

| Laga pukul 02.00 WIB | Form kedua tim | Skuad terdaftar UEFA kedua tim | Starting XI resmi | Odds kini bertimestamp | Model antarliga tervalidasi |
| --- | --- | --- | --- | --- | --- |
| Shakhtar–AEK Athens | Tidak | Ya | Ya | Belum | Belum |
| Real Betis–Porto | Ya | Ya | Ya | Belum | Belum |
| Roma–Real Madrid | Ya | Ya | Ya | Belum | Belum |
| S. Bratislava–Stuttgart | Tidak | Ya | Ya | Belum | Belum |
| Aston Villa–Fenerbahçe | Ya | Ya | Ya | Belum | Belum |
| Man City–Paris | Ya | Ya | Ya | Belum | Belum |
| Bodø/Glimt–B. Dortmund | Ya | Ya | Ya | Belum | Belum |

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

Setelah tujuh laga selesai, respons hasil resmi UEFA diambil **15 Oktober pukul 14.58 WIB**, disimpan sebagai `prospective/uefa_results_2026-10-15T07-58-54Z.json` dengan SHA-256 `16589628bb55fb09a8f6a97d8c28293bd9ea0cda8acb0c25aa8b1817ab2e9d09`, lalu dicocokkan dengan arsip tanpa mengubah probabilitas. Model campuran memperoleh **5/7 pilihan hasil benar**, log loss **0,8281**, dan Brier **0,4907**; pembanding frekuensi dasar **4/7**, log loss **0,8458**, Brier **0,5235**. Elo murni juga 5/7 dengan log loss **0,8139**. Tujuh laga terlalu sedikit untuk menyimpulkan kalibrasi atau keunggulan stabil. Rincian setiap laga dan penilaian ada di `prospective/uefa_score_2026-10-15T07-58-07Z.json`.

### Arsip sembilan laga 20 Oktober 2026 UTC

Pada **15 Oktober pukul 16.09 WIB**, `bola.uefa_forecast_live` mengambil lima tanggal laga musim 2026/27 yang sudah selesai dari API UEFA serta sembilan jadwal tanggal target. Bersama 288 hasil dua musim terdahulu, model memakai **324 hasil**. Sembilan jadwal masih `UPCOMING` dan seluruh ramalan dibuat sebelum kickoff. Arsip ada di `prospective/uefa_2026-10-15T09-09-44.309038+00-00.json`. Pemeriksaan ulang SHA-256 delapan berkas sumber dan pemutaran kembali model mengembalikan sembilan distribusi yang sama. Ini meningkatkan keterulangan alur kerja; **belum ada hasil sembilan laga**, odds sahih, atau validasi kalibrasi baru. Klub seperti Fenerbahçe, Sabah, Roma, Porto, dan AEK Athens hanya memiliki dua penampilan UEFA dalam sampel; prior kekuatan klubnya lemah.

Riwayat kemudian diperluas ke semua fase Liga Champions 2022/23–2026/27 yang selesai sampai 14 Oktober: **1.114 pertandingan** resmi, terdiri dari kualifikasi, fase grup/liga, dan gugur. Evaluasi tetap hanya menilai periode fase liga yang ditentukan. Pada 144 laga 2025/26, log loss campuran **0,9803** dibanding baseline **1,0225**; selisih −0,0422 dengan interval bootstrap 95% [−0,0710; −0,0139]. Pada holdout 18 laga MD1 2026/27, campuran **0,8532** versus baseline **0,9441**. Pada 18 laga MD2 yang kemudian diperiksa, campuran **0,9016** versus **0,9451**. MD2 adalah holdout retrospektif setelah hasil selesai.

Audit bobot baru memilih kandidat bobot Elo **0,75** pada 144 laga fase liga 2024/25. Keunggulannya atas bobot lama 0,50 hanya **−0,000013 log loss**, dengan interval bootstrap berpasangan 95% **[−0,00753; +0,00698]**. Aturan penerapan mensyaratkan seluruh interval berada di bawah nol, sehingga kandidat ditolak dan bobot **0,50 dipertahankan**. Keputusan penolakan, grid lengkap, dan tiga periode terkunci tersimpan dalam `evidence/uefa_extended_backtest_2026-10-15.json`. Protokol ini mencegah pemilihan bobot 0,75 hanya karena terlihat lebih baik setelah MD2 diketahui.

Kalibrasi per kelas pada gabungan **180 laga** periode terkunci menghasilkan ECE satu-lawan-semua sebesar **0,0534 kandang, 0,0553 seri, dan 0,0312 tandang**. Koreksi frekuensi kelas kemudian dilatih pada 144 laga 2025/26 dan diuji pada 36 laga MD1–MD2. Log loss turun dari **0,87737 menjadi 0,85277** dan Brier dari **0,51378 menjadi 0,50077**, tetapi akurasi pilihan tertinggi turun dari 63,89% menjadi 61,11%. Selisih log loss **−0,02460** memiliki interval bootstrap 95% **[−0,04718; +0,00678]**. Karena interval melintasi nol, koreksi ditolak dan tidak diterapkan pada arsip target.

Arsip target terbaru `prospective/uefa_2026-10-15T15-53-23.675934+00-00.json` memakai seluruh **1.114 hasil**, mencatat bobot Elo/Poisson 0,50/0,50, dan dapat diputar ulang persis dari snapshot. Cakupan riwayat Fenerbahçe naik dari 2 menjadi 18 laga, Sabah 2 menjadi 10, AEK Athens 2 menjadi 8, dan Slovan Bratislava 10 menjadi 38. Roma tetap hanya memiliki 2 laga dalam rentang sumber, sehingga ketidakpastian klub tersebut masih besar. Arsip lama tidak ditimpa agar perubahan protokol tetap dapat diaudit.

Pada **15 Oktober pukul 16.11 WIB**, sembilan halaman pertandingan UEFA mencocokkan tim dan kickoff dengan arsip. Daftar pemain terdaftar berhasil dibaca untuk kedua tim pada **9/9 laga**. API lineup mengembalikan `NOT_AVAILABLE` pada **9/9**, sehingga **tidak ada XI resmi**. Halaman menampilkan badge pada beberapa pemain, tetapi itu tidak menetapkan cedera atau absensi spesifik laga. Snapshot berikut URL, waktu pengambilan, dan checksum ada di `evidence/uefa_target_squad_2026-10-15.json`.

Form domestik 5/10/20 pertandingan yang telah selesai sebelum 15 Oktober tersedia bagi **18 dari 18 tim** pada sembilan laga tersebut. Lima klub baru dipetakan ke nama Football-Data yang cocok: Barcelona, Villarreal, Napoli, PSV Eindhoven, dan Ath Madrid (`Atleti` di UEFA). Slovan Bratislava dan Bodø/Glimt memakai snapshot liga tambahan yang sudah diambil sebelum laga target. Pada **15 Oktober pukul 16.17 WIB**, halaman liga FotMob Czech dan Azerbaijan diambil sebelum kickoff mendatang; ID liga dan tim cocok, tanggal laga disaring, dan jendela tersedia bagi Slavia Praha (44 hasil sebelum cutoff) serta Sabah (39 hasil). Lima laga terakhir mereka masing-masing **5–0–0** dan **4–1–0**. Hasil kedua liga itu baru dicocokkan dengan halaman tim dari penyedia yang sama, belum dengan sumber liga independen. Tabel per tim, waktu pengambilan, dan ringkasan jendela ada di `evidence/uefa_target_form_2026-10-15.json`. Snapshot ini harus disegarkan sesudah pertandingan domestik berikutnya; form antarliga belum menjadi input model peluang.

Halaman tim FotMob kemudian dipakai sebagai pembanding kedua untuk sumber Football-Data. Pencocokan dibatasi pada liga utama, hasil sebelum cutoff, venue yang sama, skor yang sama, dan tanggal berselisih paling jauh satu hari untuk mengakomodasi tanggal lokal versus WIB. Seluruh **75/75 hasil** dari lima laga terakhir **15 tim** cocok. Slavia Praha, Sabah, dan Slovan Bratislava tidak dihitung independen karena sumber utama form mereka juga FotMob. Nama lawan dari kedua penyedia dipertahankan untuk audit tetapi tidak dipaksa sama secara teks. Rincian ada di `evidence/form_crosscheck_target_2026-10-15.json`.

Kalender lintas kompetisi pada 18 halaman tim juga diaudit. Target UEFA cocok menurut kickoff dan status kandang/tandang, dan kedua halaman tim menyepakati ID FotMob pada **9/9 pasangan**. Sebanyak **17 tim** dijadwalkan bermain sekali pada 17 Oktober sebelum target 20 Oktober; Porto tidak memiliki pertandingan di antaranya. Waktu istirahat terproyeksi berkisar dari **72,25 jam** untuk Roma hingga **144 jam** untuk Porto. Hitungan ini bersumber pada jadwal yang diamati 15 Oktober; penundaan, rotasi, menit pemain, dan perjalanan belum diketahui. Laporan lengkap ada di `evidence/schedule_load_target_2026-10-15.json`.

`bola.analyst_report` menyatukan arsip peluang, form, beban jadwal, dan snapshot UEFA tanpa mengubah peluang yang sudah dibekukan. Pada laporan terbaru 15 Oktober, form dan beban jadwal tersedia untuk **9/9 laga**, demikian pula skuad terdaftar; XI resmi dan odds bertimestamp masing-masing masih **0/9**. Bukti taktik terkini yang tervalidasi serta validasi keunggulan model terhadap pasar juga belum ada. Karena itu status keputusan adalah `no_selection` pada **9/9 laga**. Peluang dari riwayat 1.114 laga tetap disimpan untuk dinilai setelah pertandingan; laporan lengkap ada di `evidence/analyst_report_schedule_2026-10-15.json`.

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

Uji terpisah memakai selisih jumlah starter berubah kedua tim sebagai fitur prapertandingan pada baseline Elo. Koefisien dipilih dari **180 laga** sebelum 1 Januari 2016, kemudian diuji pada **190 laga** mulai tanggal itu. Bobot terpilih `0,5` menghasilkan log loss **1,03352** versus **1,02748** untuk Elo tanpa fitur; selisih **+0,00605**, interval bootstrap menurut tanggal laga 95% **[−0,01135; +0,02404]**. Brier juga naik dari **0,61558** menjadi **0,61967**. Perubahan XI **tidak terbukti memperbaiki prediksi** pada uji ini. Data event historis tidak membuktikan XI tersedia sebelum kickoff dan tidak menjelaskan penyebab perubahan pemain. Detail di `reports/rotation_predict.json`.

Uji kondisi skuad yang lebih spesifik memberi setiap pemain bobot berdasarkan porsi start dalam lima laga terdahulu, kemudian menjumlah bobot pemain reguler yang hilang dari XI saat ini. Koefisien dipilih pada 140 laga awal. Pada 190 laga holdout, log loss memburuk dari **1,02748** menjadi **1,04211**; selisih **+0,01463**, interval bootstrap 95% [−0,00834; +0,03709]. Karena interval melintasi nol dan nilai titik memburuk, fitur ini ditolak. Hasil mesin ada di `evidence/lineup_continuity_epl_2015.json`.

### Uji prospektif semu fitur pemulihan

Untuk setiap laga, rata-rata pemulihan bertanda di paruh lawan dihitung **hanya dari laga sebelumnya**, setelah kedua tim memiliki setidaknya lima laga riwayat. Koefisien penyesuaian peluang Elo dipilih pada **140 laga** sebelum 1 Januari 2016 dari grid yang telah ditetapkan; koefisien terpilih `1,0` diuji pada **190 laga** mulai tanggal itu. Log loss Elo murni **1,02748**, sedangkan Elo dengan fitur pemulihan **1,03039**; selisih **+0,00291**, interval bootstrap menurut tanggal laga 95% **[−0,01876; +0,02656]**. Brier juga naik dari **0,61558** menjadi **0,62003**. Tidak ada bukti fitur ini meningkatkan prediksi 1X2 pada uji tersebut. Feed StatsBomb historis diterbitkan setelah laga, sehingga uji kronologis dalam kode belum membuktikan data tersedia tepat waktu pada 2015/16. Detail ada di `reports/tactic_predict.json`.

Uji kedua mengukur tekanan yang diikuti penguasaan baru bagi tim penekan dalam lima detik. Dari **115.402** event `Pressure`, ditemukan **11.295** pergantian penguasaan unik menurut definisi tersebut. Fitur prapertandingan memakai rata-rata hanya dari laga sebelumnya. Pada data pelatihan, log loss terendah memilih koefisien **0,0**, sehingga holdout identik dengan Elo dan fitur tekanan tidak masuk model. Ini hasil penolakan fitur yang sahih; label penyedia belum menjadi anotasi video independen. Laporan ada di `evidence/pressure_predict_epl_2015.json`.

## Kondisi skuad dan batasan

`bola.squad` sekarang menolak timestamp tanpa zona waktu, mengeluarkan bukti setelah waktu analisis, serta menandai lineup resmi kurang dari 11 pemain dan konflik status. Tesnya memakai **data sintetis**. Sembilan kandidat pertandingan pengguna diperiksa oleh `bola.fixtures`: dua telah melewati waktu mulai yang dilaporkan pada 14 Oktober 2026 pukul 23.47 WIB, tujuh belum. Pemeriksaan UEFA berikutnya memverifikasi kesembilan jadwal dan mendapati empat label matchday salah. Starting XI resmi untuk tujuh laga yang belum dimulai teramati sebelum kickoff dan badge pemain direkonsiliasi dengan peran matchday. Waktu publikasi tiap badge dan dampak absensi terhadap peluang belum tervalidasi.

Belum ada odds historis dengan timestamp tiap kutipan, xG lintas musim/kompetisi yang direkonsiliasi, berita skuad lengkap, atau video. Nilai taruhan dan dampak pemain absen belum diukur. Target 95% adalah tujuan kelengkapan proses; belum ada bukti bahwa setiap bagian sudah mencapainya atau bahwa prediksi dapat akurat 95%.
