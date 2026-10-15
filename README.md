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
python3 -m bola.club_audit --output reports/club_audit.json
python3 -m bola.tactic_predict --output reports/tactic_predict.json
python3 -m bola.rotation_predict --output reports/rotation_predict.json
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
```

`fetch_data.sh` mengambil [OpenFootball football.json](https://github.com/openfootball/football.json) commit `e6744429ee395bc86f247348c6184bb08d4eb361` (CC0). `fetch_tactics.sh` mengambil [Metrica Sports sample-data](https://github.com/metrica-sports/sample-data) commit `e706dd506b360d69d9d123d5b8026e7294b13996`, hanya checkout Sample Game 1 dan 2; penggunaan publik harus menyebut Metrica Sports. `fetch_statsbomb.sh` mengambil event dan lineup [StatsBomb open-data](https://github.com/statsbomb/open-data) laga 3869685 pada commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`, dengan checksum SHA-256. `fetch_worldcup.py` mengambil semua 64 laga Piala Dunia 2022 pada commit yang sama; metadata pertandingan memiliki checksum tetap dan file lain dicatat dalam manifest checksum lokal untuk verifikasi ulang. Penggunaan publik harus menyebut StatsBomb. Dataset ada di `.cache/` dan diabaikan Git; data StatsBomb seluruh turnamen sekitar 193 MB. Script tidak mengunduh ulang jika data sudah sesuai. Tidak perlu kredensial API.

`fetch_worldcup_2018.py` mengambil 64 berkas event Piala Dunia 2018 dengan checksum tetap di `data/statsbomb_2018_sha256.json`. `fetch_epl_2015.py` mengambil 380 laga Premier League 2015/16 dengan checksum tetap di `data/statsbomb_epl_2015_sha256.json` (sekitar 1,1 GB cache). `bola.xg_transfer` membandingkan kalibrasi xG 2018 dan 2022 serta seluruh musim klub; untuk musim klub, ia membekukan frekuensi gol hingga 31 Desember 2015 lalu menilainya pada laga mulai 1 Januari 2016. Ini pemeriksaan transfer antar sampel, bukan validasi independen model xG StatsBomb karena riwayat pelatihannya tidak diketahui.

