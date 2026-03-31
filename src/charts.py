"""Geração de gráficos para o relatório NPS."""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime

sns.set_theme(style="whitegrid")

COLORS = {
    "promoter": "#2ecc71",
    "passive": "#f39c12",
    "detractor": "#e74c3c",
    "primary": "#1a1a2e",
    "accent": "#0f3460",
}


def plot_nps_evolution(temporal_data, output_dir="reports/charts"):
    """Gráfico de evolução do NPS ao longo do tempo."""
    os.makedirs(output_dir, exist_ok=True)

    if not temporal_data:
        return None

    periods = [d["period"] for d in temporal_data]
    scores = [d["score"] for d in temporal_data]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(periods, scores, marker="o", linewidth=2.5, color=COLORS["primary"], markersize=8)
    ax.fill_between(periods, scores, alpha=0.1, color=COLORS["accent"])

    # Zonas NPS
    ax.axhspan(75, 100, alpha=0.05, color=COLORS["promoter"], label="Excelência")
    ax.axhspan(50, 75, alpha=0.05, color="#3498db", label="Qualidade")
    ax.axhspan(0, 50, alpha=0.05, color=COLORS["passive"], label="Aperfeiçoamento")
    ax.axhspan(-100, 0, alpha=0.05, color=COLORS["detractor"], label="Crítica")

    for i, (p, s) in enumerate(zip(periods, scores)):
        ax.annotate(f"{s}", (p, s), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontweight="bold", fontsize=10)

    ax.set_ylabel("NPS Score", fontsize=12)
    ax.set_title("Evolução do NPS ao Longo do Tempo", fontsize=14, fontweight="bold")
    ax.set_ylim(-10, 105)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    path = os.path.join(output_dir, "nps_evolution.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def plot_distribution(overall, output_dir="reports/charts"):
    """Gráfico de distribuição promotores/passivos/detratores."""
    os.makedirs(output_dir, exist_ok=True)

    labels = ["Promotores", "Passivos", "Detratores"]
    sizes = [
        overall.get("pct_promoters", 0),
        overall.get("pct_passives", 0),
        overall.get("pct_detractors", 0),
    ]
    colors = [COLORS["promoter"], COLORS["passive"], COLORS["detractor"]]
    counts = [overall.get("promoters", 0), overall.get("passives", 0), overall.get("detractors", 0)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Donut chart
    wedges, texts, autotexts = ax1.pie(
        sizes, labels=labels, colors=colors, autopct="%1.1f%%",
        startangle=90, pctdistance=0.75, wedgeprops=dict(width=0.4)
    )
    for t in autotexts:
        t.set_fontweight("bold")
    ax1.set_title("Distribuição NPS", fontsize=14, fontweight="bold")

    # Bar chart com contagens
    bars = ax2.bar(labels, counts, color=colors, width=0.6, edgecolor="white", linewidth=1.5)
    for bar, count in zip(bars, counts):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 str(count), ha="center", fontweight="bold", fontsize=12)
    ax2.set_ylabel("Quantidade", fontsize=12)
    ax2.set_title("Contagem por Categoria", fontsize=14, fontweight="bold")

    plt.tight_layout()
    path = os.path.join(output_dir, "nps_distribution.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def plot_score_histogram(score_distribution, output_dir="reports/charts"):
    """Histograma de notas (0-10)."""
    os.makedirs(output_dir, exist_ok=True)

    if not score_distribution:
        return None

    scores = list(range(11))
    counts = [score_distribution.get(s, 0) for s in scores]
    colors = [
        COLORS["detractor"] if s <= 6 else COLORS["passive"] if s <= 8 else COLORS["promoter"]
        for s in scores
    ]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(scores, counts, color=colors, width=0.7, edgecolor="white", linewidth=1.5)

    for bar, count in zip(bars, counts):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                    str(count), ha="center", fontweight="bold")

    ax.set_xlabel("Nota", fontsize=12)
    ax.set_ylabel("Quantidade", fontsize=12)
    ax.set_title("Distribuição de Notas NPS (0-10)", fontsize=14, fontweight="bold")
    ax.set_xticks(scores)

    plt.tight_layout()
    path = os.path.join(output_dir, "score_histogram.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def plot_touchpoint_comparison(by_touchpoint, output_dir="reports/charts"):
    """Gráfico comparativo de NPS por touchpoint."""
    os.makedirs(output_dir, exist_ok=True)

    if not by_touchpoint:
        return None

    # Filtra touchpoints com respostas suficientes
    data = [tp for tp in by_touchpoint if tp.get("total", 0) >= 2]
    if not data:
        return None

    names = [tp["touchpoint"][:30] for tp in data]
    scores = [tp["score"] for tp in data]
    colors = [
        COLORS["promoter"] if s >= 75 else "#3498db" if s >= 50
        else COLORS["passive"] if s >= 0 else COLORS["detractor"]
        for s in scores
    ]

    fig, ax = plt.subplots(figsize=(10, max(4, len(names) * 0.5)))
    bars = ax.barh(names, scores, color=colors, height=0.6, edgecolor="white")

    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{score}", va="center", fontweight="bold")

    ax.set_xlabel("NPS Score", fontsize=12)
    ax.set_title("NPS por Touchpoint", fontsize=14, fontweight="bold")
    ax.set_xlim(-10, 105)
    ax.invert_yaxis()

    plt.tight_layout()
    path = os.path.join(output_dir, "touchpoint_comparison.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def generate_all_charts(analysis, output_dir="reports/charts"):
    """Gera todos os gráficos do relatório."""
    print("Gerando gráficos...")
    charts = {}

    charts["evolution"] = plot_nps_evolution(
        analysis["temporal"]["monthly"], output_dir
    )
    charts["distribution"] = plot_distribution(analysis["overall"], output_dir)
    charts["histogram"] = plot_score_histogram(
        analysis["overall"].get("score_distribution", {}), output_dir
    )
    charts["touchpoints"] = plot_touchpoint_comparison(
        analysis["by_touchpoint"], output_dir
    )

    generated = {k: v for k, v in charts.items() if v}
    print(f"  {len(generated)} gráficos gerados em {output_dir}/")
    return charts
