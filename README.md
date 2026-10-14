# Bola: sistem analisis sepak bola yang dapat diaudit

Proyek ini melanjutkan rancangan dalam percakapan pengguna dengan bukti yang dapat dijalankan ulang. Kini tersedia baseline probabilitas 1X2, pengolah event/tracking dari laga anonim, audit xG seluruh Piala Dunia 2022, dan pemeriksa kronologi bukti skuad. Hasil ada di [RESULTS.md](RESULTS.md), sedangkan syarat target 95% ada di [AUDIT.md](AUDIT.md). Tidak ada klaim akurasi atau kesiapan 95% tanpa pengujian yang sesuai.

## Menjalankan

Memerlukan Python 3.10+ dan Git. Pakai checkout yang sudah ada di `/workspace/Bola`; tidak perlu membuat Git worktree.

```bash
cd /workspace/Bola
bash scripts/fetch_data.sh
bash scripts/fetch_tactics.sh
bash scripts/fetch_statsbomb.sh
python3 scripts/fetch_worldcup.py
bash scripts/fetch_odds.sh
python3 -m unittest discover -s tests -v
python3 -m bola.backtest --data-dir .cache/openfootball --output reports/backtest.json
python3 -m bola.backtest --league de.1 --fixed-poisson-weight 0.5 --data-dir .cache/openfootball --output reports/backtest_bundesliga.json
python3 -m bola.backtest --league nl.1 --test-seasons 2024-25 --fixed-poisson-weight 0.5 --data-dir .cache/openfootball --output reports/backtest_eredivisie.json
python3 -m bola.tactics --data-dir .cache/metrica --output reports/tactics.json
python3 -m bola.tactics --game 2 --data-dir .cache/metrica --output reports/tactics_game2.json
python3 -m bola.statsbomb --data-dir .cache/statsbomb --output reports/statsbomb.json
python3 -m bola.worldcup --data-dir .cache/statsbomb --output reports/worldcup.json
python3 -m bola.odds --scores-dir .cache/openfootball --odds-dir .cache/odds --output reports/odds_benchmark.json
```

`fetch_data.sh` mengambil [OpenFootball football.json](https://github.com/openfootball/football.json) commit `e6744429ee395bc86f247348c6184bb08d4eb361` (CC0). `fetch_tactics.sh` mengambil [Metrica Sports sample-data](https://github.com/metrica-sports/sample-data) commit `e706dd506b360d69d9d123d5b8026e7294b13996`, hanya checkout Sample Game 1 dan 2; penggunaan publik harus menyebut Metrica Sports. `fetch_statsbomb.sh` mengambil event dan lineup [StatsBomb open-data](https://github.com/statsbomb/open-data) laga 3869685 pada commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`, dengan checksum SHA-256. `fetch_worldcup.py` mengambil semua 64 laga Piala Dunia 2022 pada commit yang sama; metadata pertandingan memiliki checksum tetap dan file lain dicatat dalam manifest checksum lokal untuk verifikasi ulang. Penggunaan publik harus menyebut StatsBomb. Dataset ada di `.cache/` dan diabaikan Git; data StatsBomb seluruh turnamen sekitar 193 MB. Script tidak mengunduh ulang jika data sudah sesuai. Tidak perlu kredensial API.

`fetch_odds.sh` mengambil CSV Premier League 2024/25 dan 2025/26 dari [Football-Data](https://www.football-data.co.uk/englandm.php), dengan checksum tetap. `bola.odds` mencocokkan tepat 760 hasil pertandingan menurut tim, tanggal, dan skor sebelum membandingkan probabilitas 1X2 model dengan odds rata-rata pembukaan/penutupan yang dinormalisasi. CSV tidak menyertakan timestamp tiap kutipan odds, sehingga hasilnya adalah benchmark historis, bukan simulasi keputusan taruhan saat itu.

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
```

`bola.uefa` membaca [sitemap pertandingan Liga Champions UEFA](https://www.uefa.com/sitemap/matches/uefachampionsleague.xml) dan halaman sembilan pertandingan, lalu memeriksa pasangan tim, waktu mulai, kompetisi, status, dan matchday. `bola.uefa_squad` membaca daftar skuad resmi serta badge status pemain untuk laga yang masih berstatus Upcoming. Snapshot HTML dan checksum disimpan di `.cache/uefa`; laporan waktu pengambilan di `reports/`. Daftar skuad tidak sama dengan starting XI; badge pemain tidak mempunyai timestamp publikasi pada halaman tersebut dan tidak boleh dijadikan konfirmasi absen dalam pertandingan tertentu tanpa pemeriksaan lanjutan.

## Protokol model

- Riwayat awal 2020/21–2022/23, validasi 2023/24, lalu pengujian pada musim setelahnya. Semua laga bertanggal sama diprediksi sebelum hasil tanggal itu dimasukkan.
- OpenFootball memakai dua format skor final; keduanya dibaca. Audit menghentikan analisis jika jumlah fixture unik atau skor final tidak lengkap.
- Metrik: akurasi 1X2, Brier multiclass, log loss, RPS, ECE keyakinan 10 bin, dan bootstrap berpasangan menurut tanggal.
- Dataset adalah snapshot tanpa timestamp publikasi historis per hasil. Pemisahan tanggal mencegah penggunaan hasil laga masa depan dalam model, tetapi belum membuktikan kapan tiap data sumber tersedia.
- Model 1X2 belum memakai xG, odds, cedera, atau skuad. Prediksinya bukan analisis pasar taruhan lengkap.
