"""Render an auditable analyst JSON report as a readable Markdown brief."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


GATE_LABELS = {
    "before_kickoff": "Waktu analisis sebelum kickoff",
    "official_fixture_upcoming": "Fixture resmi masih upcoming",
    "official_fixture_snapshot_within_30m": "Snapshot fixture berumur maksimal 30 menit",
    "domestic_form_5_10_20_for_both": "Form liga 5/10/20 tersedia untuk kedua tim",
    "domestic_form_snapshot_within_24h": "Form diperbarui dalam 24 jam",
    "schedule_load_for_both": "Jadwal kedua tim tersedia",
    "schedule_snapshot_within_24h": "Jadwal diperbarui dalam 24 jam",
    "recent_match_stats_for_both": "Statistik terbaru tersedia untuk kedua tim",
    "recent_stats_snapshot_within_24h": "Statistik terbaru diperbarui dalam 24 jam",
    "registered_squad_for_both": "Skuad terdaftar tersedia untuk kedua tim",
    "registered_squad_snapshot_within_24h": "Snapshot skuad diperbarui dalam 24 jam",
    "official_starting_xi_before_kickoff": "XI resmi diumumkan sebelum kickoff",
    "fresh_market_screenshot": "Bukti odds 1X2 bertimestamp masih segar",
    "validated_current_tactical_evidence": "Bukti taktik target tervalidasi",
    "model_validated_against_current_market": "Model tervalidasi terhadap pasar saat ini",
}

LIMITATION_LABELS = {
    "Domestic form is descriptive and is not an input to the frozen UEFA probability model.":
        "Form domestik bersifat deskriptif dan tidak menjadi input model probabilitas UEFA yang dibekukan.",
    "Player badges do not prove match-specific absence, injury severity, or starting status.":
        "Badge pemain tidak membuktikan absensi untuk laga ini, tingkat cedera, atau status starter.",
    "Schedule load counts team fixtures but does not measure player minutes, travel, sleep, or fatigue.":
        "Beban jadwal menghitung pertandingan tim, bukan menit bermain, perjalanan, tidur, atau kelelahan pemain.",
    "Recent match statistics are descriptive, come from one provider, and are not a validated tactical model.":
        "Statistik laga terbaru bersifat deskriptif, berasal dari satu penyedia, dan bukan model taktik tervalidasi.",
    "No current tactical feature has passed a predictive holdout test.":
        "Belum ada fitur taktik saat ini yang lulus uji prediksi holdout.",
    "The results-only UEFA model has not demonstrated a stable edge over current market prices.":
        "Model UEFA berbasis hasil saja belum menunjukkan keunggulan stabil atas harga pasar saat ini.",
}


def _counts(values: dict | None) -> str:
    if not values:
        return "belum tersedia"
    return ", ".join(f"{team}: {count}" for team, count in values.items())


def _form_line(form: dict | None) -> str:
    if not form:
        return "belum tersedia"
    parts = []
    for size in (5, 10, 20):
        window = form.get("windows", {}).get(str(size))
        if not window:
            parts.append(f"{size}: —")
            continue
        record = window.get("record", {})
        parts.append(f"{size}: {record.get('W', '—')}-{record.get('D', '—')}-{record.get('L', '—')}")
    five = form.get("windows", {}).get("5", {})
    if five and five.get("goals_for_per_game") is not None:
        goals_against = five.get("goals_against_per_game")
        if goals_against is not None:
            parts.append(f"GF/GA 5 laga: {five['goals_for_per_game']:.2f}/{goals_against:.2f}")
    return "; ".join(parts)


def _stat_line(recent: dict | None) -> str:
    if not recent:
        return "belum tersedia"
    averages = recent.get("averages", {}).get("All", {})
    names = (("shots", "tembakan"), ("shots_on_target", "tepat sasaran"),
             ("big_chances", "peluang besar"), ("corners", "corner"))
    values = []
    for metric, label in names:
        item = averages.get(metric)
        if item and item.get("observed_games", 0) > 0:
            values.append(f"{label} {item['team_mean']:.1f} vs {item['opponent_mean']:.1f} ({item['observed_games']} laga)")
    stats_count = recent.get("stats_available_games", 0)
    lineup_count = recent.get("lineup_available_games", 0)
    detail = ", ".join(values) if values else "metrik ringkas tidak tersedia"
    return f"statistik {stats_count}/5 laga; lineup historis {lineup_count}/5; {detail}"


def render(report: dict) -> str:
    """Return an evidence-first brief; never turn exploratory probabilities into picks."""
    matches = report.get("matches")
    if not isinstance(matches, list):
        raise ValueError("Analyst report must contain a matches list")
    summary = report.get("summary", {})
    lines = [
        "# Ringkasan analisis prapertandingan",
        "",
        f"- Dibuat: {report.get('generated_at', 'tidak tercatat')}",
        f"- Tanggal target UTC: {report.get('target_date_utc', 'tidak tercatat')}",
        f"- Laga: {summary.get('matches', len(matches))}; perlu ditinjau: {summary.get('eligible_for_review', 0)}; `no_selection`: {summary.get('no_selection', 0)}",
        "",
        "Peluang yang ditampilkan bersifat eksploratif. `no_selection` berarti sedikitnya satu gerbang wajib belum lulus; jangan perlakukan peluang sebagai rekomendasi taruhan.",
    ]
    for match in matches:
        probabilities = match.get("probabilities_h_d_a_exploratory") or []
        if len(probabilities) == 3:
            probability_text = " / ".join(f"{value * 100:.1f}%" for value in probabilities)
        else:
            probability_text = "tidak tersedia"
        lines.extend(("", f"## {match.get('home', '?')} vs {match.get('away', '?')}", "",
                      f"- Kickoff: {match.get('kickoff', 'tidak tercatat')} UTC; match ID: `{match.get('match_id', '—')}`",
                      f"- Peluang eksploratif 1X2 (kandang / seri / tandang): {probability_text}"))
        forms = match.get("form") or {}
        for team in (match.get("home"), match.get("away")):
            if not team:
                continue
            schedule = (match.get("schedule_load") or {}).get(team) or {}
            recent = (match.get("recent_match_stats") or {}).get(team)
            form_data = forms.get(team)
            form_source_time = ((form_data or {}).get("source") or {}).get("retrieved_at_latest")
            form_time_text = f"; form diambil {form_source_time}" if form_source_time else ""
            lines.append(f"- **{team}:** form {_form_line(form_data)}{form_time_text}; {_stat_line(recent)}")
            if schedule:
                upcoming = schedule.get("scheduled_matches_before_target", 0)
                rest = schedule.get("projected_hours_from_preceding_fixture_to_target")
                rest_text = f"; istirahat terproyeksi {rest:.1f} jam" if isinstance(rest, (int, float)) else ""
                schedule_time = schedule.get("source_retrieved_at")
                schedule_time_text = f"; sumber diambil {schedule_time}" if schedule_time else ""
                lines.append(f"  - Jadwal: {schedule.get('completed_in_previous_14_days', 0)} laga selesai dalam 14 hari; {upcoming} laga terjadwal sebelum target{rest_text}{schedule_time_text}.")
        squad_counts = match.get("registered_players") or {}
        badge_counts = match.get("flagged_player_counts") or {}
        lines.append(f"- Skuad terdaftar: {_counts(squad_counts)}; badge UEFA tercatat: {_counts(badge_counts)}.")
        lines.append(f"- XI resmi: {match.get('lineup_status', 'belum diperiksa')}; waktu snapshot skuad: {match.get('squad_retrieved_at') or 'tidak tercatat'}.")
        market = match.get("market")
        if market:
            lines.append(f"- Snapshot pasar: bookmaker {market.get('bookmaker', 'tidak tercatat')}; diamati {market.get('quote_observed_at_transcribed', 'tidak tercatat')}.")
        else:
            lines.append("- Snapshot pasar bertimestamp: tidak tersedia.")
        blockers = match.get("blocking_gates") or []
        if blockers:
            labels = [GATE_LABELS.get(name, name) for name in blockers]
            lines.append("- Gerbang yang menghambat: " + "; ".join(labels) + ".")
        lines.append(f"- Status: **{match.get('selection_status', 'no_selection')}**.")
    limitations = report.get("limitations") or []
    if limitations:
        lines.extend(("", "## Batasan", ""))
        lines.extend(f"- {LIMITATION_LABELS.get(limitation, limitation)}" for limitation in limitations)
    provenance = report.get("input_sha256") or {}
    if provenance or report.get("schedule_input_sha256") or report.get("recent_stats_input_sha256"):
        lines.extend(("", "## Jejak input", ""))
        for name, digest in sorted(provenance.items()):
            lines.append(f"- {name}: SHA-256 `{digest}`")
        if report.get("schedule_input_sha256"):
            lines.append(f"- schedule: SHA-256 `{report['schedule_input_sha256']}`")
        if report.get("recent_stats_input_sha256"):
            lines.append(f"- recent_stats: SHA-256 `{report['recent_stats_input_sha256']}`")
        for index, digest in enumerate(report.get("market_input_sha256") or [], start=1):
            lines.append(f"- market {index}: SHA-256 `{digest}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="JSON produced by bola.analyst_report")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    markdown = render(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
