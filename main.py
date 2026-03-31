#!/usr/bin/env python3
"""
NPS Branddi - Pipeline principal de coleta e geração de relatórios.

Uso:
    python main.py              # Coleta dados + gera relatórios
    python main.py --collect    # Apenas coleta dados
    python main.py --report     # Apenas gera relatórios (usa dados existentes)
    python main.py --schedule   # Executa em modo agendado (diário às 8h)
"""

import argparse
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(__file__))

from src.wehelp_client import fetch_and_save_data
from src.report_generator import generate_reports
from src.charts import generate_all_charts
from src.analyzer import run_full_analysis


def run_pipeline(collect=True, report=True):
    """Executa o pipeline completo."""
    print("\n" + "=" * 60)
    print("  NPS BRANDDI - PIPELINE DE RELATÓRIOS")
    print("=" * 60)

    if collect:
        print("\n[ETAPA 1] Coletando dados da WeHelp...")
        try:
            fetch_and_save_data()
        except Exception as e:
            print(f"\nERRO na coleta: {e}")
            print("Verifique a configuração de autenticação no .env")
            if not report:
                return False

    if report:
        print("\n[ETAPA 2] Executando análise...")
        try:
            analysis = run_full_analysis()
            if "error" in analysis:
                print(f"\nERRO: {analysis['error']}")
                return False
        except Exception as e:
            print(f"\nERRO na análise: {e}")
            return False

        print("\n[ETAPA 3] Gerando gráficos...")
        try:
            generate_all_charts(analysis)
        except Exception as e:
            print(f"\nAVISO: Erro nos gráficos (não crítico): {e}")

        print("\n[ETAPA 4] Gerando relatórios...")
        try:
            from src.report_generator import generate_html_report, generate_excel_report
            html_path = generate_html_report(analysis)
            excel_path = generate_excel_report(analysis)
        except Exception as e:
            print(f"\nERRO na geração: {e}")
            return False

        # Resumo final
        s = analysis["summary"]
        print("\n" + "=" * 60)
        print(f"  RELATÓRIO GERADO COM SUCESSO!")
        print(f"  NPS: {s['nps_score']} | Zona: {s['zone']}")
        print(f"  Respostas: {s['total_responses']} | Clientes: {s['total_clients']}")
        print(f"  Clientes em risco: {s['high_risk_clients']}")
        print(f"  Sugestões: {s['total_suggestions']}")
        print("=" * 60 + "\n")

    return True


def run_scheduled():
    """Executa em modo agendado."""
    import schedule
    import time

    print("Modo agendado ativado. Execução diária às 08:00.")
    print("Pressione Ctrl+C para parar.\n")

    # Executa imediatamente na primeira vez
    run_pipeline()

    # Agenda execução diária
    schedule.every().day.at("08:00").do(run_pipeline)

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="NPS Branddi - Relatórios de NPS")
    parser.add_argument("--collect", action="store_true", help="Apenas coleta dados")
    parser.add_argument("--report", action="store_true", help="Apenas gera relatórios")
    parser.add_argument("--schedule", action="store_true", help="Modo agendado (diário)")
    args = parser.parse_args()

    if args.schedule:
        run_scheduled()
    elif args.collect:
        run_pipeline(collect=True, report=False)
    elif args.report:
        run_pipeline(collect=False, report=True)
    else:
        run_pipeline(collect=True, report=True)


if __name__ == "__main__":
    main()
