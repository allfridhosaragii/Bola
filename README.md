# Bola: sistem analisis sepak bola yang dapat diaudit

Proyek ini melanjutkan rancangan dalam percakapan pengguna dengan bukti yang dapat dijalankan ulang. Kini tersedia baseline probabilitas 1X2, pengolah event/tracking dari laga anonim, audit xG Piala Dunia 2018 dan 2022, dan pemeriksa kronologi bukti skuad. Hasil ada di [RESULTS.md](RESULTS.md), sedangkan syarat target 95% ada di [AUDIT.md](AUDIT.md). Tidak ada klaim akurasi atau kesiapan 95% tanpa pengujian yang sesuai.

## Menjalankan

Memerlukan Python 3.10+ dan Git. Pakai checkout yang sudah ada di `/workspace/Bola`; tidak perlu membuat Git worktree.

```bash
cd /workspace/Bola
bash scripts/fetch_data.sh
bash scripts/fetch_tactics.sh
bash scripts/fetch_statsbomb.sh
python3 scripts/fetch_worldcup.py
python3 scripts/fetch_worldcup_2018.py
python3 scripts/fetch_epl_2015.py
python3 scripts/fetch_wsl.py
python3 scripts/fetch_form.py
python3 scripts/fetch_form_extra.py
python3 scripts/fetch_fotmob_form.py
python3 scripts/fetch_fotmob_recent.py
python3 scripts/fetch_understat.py
bash scripts/fetch_odds.sh
python3 -m unittest discover -s tests -v
python3 -m bola.backtest --data-dir .cache/openfootball --output reports/backtest.json
python3 -m bola.backtest --league de.1 --fixed-poisson-weight 0.5 --data-dir .cache/openfootball --output reports/backtest_bundesliga.json
python3 -m bola.backtest --league nl.1 --test-seasons 2024-25 --fixed-poisson-weight 0.5 --data-dir .cache/openfootball --output reports/backtest_eredivisie.json
python3 -m bola.tactics --data-dir .cache/metrica --output reports/tactics.json
python3 -m bola.tactics --game 2 --data-dir .cache/metrica --output reports/tactics_game2.json
python3 -m bola.statsbomb --data-dir .cache/statsbomb --output reports/statsbomb.json
python3 -m bola.worldcup --data-dir .cache/statsbomb --output reports/worldcup.json
python3 -m bola.xg_transfer --output reports/xg_transfer.json
python3 -m bola.xg_provider_compare --output reports/xg_provider_compare.json
python3 -m bola.xg_provider_predict --output reports/xg_provider_predict.json
python3 -m bola.club_audit --output reports/club_audit.json
python3 -m bola.tactic_predict --output reports/tactic_predict.json
python3 -m bola.rotation_predict --output reports/rotation_predict.json
python3 -m bola.pressure_predict --output reports/pressure_predict.json
python3 -m bola.pressure_transfer --output reports/pressure_transfer.json
python3 -m bola.feature_family_audit --output reports/feature_family_audit.json
python3 -m bola.shot_quality_predict --output reports/shot_quality_predict.json
python3 -m bola.shot_quality_transfer --output reports/shot_quality_transfer.json
python3 -m bola.shot_quality_incremental --output reports/shot_quality_incremental.json
python3 -m bola.lineup_continuity_predict --output reports/lineup_continuity_predict.json
python3 -m bola.lineup_continuity_transfer --output reports/lineup_continuity_transfer.json
python3 -m bola.rest_load_predict --output reports/rest_load_predict.json
python3 -m bola.shot_endpoint_audit --output reports/shot_endpoints.json
python3 -m bola.form --cutoff-date-wib 2026-10-15 --output reports/current_form.json
python3 -m bola.form_extra --cutoff-date-wib 2026-10-15 --output reports/current_form_extra.json
python3 -m bola.form_fotmob --cutoff-date-wib 2026-10-15 --output reports/current_form_fotmob.json
python3 -m bola.fotmob_recent_stats --output reports/fotmob_recent_stats.json
python3 -m bola.recovery --data-dir .cache/statsbomb --seconds 15 --output reports/recovery.json
python3 -m bola.odds --scores-dir .cache/openfootball --odds-dir .cache/odds --output reports/odds_benchmark.json
python3 -m bola.odds_multi --league de.1 --scores-dir .cache/openfootball --odds-dir .cache/odds --output reports/odds_bundesliga.json
python3 -m bola.odds_multi --league nl.1 --scores-dir .cache/openfootball --odds-dir .cache/odds --output reports/odds_eredivisie.json
python3 scripts/fetch_uefa_history.py
python3 -m bola.uefa_backtest --output reports/uefa_backtest.json
python3 scripts/fetch_uefa_extended_history.py
python3 -m bola.uefa_extended_backtest --output reports/uefa_extended_backtest.json
```

