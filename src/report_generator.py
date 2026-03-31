"""Gerador de relatórios NPS em HTML e Excel."""

import os
import json
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
import pandas as pd

from .analyzer import run_full_analysis, responses_to_dataframe, load_data


def generate_html_report(analysis, output_dir="reports"):
    """Gera relatório HTML a partir da análise."""
    os.makedirs(output_dir, exist_ok=True)

    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report.html")

    html = template.render(
        company_name=analysis["company"]["name"],
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
        overall=analysis["overall"],
        summary=analysis["summary"],
        temporal=analysis["temporal"],
        by_touchpoint=analysis["by_touchpoint"],
        by_client=analysis["by_client"],
        comments=analysis["comments"],
        suggestions=analysis["suggestions"],
    )

    timestamp = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(output_dir, f"nps_report_{timestamp}.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    # Também salva como latest
    latest_path = os.path.join(output_dir, "nps_report_latest.html")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Relatório HTML gerado: {filepath}")
    return filepath


def generate_excel_report(analysis, output_dir="reports"):
    """Gera relatório Excel com múltiplas abas."""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(output_dir, f"nps_report_{timestamp}.xlsx")

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        # Aba: Resumo
        summary_data = {
            "Métrica": [
                "NPS Score", "Zona", "Total Respostas", "Clientes Únicos",
                "Promotores", "Passivos", "Detratores",
                "% Promotores", "% Passivos", "% Detratores",
                "Clientes em Risco", "Touchpoints Ativos",
            ],
            "Valor": [
                analysis["overall"].get("score"),
                analysis["overall"].get("zone"),
                analysis["summary"]["total_responses"],
                analysis["summary"]["total_clients"],
                analysis["overall"].get("promoters"),
                analysis["overall"].get("passives"),
                analysis["overall"].get("detractors"),
                analysis["overall"].get("pct_promoters"),
                analysis["overall"].get("pct_passives"),
                analysis["overall"].get("pct_detractors"),
                analysis["summary"]["high_risk_clients"],
                analysis["summary"]["active_touchpoints"],
            ],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Resumo", index=False)

        # Aba: Evolução Mensal
        if analysis["temporal"]["monthly"]:
            df_monthly = pd.DataFrame(analysis["temporal"]["monthly"])
            cols = ["period", "score", "total", "promoters", "passives", "detractors", "zone"]
            available = [c for c in cols if c in df_monthly.columns]
            df_monthly[available].to_excel(writer, sheet_name="Evolução Mensal", index=False)

        # Aba: Por Touchpoint
        if analysis["by_touchpoint"]:
            df_tp = pd.DataFrame(analysis["by_touchpoint"])
            cols = ["touchpoint", "score", "total", "promoters", "passives", "detractors", "zone"]
            available = [c for c in cols if c in df_tp.columns]
            df_tp[available].to_excel(writer, sheet_name="Por Touchpoint", index=False)

        # Aba: Por Cliente
        if analysis["by_client"]:
            df_clients = pd.DataFrame(analysis["by_client"])
            cols = [
                "client_name", "score", "total_responses", "promoters", "passives",
                "detractors", "trend", "churn_risk", "first_response", "last_response",
            ]
            available = [c for c in cols if c in df_clients.columns]
            df_clients[available].to_excel(writer, sheet_name="Por Cliente", index=False)

        # Aba: Comentários
        recent = analysis["comments"].get("recent_comments", [])
        if recent:
            df_comments = pd.DataFrame(recent)
            df_comments.to_excel(writer, sheet_name="Comentários", index=False)

        # Aba: Sugestões
        if analysis["suggestions"]:
            df_sug = pd.DataFrame(analysis["suggestions"])
            df_sug.to_excel(writer, sheet_name="Sugestões", index=False)

    print(f"Relatório Excel gerado: {filepath}")
    return filepath


def generate_reports(data_dir="data", output_dir="reports"):
    """Pipeline completo: análise + geração de relatórios."""
    print("\n" + "=" * 60)
    print("  GERAÇÃO DE RELATÓRIO NPS - BRANDDI")
    print("=" * 60 + "\n")

    # Executa análise
    analysis = run_full_analysis(data_dir)
    if "error" in analysis:
        print(f"ERRO: {analysis['error']}")
        return None

    # Gera relatórios
    html_path = generate_html_report(analysis, output_dir)
    excel_path = generate_excel_report(analysis, output_dir)

    print(f"\n{'=' * 60}")
    print(f"  NPS: {analysis['summary']['nps_score']} ({analysis['summary']['zone']})")
    print(f"  Relatórios salvos em: {output_dir}/")
    print(f"{'=' * 60}\n")

    return {"html": html_path, "excel": excel_path, "analysis": analysis}


if __name__ == "__main__":
    generate_reports()