`fetch_understat.py` mengambil satu CSV musim EPL 2015/16 dari [cermin komunitas Understat](https://github.com/douglasbc/scraping-understat-dataset), pada commit dan SHA-256 tetap. `bola.xg_provider_compare` mencocokkan seluruh 380 pasangan kandang/tandang dengan skor akhir yang sama dan tanggal selisih paling jauh satu hari, lalu membandingkan xG per tim per laga. Jumlah tembakan berbeda menurut penyedia, jadi modul ini tidak menyatakan telah mencocokkan setiap tembakan. Laporan lengkap ada di `evidence/xg_provider_compare_epl_2015.json`; berkas sumber mentah hanya disimpan di `.cache/`.

`bola.shot_endpoint_audit` memeriksa ketersediaan kolom post-shot xG dan letak akhir tembakan Saved/Goal dalam seluruh musim klub. Ia juga menghitung rasio penyelamatan deskriptif dan interval Wilson per penjaga gawang ketika tepat satu kiper lawan terlihat di freeze frame; salinan laporan ada di `evidence/shot_endpoints_epl_2015.json`. Endpoint Saved di luar interval lateral gawang nominal menunjukkan bahwa koordinat tersebut tidak boleh langsung dipakai sebagai titik sasaran untuk model post-shot.

`fetch_odds.sh` mengambil CSV Premier League dan Bundesliga 2024/25–2025/26 serta Eredivisie 2024/25 dari [Football-Data](https://www.football-data.co.uk/), dengan checksum tetap. `bola.odds` dan `bola.odds_multi` mencocokkan seluruh **1.678** hasil uji menurut pasangan tim, tanggal, dan skor sebelum membandingkan probabilitas 1X2 model dengan odds rata-rata pembukaan/penutupan yang dinormalisasi. CSV tidak menyertakan timestamp tiap kutipan odds, sehingga hasilnya adalah benchmark historis, bukan simulasi keputusan taruhan saat itu.

`bola.recovery` memeriksa checksum event 64 laga Piala Dunia 2022, lalu mengelompokkan pemulihan bola berhasil pertama per penguasaan bola berdasarkan paruh lapangan. Ia menghitung tembakan tim yang sama dalam penguasaan dan jendela waktu yang sama, serta interval bootstrap menurut pertandingan. Ini mengukur hubungan deskriptif lokasi pemulihan dan tembakan, bukan sebab akibat atau label pressing yang tervalidasi.

`bola.club_audit` menerapkan pemeriksaan pemulihan yang sama pada 380 laga Premier League 2015/16, mencocokkan 760 starting XI dengan ID tim, dan menghitung jumlah starter berubah dari laga sebelumnya pada 740 penampilan tim yang memiliki pembanding. Ia membandingkan poin aktual dengan baseline Elo berbasis hasil terdahulu dalam tiga kelompok rotasi. Hasil rotasi bersifat deskriptif; alasan pemain tidak tampil tidak tersedia.

`bola.tactic_predict` memakai rata-rata pemulihan di paruh lawan dari laga-laga terdahulu saja sebagai fitur 1X2 tambahan pada Elo. Koefisien dipilih dari 140 laga sebelum 1 Januari 2016, lalu diuji pada 190 laga setelahnya. Fitur tersebut tidak memperbaiki log loss uji pada sampel ini; lihat `reports/tactic_predict.json`. Ini uji fitur historis, bukan bukti tersedianya feed event sebelum pertandingan berikutnya.

`bola.rotation_predict` menguji jumlah starter berubah dibanding laga sebelumnya sebagai fitur tambahan 1X2: koefisien dipilih dari 180 laga sebelum 1 Januari 2016 dan diuji pada 190 laga berikutnya. Fitur itu juga tidak memperbaiki log loss uji. Ini bukan estimasi dampak pemain absen karena alasan rotasi tidak tersedia.

`fetch_uefa_history.py` mengambil kalender dan hasil resmi 144 laga fase liga UEFA 2024/25, 144 laga 2025/26, serta 18 laga MD1 2026/27 dari [API pertandingan UEFA](https://match.uefa.com/v5/), lalu menyimpan respons mentah, checksum, dan waktu pengambilan dalam folder snapshot. `bola.uefa_backtest` menguji model skor 1X2 lintas klub dan liga secara kronologis dengan ID tim resmi: musim pertama untuk riwayat, musim kedua untuk validasi, dan 18 laga MD1 musim ketiga sebagai uji kecil berikutnya. Bobot campuran 0,5 berasal dari validasi Premier League, bukan dipilih menggunakan laga UEFA. Snapshot historis tidak menyediakan waktu pertama publikasi setiap hasil; uji tanggal mencegah pemakaian hasil laga mendatang dalam kode, tetapi tidak membuktikan histori feed sumber.

`python3 -m bola.uefa_forecast` membekukan ramalan 1X2 **eksploratif** untuk tujuh laga UEFA 15 Oktober 2026 pukul 02.00 WIB, jika dijalankan sebelum kickoff. Ia memasukkan hanya hasil yang sudah `FINISHED` pada tanggal sebelumnya, menolak laga yang sudah dimulai, dan menyimpan waktu pembuatan serta checksum sumber dalam berkas `prospective/` yang tidak ditimpa. Perintah ini khusus untuk periode tersebut; berkasnya dipakai untuk pengujian setelah hasil keluar, bukan dua rekomendasi taruhan.

Ketujuh laga sudah selesai dan arsip dinilai tanpa mengubah peluangnya. Jalankan ulang dengan respons resmi yang dibekukan: `python3 -m bola.uefa_score prospective/uefa_2026-10-14T18-02-34.009581+00-00.json --results-json prospective/uefa_results_2026-10-15T07-58-54Z.json --output reports/uefa_prospective_score.json`. Hapus laporan lama terlebih dahulu jika menjalankan ulang; perintah sengaja menolak menimpanya. Penilai mencocokkan ID/waktu/tim dan menghitung log loss, Brier, serta akurasi pilihan tertinggi. Laporan penilaian yang dapat ditinjau ada di `prospective/uefa_score_2026-10-15T07-58-07Z.json`.

Untuk form terkini, ambil snapshot liga domestik 2025/26 dan 2026/27 dari Football-Data, lalu pakai cutoff tanggal WIB:

```bash
python3 scripts/fetch_form.py
python3 -m bola.form --cutoff-date-wib 2026-10-15 --output reports/current_form.json
python3 scripts/fetch_form_extra.py
python3 -m bola.form_extra --cutoff-date-wib 2026-10-15 --output reports/current_form_extra.json
python3 scripts/fetch_fotmob_form.py
python3 -m bola.form_fotmob --cutoff-date-wib 2026-10-15 --output reports/current_form_fotmob.json
python3 scripts/fetch_fotmob_recent.py
python3 -m bola.fotmob_recent_stats --output reports/fotmob_recent_stats.json
```

Delapan belas CSV mencakup sembilan liga dalam `.cache/form/`; dua CSV lain untuk Austria dan Norwegia ada di `.cache/form_extra/`. Manifest mencatat URL, waktu pengambilan, dan SHA-256 setiap berkas. Snapshot lama tersimpan di subfolder `snapshots/` dan dapat dijalankan ulang dengan `--data-dir` yang menunjuk foldernya. Kedua pengolah hanya memasukkan hasil bertanggal **sebelum** cutoff serta menghitung jendela 5/10/20 laga, bobot waktu, pembagian kandang/tandang, gol, dan surplus hasil terhadap Elo lawan sebelum pertandingan. Statistik tembakan, corner, kartu, dan xG hanya tersedia pada liga dan baris tertentu. Elo dihitung terpisah per liga dan tidak dapat dibandingkan langsung lintas liga. Form ini tidak mencakup pertandingan UEFA atau piala domestik.

`fetch_fotmob_form.py` membekukan empat halaman liga FotMob/enet Slovakia dan Ukraina 2025/26–2026/27 dengan waktu pengambilan dan SHA-256. `bola.form_fotmob` memeriksa ID liga, musim, ID tim, status serta skor laga, menyingkirkan laga yang dibatalkan atau diputuskan administratif, dan menghitung form Shakhtar serta Slovan Bratislava. Gabungan tiga laporan form kini mencakup **18 dari 18 tim**. Halaman FotMob ini baru diambil **setelah** kickoff 15 Oktober, sehingga angka untuk dua klub tersebut adalah rekonstruksi retrospektif sebelum tanggal laga, bukan bukti informasi sudah tersedia pada saat prediksi prapertandingan. Ringkasan dan manifestnya ada di `evidence/form_fotmob_2026-10-15.json`.

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