`fetch_data.sh` mengambil [OpenFootball football.json](https://github.com/openfootball/football.json) commit `e6744429ee395bc86f247348c6184bb08d4eb361` (CC0). `fetch_tactics.sh` mengambil [Metrica Sports sample-data](https://github.com/metrica-sports/sample-data) commit `e706dd506b360d69d9d123d5b8026e7294b13996`, hanya checkout Sample Game 1 dan 2; penggunaan publik harus menyebut Metrica Sports. `fetch_statsbomb.sh` mengambil event dan lineup [StatsBomb open-data](https://github.com/statsbomb/open-data) laga 3869685 pada commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`, dengan checksum SHA-256. `fetch_worldcup.py` mengambil semua 64 laga Piala Dunia 2022 pada commit yang sama; metadata pertandingan memiliki checksum tetap dan file lain dicatat dalam manifest checksum lokal untuk verifikasi ulang. Penggunaan publik harus menyebut StatsBomb. Dataset ada di `.cache/` dan diabaikan Git; data StatsBomb seluruh turnamen sekitar 193 MB. Script tidak mengunduh ulang jika data sudah sesuai. Tidak perlu kredensial API.

`fetch_worldcup_2018.py` mengambil 64 berkas event Piala Dunia 2018 dengan checksum tetap di `data/statsbomb_2018_sha256.json`. `fetch_epl_2015.py` mengambil 380 laga Premier League 2015/16 dengan checksum tetap di `data/statsbomb_epl_2015_sha256.json` (sekitar 1,1 GB cache). `bola.xg_transfer` membandingkan kalibrasi xG 2018 dan 2022 serta seluruh musim klub; untuk musim klub, ia membekukan frekuensi gol hingga 31 Desember 2015 lalu menilainya pada laga mulai 1 Januari 2016. Ini pemeriksaan transfer antar sampel, bukan validasi independen model xG StatsBomb karena riwayat pelatihannya tidak diketahui.

`fetch_understat.py` mengambil satu CSV musim EPL 2015/16 dari [cermin komunitas Understat](https://github.com/douglasbc/scraping-understat-dataset), pada commit dan SHA-256 tetap. `bola.xg_provider_compare` mencocokkan seluruh 380 pasangan kandang/tandang dengan skor akhir yang sama dan tanggal selisih paling jauh satu hari, lalu membandingkan xG per tim per laga. Jumlah tembakan berbeda menurut penyedia, jadi modul ini tidak menyatakan telah mencocokkan setiap tembakan. Laporan lengkap ada di `evidence/xg_provider_compare_epl_2015.json`; berkas sumber mentah hanya disimpan di `.cache/`.

Audit lintas penyedia juga memisahkan penalti. StatsBomb memiliki **9.817 tembakan nonpenalti dan 900,08 npxG**, sedangkan Understat **9.690 dan 923,33**; korelasi npxG per tim-laga **0,8960**. `bola.xg_provider_predict` menerapkan koefisien `0,25` yang dipilih dari StatsBomb ke fitur Understat tanpa penyetelan untuk uji utama. Pada 190 laga holdout, log loss turun dari **1,02748** menjadi **1,01763**, tetapi interval bootstrap selisih **[−0,03485; +0,01683]** melintasi nol. Gerbang ketahanan penyedia belum lulus.

`bola.shot_endpoint_audit` memeriksa ketersediaan kolom post-shot xG dan letak akhir tembakan Saved/Goal dalam seluruh musim klub. Ia juga menghitung rasio penyelamatan deskriptif dan interval Wilson per penjaga gawang ketika tepat satu kiper lawan terlihat di freeze frame; salinan laporan ada di `evidence/shot_endpoints_epl_2015.json`. Endpoint Saved di luar interval lateral gawang nominal menunjukkan bahwa koordinat tersebut tidak boleh langsung dipakai sebagai titik sasaran untuk model post-shot.

`fetch_odds.sh` mengambil CSV Premier League dan Bundesliga 2024/25–2025/26 serta Eredivisie 2024/25 dari [Football-Data](https://www.football-data.co.uk/), dengan checksum tetap. `bola.odds` dan `bola.odds_multi` mencocokkan seluruh **1.678** hasil uji menurut pasangan tim, tanggal, dan skor sebelum membandingkan probabilitas 1X2 model dengan odds rata-rata pembukaan/penutupan yang dinormalisasi. CSV tidak menyertakan timestamp tiap kutipan odds, sehingga hasilnya adalah benchmark historis, bukan simulasi keputusan taruhan saat itu.

`bola.recovery` memeriksa checksum event 64 laga Piala Dunia 2022, lalu mengelompokkan pemulihan bola berhasil pertama per penguasaan bola berdasarkan paruh lapangan. Ia menghitung tembakan tim yang sama dalam penguasaan dan jendela waktu yang sama, serta interval bootstrap menurut pertandingan. Ini mengukur hubungan deskriptif lokasi pemulihan dan tembakan, bukan sebab akibat atau label pressing yang tervalidasi.

`bola.club_audit` menerapkan pemeriksaan pemulihan yang sama pada 380 laga Premier League 2015/16, mencocokkan 760 starting XI dengan ID tim, dan menghitung jumlah starter berubah dari laga sebelumnya pada 740 penampilan tim yang memiliki pembanding. Ia membandingkan poin aktual dengan baseline Elo berbasis hasil terdahulu dalam tiga kelompok rotasi. Hasil rotasi bersifat deskriptif; alasan pemain tidak tampil tidak tersedia.

`bola.tactic_predict` memakai rata-rata pemulihan di paruh lawan dari laga-laga terdahulu saja sebagai fitur 1X2 tambahan pada Elo. Koefisien dipilih dari 140 laga sebelum 1 Januari 2016, lalu diuji pada 190 laga setelahnya. Fitur tersebut tidak memperbaiki log loss uji pada sampel ini; lihat `reports/tactic_predict.json`. Ini uji fitur historis, bukan bukti tersedianya feed event sebelum pertandingan berikutnya.

`bola.rotation_predict` menguji jumlah starter berubah dibanding laga sebelumnya sebagai fitur tambahan 1X2: koefisien dipilih dari 180 laga sebelum 1 Januari 2016 dan diuji pada 190 laga berikutnya. Fitur itu juga tidak memperbaiki log loss uji. Ini bukan estimasi dampak pemain absen karena alasan rotasi tidak tersedia.

`bola.pressure_predict` memeriksa 115.402 event tekanan dan 11.295 penguasaan unik yang berpindah ke tim penekan dalam lima detik. Koefisien dipilih tanpa melihat 190 laga holdout; nilai yang terpilih adalah **0**, sehingga fitur tekanan ditolak. `bola.lineup_continuity_predict` memberi bobot pemain yang tidak masuk XI menurut frekuensi start dalam lima laga sebelumnya. Fitur itu dipilih pada 140 laga awal, tetapi log loss holdout memburuk dari **1,02748** menjadi **1,04211** pada 190 laga. Interval perbedaannya melintasi nol. Kedua hasil ini mencegah metrik taktik atau skuad yang belum terbukti masuk ke peluang pertandingan.

`bola.pressure_transfer` menambah **157.628 event tekanan** dan **15.145** perebutan penguasaan unik dari 457 laga WSL. Tiga dataset musim awal memilih koefisien `0,5`, lalu 2023/24 digunakan sebagai holdout 102 laga. Log loss turun dari **0,97354** menjadi **0,95348**, tetapi interval bootstrap selisih **[−0,04389; +0,00437]** melintasi nol. Fitur tetap ditolak karena belum melewati gerbang ketidakpastian.

`bola.feature_family_audit` menyatukan empat fitur pada 102 laga WSL 2023/24 yang sama dan menjalankan 8.000 bootstrap per tanggal. Interval Bonferroni 98,75% per fitur mengendalikan tingkat kesalahan keluarga 5%. Form gol tetap lulus dengan selisih log loss **−0,05851 [−0,09134; −0,02395]**, demikian pula npxG **−0,10892 [−0,16202; −0,05758]**. Tekanan dan kontinuitas XI gagal. Audit ini mengoreksi penggunaan ulang holdout secara retrospektif; ia bukan holdout baru atau izin penerapan UEFA.

`bola.lineup_continuity_transfer` membekukan koefisien EPL tersebut lalu mengujinya tanpa penyetelan pada empat dataset musim WSL. Sebanyak **914 Starting XI** dari 457 laga diperiksa dengan 461 checksum. Pada 335 prediksi, log loss memburuk dari **0,95753** menjadi **0,97195**; selisih **+0,01442** dengan interval bootstrap **[−0,00107; +0,03014]**. Karena fitur gagal pada holdout EPL dan transfer WSL, fitur kontinuitas ditolak sebagai input probabilitas.

`bola.rest_load_predict` menguji selisih hari istirahat yang dibatasi maksimum 14 hari. Tiga dataset musim WSL awal menyediakan 307 prediksi pelatihan dan memilih koefisien `0`; holdout 2023/24 berisi 126 prediksi sehingga hasilnya identik dengan Elo. Dari 866 observasi tim, hanya 13 memiliki istirahat tiga hari atau kurang. Waktu istirahat tetap dilaporkan sebagai konteks jadwal, tetapi tidak mengubah peluang model.

`bola.shot_quality_predict` menguji selisih rata-rata npxG dalam tepat lima laga terdahulu sebagai tambahan pada Elo. Seluruh **380 laga, 1.313.773 event, dan 9.817 tembakan nonpenalti** diperiksa dengan checksum. Koefisien dipilih pada 140 laga awal dan diuji pada 190 laga mulai 1 Januari 2016. Log loss turun dari **1,02748** menjadi **1,01202**, tetapi interval bootstrap selisihnya **[−0,03803; +0,00780]** melintasi nol. Sesuai gerbang yang ditetapkan, fitur belum dimasukkan ke model UEFA.

`fetch_wsl.py` mengambil empat dataset musim FA Women's Super League dari commit StatsBomb yang sama: 2018/19, 2019/20 yang terhenti, 2020/21, dan 2023/24. Sebanyak **457 pertandingan dan 457 berkas event** diperiksa terhadap hash SHA-256 yang disimpan di `data/statsbomb_wsl_sha256.json`. `bola.shot_quality_transfer` membekukan koefisien `0,25` yang dipilih pada EPL tanpa menyetel ulang pada WSL. Pada 335 prediksi yang memiliki lima laga riwayat musim itu, log loss turun dari **0,95753** menjadi **0,85019**, dengan interval bootstrap selisih **[−0,13269; −0,08185]**. Gerbang transfer tersebut lulus, tetapi belum membuktikan transfer ke kompetisi UEFA pria atau ketersediaan feed xG sebelum pertandingan.

`bola.shot_quality_incremental` menguji pembanding yang lebih kuat. Bobot form selisih gol, npxG, dan gabungannya dipilih hanya pada 140 laga EPL awal lalu dibekukan. Di WSL, model form gol mencapai log loss **0,89533**, sedangkan npxG **0,85019**. Selisih npxG dikurangi form gol **−0,04514** memiliki interval bootstrap 95% **[−0,05932; −0,03039]**. Grid gabungan memilih bobot gol `0` setelah npxG tersedia. Ini membuktikan nilai tambah dalam sampel transfer tersebut, bukan kesiapan penggunaan UEFA.

`fetch_uefa_history.py` mengambil kalender dan hasil resmi 144 laga fase liga UEFA 2024/25, 144 laga 2025/26, serta 18 laga MD1 2026/27 dari [API pertandingan UEFA](https://match.uefa.com/v5/), lalu menyimpan respons mentah, checksum, dan waktu pengambilan dalam folder snapshot. `bola.uefa_backtest` menguji model skor 1X2 lintas klub dan liga secara kronologis dengan ID tim resmi: musim pertama untuk riwayat, musim kedua untuk validasi, dan 18 laga MD1 musim ketiga sebagai uji kecil berikutnya. Bobot campuran 0,5 berasal dari validasi Premier League, bukan dipilih menggunakan laga UEFA. Snapshot historis tidak menyediakan waktu pertama publikasi setiap hasil; uji tanggal mencegah pemakaian hasil laga mendatang dalam kode, tetapi tidak membuktikan histori feed sumber.

`python3 -m bola.uefa_forecast` membekukan ramalan 1X2 **eksploratif** untuk tujuh laga UEFA 15 Oktober 2026 pukul 02.00 WIB, jika dijalankan sebelum kickoff. Ia memasukkan hanya hasil yang sudah `FINISHED` pada tanggal sebelumnya, menolak laga yang sudah dimulai, dan menyimpan waktu pembuatan serta checksum sumber dalam berkas `prospective/` yang tidak ditimpa. Perintah ini khusus untuk periode tersebut; berkasnya dipakai untuk pengujian setelah hasil keluar, bukan dua rekomendasi taruhan.

Riwayat UEFA yang diperluas berisi **1.114 pertandingan resmi** dari 2022/23 sampai 14 Oktober 2026: kualifikasi, fase grup/liga, dan gugur. Model tetap dinilai hanya pada fase liga yang ditetapkan sebelumnya. Grid 2024/25 memilih bobot Elo 0,75, tetapi perbaikannya terhadap bobot 0,50 hanya **0,000013 log loss** dengan interval bootstrap 95% **[−0,00753; 0,00698]**. Karena interval melintasi nol, aturan penerapan mempertahankan bobot 0,50. Pada 18 laga Matchday 2 musim 2026/27, log loss campuran yang dipertahankan adalah **0,9016**, dibanding baseline frekuensi **0,9451**. Sampel itu merupakan holdout retrospektif setelah hasil selesai dan belum dibandingkan dengan odds pasar. Laporan terverifikasi ada di `evidence/uefa_extended_backtest_2026-10-15.json`.

### Alur analis untuk tanggal UEFA berikutnya

Untuk tanggal pertandingan baru, jalankan `bola.uefa_forecast_live` dengan **tanggal UTC** dan musim UEFA. Misalnya laga 20 Oktober 2026 UTC (dua laga dimulai 23.45 WIB dan sisanya 21 Oktober 02.00 WIB):

```bash
python3 -m bola.uefa_forecast_live --target-date-utc 2026-10-20 --season-year 2027
python3 -m bola.uefa_forecast_live --verify prospective/uefa_2026-10-15T15-53-23.675934+00-00.json
```

Satu perintah untuk penyegaran menyeluruh sebelum kickoff adalah `bash scripts/refresh_uefa_target.sh 2026-10-20`. Perintah ini mengambil ulang data form, kalender, dan lima pertandingan terkini tiap tim, membuat arsip peluang baru, memeriksa ulang sumbernya, lalu menyimpan status fixture, beban jadwal, statistik pertandingan, skuad, lineup, dan form sebagai laporan bertimestamp di `reports/`. Alur ini telah dijalankan ujung ke ujung pada 15 Oktober: sembilan fixture, sembilan pasangan skuad terdaftar, sembilan pasangan kalender yang cocok, statistik terkini 18/18 tim, nol XI target resmi, dan form 18/18 tim. Jalankan ulang menjelang pertandingan; hasil lama tidak otomatis menjadi bukti keadaan saat kickoff. Saat ini protokol riwayat model mendukung musim UEFA 2026/27.

Penyegaran itu juga membuat satu laporan analis yang menggabungkan semua bukti. Contoh terbaru dengan riwayat UEFA diperluas, parameter model, beban jadwal, dan statistik terkini tercatat ada di `evidence/analyst_report_current_stats_2026-10-15.json`. Untuk merakitnya secara manual:

```bash
python3 -m bola.analyst_report \
  --forecast prospective/uefa_2026-10-15T15-53-23.675934+00-00.json \
  --form evidence/uefa_target_form_2026-10-15.json \
  --squad evidence/uefa_target_squad_model_gate_2026-10-15.json \
  --schedule evidence/schedule_load_target_2026-10-15.json \
  --recent-stats evidence/fotmob_target_recent_stats_2026-10-15.json \
  --output reports/analyst_report.json
```

Laporan memeriksa kesamaan ID, tim, kickoff, urutan waktu sumber, kesegaran fixture, form 5/10/20, beban jadwal, skuad terdaftar, XI resmi, odds, bukti taktik, dan validasi model terhadap pasar. Peluang model tetap dicatat untuk penilaian prospektif. Selama satu gerbang wajib belum lulus, status pertandingan adalah `no_selection`.

Perintah pertama mengambil kalender, hasil yang telah selesai sebelum tanggal target, dan jadwal target dari API resmi UEFA. Semua laga pada tanggal UTC target dihitung dari keadaan model yang sama agar hasil laga lebih awal pada hari itu tidak bocor ke ramalan laga berikutnya. Respons mentah disimpan di `.cache/uefa_forecast/`; arsip di `prospective/` mencatat checksum dan hash kode model. Perintah kedua menghitung ulang arsip dari snapshot lokal serta memeriksa hash; simpan snapshot tersebut bila ingin memverifikasi arsip pada mesin lain. Arsip tidak ditimpa. Jika kode model berubah, verifikasi membutuhkan versi kode yang tercatat dalam arsip.

Pada hari pertandingan, cocokkan dulu nama tim, kompetisi, waktu, dan ID pertandingan dari sumber resmi. Perbarui form dan bukti skuad dengan cutoff yang sesuai; starting XI hanya dianggap resmi setelah feed UEFA memuat sebelas pemain per tim sebelum kickoff. Tangkapan layar jadwal atau odds adalah petunjuk awal yang harus dicocokkan dengan fixture UEFA. Jangan gunakan data yang pertama kali diambil setelah kickoff untuk mengklaim analisis prapertandingan.

Untuk snapshot resmi fixture, daftar skuad, dan status lineup dari arsip target, jalankan:

```bash
python3 -m bola.uefa_target_snapshot --forecast prospective/uefa_2026-10-15T15-53-23.675934+00-00.json --output reports/uefa_target_2026-10-20_refresh.json
```

Snapshot awal 15 Oktober ada di `evidence/uefa_target_squad_2026-10-15.json`: sembilan fixture masih Upcoming; daftar pemain terdaftar tersedia untuk 18 tim, tetapi belum ada starting XI resmi. Nama dan waktu dari halaman UEFA diperiksa terhadap arsip model. Untuk statistik liga, `bola.target_form_audit` menyatukan tiga sumber form yang telah diperiksa waktu pengambilannya. Snapshot awal ada di `evidence/uefa_target_form_2026-10-15.json`: jendela 5/10/20 tersedia untuk **18 dari 18 tim** setelah liga Czech dan Azerbaijan ditambahkan dari FotMob. Dua liga itu hanya memiliki satu penyedia hasil yang diverifikasi dalam proyek ini. Ambil ulang data form setelah pertandingan liga berikutnya sebelum memakai ringkasan itu dekat kickoff.

Jika ada tangkapan layar odds 1X2, transkripsikan nilainya ke JSON lokal dengan `match_id`, `home`, `away`, `kickoff`, `observed_at` berzona waktu, `bookmaker`, `market` bernilai `1X2_regular_time`, `decimal_odds` berisi `home`/`draw`/`away`, dan `screenshot_path`. Lalu jalankan:

```bash
python3 -m bola.market_snapshot --forecast prospective/uefa_2026-10-15T15-53-23.675934+00-00.json --quote /tmp/odds_quote.json --output reports/odds_quote_comparison.json
```

Modul ini menolak identitas laga yang berbeda, harga invalid, bukti gambar kosong, serta waktu setelah kickoff. Ia menyimpan SHA-256 gambar, menghitung margin pasar dan probabilitas 1X2 pasar setelah margin dinormalisasi. Jam dan angka di gambar masih memerlukan pemeriksaan manusia: transkripsi JSON tidak membuktikan isi layar atau bahwa harga dapat dipasang saat itu. Perbandingan tersebut bukan sinyal taruhan. Jika odds, lineup, atau bukti kualitas model tidak memadai, hasil analisis adalah **tunda/tidak ada pilihan**, bukan dua pilihan yang dipaksakan.

Setelah semua laga dalam arsip selesai, nilai distribusi yang **sudah dibekukan** terhadap skor resmi UEFA:

```bash
python3 -m bola.uefa_score prospective/uefa_2026-10-15T15-53-23.675934+00-00.json --output reports/uefa_score_2026-10-20.json
```

Perintah penilaian menolak hasil yang belum final, perubahan identitas fixture, serta arsip yang dibuat sesudah kickoff. Ulangi pengamatan prospektif pada banyak tanggal sebelum menyimpulkan kalibrasi atau manfaat terhadap pasar.

Ketujuh laga sudah selesai dan arsip dinilai tanpa mengubah peluangnya. Jalankan ulang dengan respons resmi yang dibekukan: `python3 -m bola.uefa_score prospective/uefa_2026-10-14T18-02-34.009581+00-00.json --results-json prospective/uefa_results_2026-10-15T07-58-54Z.json --output reports/uefa_prospective_score.json`. Hapus laporan lama terlebih dahulu jika menjalankan ulang; perintah sengaja menolak menimpanya. Penilai mencocokkan ID/waktu/tim dan menghitung log loss, Brier, serta akurasi pilihan tertinggi. Laporan penilaian yang dapat ditinjau ada di `prospective/uefa_score_2026-10-15T07-58-07Z.json`.

Untuk form terkini, ambil snapshot liga domestik 2025/26 dan 2026/27 dari Football-Data, lalu pakai cutoff tanggal WIB:

```bash
python3 scripts/fetch_form.py
python3 -m bola.form --cutoff-date-wib 2026-10-15 --output reports/current_form.json
python3 scripts/fetch_form_extra.py
python3 -m bola.form_extra --cutoff-date-wib 2026-10-15 --output reports/current_form_extra.json
python3 scripts/fetch_fotmob_form.py
python3 -m bola.form_fotmob --cutoff-date-wib 2026-10-15 --output reports/current_form_fotmob.json
python3 scripts/fetch_fotmob_target_teams.py
python3 -m bola.form_crosscheck --form reports/current_form.json --extra-form reports/current_form_extra.json --fotmob-form reports/current_form_fotmob.json --cutoff-date-wib 2026-10-15 --output reports/form_crosscheck.json
python3 -m bola.schedule_load --forecast prospective/uefa_2026-10-15T15-53-23.675934+00-00.json --output reports/schedule_load.json
python3 scripts/fetch_fotmob_target_recent.py
python3 -m bola.fotmob_recent_stats --data-dir .cache/fotmob_target_recent/LOKASI_SNAPSHOT --output reports/target_recent_stats.json
python3 scripts/fetch_fotmob_recent.py
python3 -m bola.fotmob_recent_stats --output reports/fotmob_recent_stats.json
```

Delapan belas CSV mencakup sembilan liga dalam `.cache/form/`; dua CSV lain untuk Austria dan Norwegia ada di `.cache/form_extra/`. Manifest mencatat URL, waktu pengambilan, dan SHA-256 setiap berkas. Snapshot lama tersimpan di subfolder `snapshots/` dan dapat dijalankan ulang dengan `--data-dir` yang menunjuk foldernya. Kedua pengolah hanya memasukkan hasil bertanggal **sebelum** cutoff serta menghitung jendela 5/10/20 laga, bobot waktu, pembagian kandang/tandang, gol, dan surplus hasil terhadap Elo lawan sebelum pertandingan. Statistik tembakan, corner, kartu, dan xG hanya tersedia pada liga dan baris tertentu. Elo dihitung terpisah per liga dan tidak dapat dibandingkan langsung lintas liga. Form ini tidak mencakup pertandingan UEFA atau piala domestik.

`fetch_fotmob_form.py` membekukan delapan halaman liga FotMob/enet Slovakia, Ukraina, Czech, dan Azerbaijan untuk 2025/26–2026/27 dengan waktu pengambilan dan SHA-256. `bola.form_fotmob` memeriksa ID liga, musim, ID tim, status serta skor laga, menyingkirkan laga yang dibatalkan atau diputuskan administratif, lalu menghitung form Shakhtar, Slovan Bratislava, Slavia Praha, dan Sabah. Halaman Slovakia/Ukraina pertama kali diambil **setelah** kickoff laga 15 Oktober, sehingga angka dua klub itu hanya rekonstruksi retrospektif untuk laga lama. Halaman Czech/Azerbaijan diambil sebelum laga target 20 Oktober UTC. Semua halaman tetap berupa satu penyedia dan belum menggantikan verifikasi hasil dengan sumber independen.

`fetch_fotmob_target_teams.py` mengambil halaman tim terpisah untuk 18 klub target. `bola.form_crosscheck` hanya membandingkan pertandingan liga utama yang selesai sebelum cutoff. Lima hasil terakhir untuk **15 tim**, total **75 pertandingan**, cocok antara sumber utama Football-Data dan FotMob pada tanggal (toleransi satu hari karena zona waktu), venue, dan skor. Slavia Praha, Sabah, dan Slovan Bratislava memakai FotMob pada kedua sisi sehingga ditandai `same-provider` dan tidak dihitung sebagai verifikasi independen. Artefak lengkap ada di `evidence/form_crosscheck_target_2026-10-15.json`.

`bola.schedule_load` memeriksa checksum 18 halaman tim, mencocokkan kandang/tandang dan kickoff dengan arsip UEFA, lalu menghitung pertandingan kompetitif selesai dalam 14/28 hari dan jadwal di antara waktu pengambilan dan kickoff target. Kedua halaman tim menyepakati ID FotMob untuk **9/9 pertandingan**. Sebanyak **17 dari 18 tim** memiliki satu pertandingan terjadwal sebelum target; Porto tidak. Waktu istirahat terproyeksi terpendek adalah **72,25 jam**. Angka ini tidak mengukur menit pemain, perjalanan, tidur, atau kelelahan. Bukti ada di `evidence/schedule_load_target_2026-10-15.json`.

`fetch_fotmob_target_recent.py` membekukan lima pertandingan kompetitif terakhir bagi 18 tim dengan 90 observasi tim-pertandingan dari 82 laga unik. `bola.fotmob_recent_stats` memeriksa ID, kompetisi, kickoff, status, skor, checksum, serta XI. Statistik tersedia pada **84/90 observasi** dan seluruh 18 tim memiliki setidaknya satu halaman statistik; 14 tim lengkap 5/5. XI lengkap tersedia pada **86/90 observasi**, dengan 16 tim lengkap 5/5. Ringkasan mencakup tembakan, tepat sasaran, peluang besar, sentuhan kotak lawan, penguasaan, operan, corner, disiplin, penyelamatan, formasi, pemain inti, dan perubahan starter. Ini data deskriptif dari satu penyedia dan tidak dianggap sebagai model taktik tervalidasi. Bukti ada di `evidence/fotmob_target_recent_stats_2026-10-15.json`.

`fetch_fotmob_recent.py` membekukan halaman pertandingan untuk lima laga liga terakhir sebelum cutoff dari masing-masing dua klub itu. `bola.fotmob_recent_stats` memeriksa identitas laga, waktu, skor, dan checksum, kemudian menghitung rata-rata statistik yang **benar-benar ada** pada halaman. Kedua tim memiliki data tembakan, tepat sasaran, penguasaan bola, dan corner pada 5/5 laga. FotMob menyediakan metrik lebih lengkap untuk Slovan daripada Shakhtar; kolom yang tidak tersedia tidak diisi dengan perkiraan. Rincian dan cakupan tiap metrik ada di `evidence/fotmob_recent_stats_2026-10-15.json`.

## Ledger bukti skuad

Modul `bola.squad` menerima JSON dengan `fixture.home`, `fixture.away`, `fixture.kickoff`, `as_of`, dan daftar `evidence`. Tiap bukti berisi `team`, `player`, `claim`, `source_kind`, `source_url`, `published_at`, dan `retrieved_at`. Gunakan timestamp ISO 8601 dengan zona waktu. `claim`: `starting`, `bench`, `out_injured`, `out_suspended`, `doubtful`, `available`.

```json
{
  "fixture": {"home": "Contoh A", "away": "Contoh B", "kickoff": "2026-10-15T20:00:00+07:00"},
  "as_of": "2026-10-15T18:00:00+07:00",
  "evidence": []
}
```

Jalankan `python3 -m bola.squad path/ledger.json --output reports/squad.json`. URL dan kategori sumber harus diperiksa manusia terhadap artikel/daftar resmi; validator tidak mengunduh halaman dan tidak menyatakan kebenaran klaim dari metadata saja. Tidak ada laporan skuad pertandingan nyata tanpa data sumber tersebut.

## Kandidat pertandingan pengguna

Daftar sembilan pertandingan yang diberikan pengguna untuk 14–15 Oktober 2026 WIB dicatat di [examples/candidate_fixtures_2026-10-14.json](examples/candidate_fixtures_2026-10-14.json). Ini **laporan pengguna, bukan jadwal terverifikasi**. Audit waktu yang dapat direproduksi:

```bash
python3 -m bola.fixtures examples/candidate_fixtures_2026-10-14.json --as-of 2026-10-14T23:47:15+07:00 --output reports/fixture_candidates.json
```

Pada waktu tersebut, dua kandidat pukul 23.45 WIB sudah melewati waktu mulai yang dilaporkan; tujuh kandidat pukul 02.00 WIB masih sebelum waktu mulai yang dilaporkan. Status pertandingan aktual, identitas singkatan seperti “Madrid” dan “VfB”, kompetisi, serta jadwal harus dikonfirmasi dengan sumber pertandingan yang dapat diakses sebelum analisis pra-laga. Pemeriksaan ini tidak mengubah laporan pengguna menjadi verifikasi resmi.

Verifikasi resmi yang kemudian berhasil dijalankan:

```bash
python3 -m bola.uefa --output reports/uefa_fixtures.json
python3 -m bola.uefa_squad --fixtures reports/uefa_fixtures.json --output reports/uefa_squads.json
python3 -m bola.uefa_lineup_api --fixtures reports/uefa_fixtures.json --output reports/uefa_lineups.json
python3 -m bola.rotation --lineups reports/uefa_lineups.json --output reports/uefa_rotation.json
```

`bola.uefa` membaca [sitemap pertandingan Liga Champions UEFA](https://www.uefa.com/sitemap/matches/uefachampionsleague.xml) dan halaman sembilan pertandingan, lalu memeriksa pasangan tim, waktu mulai, kompetisi, status, dan matchday. `bola.uefa_squad` membaca daftar skuad resmi serta badge status pemain untuk laga yang masih berstatus Upcoming. Snapshot HTML dan checksum disimpan di `.cache/uefa`; laporan waktu pengambilan di `reports/`. Daftar skuad tidak sama dengan starting XI; badge pemain tidak mempunyai timestamp publikasi pada halaman tersebut dan tidak boleh dijadikan konfirmasi absen dalam pertandingan tertentu tanpa pemeriksaan lanjutan.

`bola.uefa_lineup_api` membaca endpoint resmi yang dipakai halaman lineup UEFA, memeriksa identitas tim dan kickoff, lalu memerlukan tepat 11 pemain unik per tim sebelum menandai starting XI lengkap. Respons dan checksum SHA-256 disimpan di `.cache/uefa/api`. Waktu pengambilan dibedakan dari waktu pengumuman lineup, yang tidak ada pada respons API. Lineup yang baru diamati setelah kickoff tidak dapat dipakai sebagai bukti keputusan prapertandingan.

`bola.rotation` membandingkan ID 11 starter UEFA MD1 dengan lineup yang diamati sebelum MD2. Hasilnya menghitung starter yang dipertahankan, starter baru dari bangku cadangan MD1, starter baru yang tidak ada di daftar hari pertandingan MD1, serta posisi umum pemain baru menurut UEFA. Perubahan ini tidak mengidentifikasi sebab pergantian atau formasi taktik. Jalankan setelah `fetch_uefa_history.py` dan `bola.uefa_lineup_api`.

Untuk menggabungkan fixture UEFA, daftar skuad, dan form domestik pada satu waktu analisis:

```bash
python3 -m bola.dossier --fixtures reports/uefa_fixtures.json --squads reports/uefa_squads.json --lineups reports/uefa_lineups.json --form reports/current_form.json --extra-form reports/current_form_extra.json --output reports/prematch_dossier.json
```

`bola.dossier` memeriksa kecocokan fixture dan waktu sumber, membandingkan badge skuad dengan peran starter/bangku cadangan resmi menurut ID pemain, mencatat hari sejak laga **liga domestik yang tercakup sumber**, lalu memberi gerbang bukti per laga. Jumlah hari itu bukan ukuran istirahat total karena laga piala dan tim nasional tidak tercakup. Status fixture, daftar skuad, dan lineup perlu diambil ulang jika snapshot lebih tua dari 30 menit. Laporan tersebut belum menyatakan siap menghasilkan dua prediksi sampai tersedia starting XI resmi sebelum kickoff, odds kini dengan waktu pengambilan, serta model probabilitas antarliga yang tervalidasi. Jika memakai `--as-of`, waktunya harus sesuai dengan saat sumber sudah tersedia.

Jalankan `bash scripts/refresh_uefa_prematch.sh` untuk mengambil ulang ketiga sumber UEFA dan menyusun dossier pada waktu terkini. Snapshot respons API lineup disimpan dengan nama bertimestamp agar perubahan status sebelum kickoff dapat diperiksa kemudian. Pastikan `reports/current_form.json` sudah memakai cutoff tanggal WIB yang sama dengan hari pemeriksaan.

## Protokol model

- Riwayat awal 2020/21–2022/23, validasi 2023/24, lalu pengujian pada musim setelahnya. Semua laga bertanggal sama diprediksi sebelum hasil tanggal itu dimasukkan.
- OpenFootball memakai dua format skor final; keduanya dibaca. Audit menghentikan analisis jika jumlah fixture unik atau skor final tidak lengkap.
- Metrik: akurasi 1X2, Brier multiclass, log loss, RPS, ECE keyakinan 10 bin, dan bootstrap berpasangan menurut tanggal.
- Dataset adalah snapshot tanpa timestamp publikasi historis per hasil. Pemisahan tanggal mencegah penggunaan hasil laga masa depan dalam model, tetapi belum membuktikan kapan tiap data sumber tersedia.
- Model 1X2 belum memakai xG, odds, cedera, atau skuad. Prediksinya bukan analisis pasar taruhan lengkap.
