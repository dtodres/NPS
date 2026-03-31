"""Módulo de análise de dados NPS da Branddi."""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

import pandas as pd
import numpy as np


def load_data(data_dir="data"):
    """Carrega dados salvos dos JSONs."""
    datasets = {}
    for filename in os.listdir(data_dir):
        if filename.endswith(".json") and filename != "metadata.json":
            name = filename.replace(".json", "")
            with open(os.path.join(data_dir, filename), "r", encoding="utf-8") as f:
                datasets[name] = json.load(f)
    return datasets


def responses_to_dataframe(responses):
    """Converte respostas NPS em DataFrame estruturado."""
    rows = []
    for r in responses:
        person = r.get("person", {})
        base = {
            "response_id": r.get("id"),
            "person_name": person.get("name", "Anônimo"),
            "person_id": person.get("personId", ""),
            "customer_since": person.get("customerSince"),
            "gender": person.get("gender"),
            "replied_at": r.get("repliedAt"),
            "created_at": r.get("createdAt"),
            "status": r.get("status"),
            "survey_destination": r.get("survey", {}).get("destination"),
            "survey_group_id": r.get("survey", {}).get("groupId"),
            "channel": r.get("answeredTrace", {}).get("channel", ""),
        }

        forms = r.get("forms", [])
        for form in forms:
            nps_data = form.get("nps", {})
            row = {
                **base,
                "touchpoint_id": form.get("touchpointId"),
                "touchpoint_name": form.get("touchpointName", ""),
                "form_type": form.get("formType", ""),
                "nps_score": nps_data.get("evaluation"),
                "nps_status": nps_data.get("status"),  # PROMOTER, PASSIVE, DETRACTOR
                "comment": form.get("comment", ""),
            }
            rows.append(row)

        # Se não tem forms, adiciona o registro base
        if not forms:
            rows.append({**base, "touchpoint_id": None, "touchpoint_name": "",
                         "form_type": "", "nps_score": None, "nps_status": None, "comment": ""})

    df = pd.DataFrame(rows)

    # Conversão de datas
    for col in ["replied_at", "created_at", "customer_since"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    return df


def calculate_nps(scores):
    """Calcula NPS a partir de uma série de scores (0-10)."""
    if len(scores) == 0:
        return {"score": None, "total": 0, "promoters": 0, "passives": 0, "detractors": 0}

    valid = scores.dropna()
    if len(valid) == 0:
        return {"score": None, "total": 0, "promoters": 0, "passives": 0, "detractors": 0}

    promoters = (valid >= 9).sum()
    passives = ((valid >= 7) & (valid < 9)).sum()
    detractors = (valid < 7).sum()
    total = len(valid)
    score = round(((promoters - detractors) / total) * 100, 2)

    return {
        "score": score,
        "total": total,
        "promoters": int(promoters),
        "passives": int(passives),
        "detractors": int(detractors),
        "pct_promoters": round(promoters / total * 100, 1),
        "pct_passives": round(passives / total * 100, 1),
        "pct_detractors": round(detractors / total * 100, 1),
    }


def nps_zone(score):
    """Retorna a zona do NPS."""
    if score is None:
        return "Sem dados"
    if score >= 75:
        return "Excelência"
    if score >= 50:
        return "Qualidade"
    if score >= 0:
        return "Aperfeiçoamento"
    return "Crítica"


def nps_zone_color(score):
    """Retorna cor CSS para a zona NPS."""
    if score is None:
        return "#999"
    if score >= 75:
        return "#2ecc71"
    if score >= 50:
        return "#3498db"
    if score >= 0:
        return "#f39c12"
    return "#e74c3c"


def analyze_overall(df):
    """Análise geral do NPS."""
    nps = calculate_nps(df["nps_score"])
    nps["zone"] = nps_zone(nps["score"])
    nps["zone_color"] = nps_zone_color(nps["score"])

    # Distribuição de scores
    if not df["nps_score"].dropna().empty:
        dist = df["nps_score"].dropna().value_counts().sort_index()
        nps["score_distribution"] = {int(k): int(v) for k, v in dist.items()}
    else:
        nps["score_distribution"] = {}

    # Taxa de resposta
    nps["response_rate"] = None  # Precisa do total de enviados

    return nps


def analyze_temporal(df, period="M"):
    """Análise temporal do NPS por período (M=mensal, W=semanal, Q=trimestral)."""
    if df.empty or df["replied_at"].isna().all():
        return []

    df_sorted = df.dropna(subset=["replied_at"]).copy()
    df_sorted["period"] = df_sorted["replied_at"].dt.to_period(period)

    results = []
    for period_val, group in df_sorted.groupby("period"):
        nps = calculate_nps(group["nps_score"])
        nps["period"] = str(period_val)
        nps["period_start"] = period_val.start_time.strftime("%Y-%m-%d")
        nps["period_end"] = period_val.end_time.strftime("%Y-%m-%d")
        nps["zone"] = nps_zone(nps["score"])
        results.append(nps)

    return results


def analyze_by_touchpoint(df):
    """Análise por touchpoint (ponto de contato)."""
    results = []
    for tp_name, group in df.groupby("touchpoint_name"):
        if not tp_name:
            continue
        nps = calculate_nps(group["nps_score"])
        nps["touchpoint"] = tp_name
        nps["zone"] = nps_zone(nps["score"])
        nps["comments"] = group["comment"].dropna().tolist()
        nps["comments"] = [c for c in nps["comments"] if c.strip()]
        results.append(nps)

    return sorted(results, key=lambda x: x.get("score") or -999, reverse=True)


def analyze_by_client(df):
    """Análise detalhada por cliente."""
    results = []
    for person_id, group in df.groupby("person_id"):
        if not person_id:
            continue
        person_name = group["person_name"].iloc[0]
        nps = calculate_nps(group["nps_score"])
        nps["client_name"] = person_name
        nps["client_id"] = person_id
        nps["total_responses"] = len(group)
        nps["first_response"] = group["replied_at"].min()
        nps["last_response"] = group["replied_at"].max()
        nps["comments"] = [c for c in group["comment"].dropna().tolist() if c.strip()]

        # Tendência: última nota vs primeira
        scores = group.sort_values("replied_at")["nps_score"].dropna()
        if len(scores) >= 2:
            nps["trend"] = "up" if scores.iloc[-1] > scores.iloc[0] else (
                "down" if scores.iloc[-1] < scores.iloc[0] else "stable"
            )
        else:
            nps["trend"] = "stable"

        # Classifica risco de churn
        last_score = scores.iloc[-1] if len(scores) > 0 else None
        if last_score is not None:
            if last_score <= 6:
                nps["churn_risk"] = "Alto"
            elif last_score <= 8:
                nps["churn_risk"] = "Médio"
            else:
                nps["churn_risk"] = "Baixo"
        else:
            nps["churn_risk"] = "Indeterminado"

        results.append(nps)

    return sorted(results, key=lambda x: x.get("score") or -999, reverse=True)


def analyze_comments(df):
    """Análise de comentários - extrai temas e sentimentos."""
    comments = df[["comment", "nps_score", "nps_status", "person_name", "touchpoint_name", "replied_at"]].copy()
    comments = comments[comments["comment"].notna() & (comments["comment"].str.strip() != "")]

    if comments.empty:
        return {"total_comments": 0, "comments_by_status": {}, "recent_comments": []}

    result = {
        "total_comments": len(comments),
        "comments_by_status": {},
        "recent_comments": [],
        "word_frequency": {},
    }

    # Comentários por status NPS
    for status in ["PROMOTER", "PASSIVE", "DETRACTOR"]:
        status_comments = comments[comments["nps_status"] == status]
        result["comments_by_status"][status] = {
            "count": len(status_comments),
            "comments": status_comments[["comment", "person_name", "nps_score", "touchpoint_name"]].to_dict("records"),
        }

    # Comentários mais recentes
    recent = comments.sort_values("replied_at", ascending=False).head(20)
    result["recent_comments"] = recent[
        ["comment", "person_name", "nps_score", "nps_status", "touchpoint_name", "replied_at"]
    ].to_dict("records")

    # Frequência de palavras (simples)
    stopwords_pt = {
        "a", "o", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
        "um", "uma", "que", "para", "com", "por", "se", "não", "mais", "muito", "como",
        "é", "são", "foi", "ser", "ter", "está", "eu", "ele", "ela", "nós", "eles",
        "me", "meu", "minha", "seu", "sua", "nos", "ao", "aos", "às", "os", "as",
    }
    all_text = " ".join(comments["comment"].str.lower())
    words = [w.strip(".,!?;:()\"'") for w in all_text.split() if len(w) > 2]
    words = [w for w in words if w and w not in stopwords_pt]
    freq = defaultdict(int)
    for w in words:
        freq[w] += 1
    result["word_frequency"] = dict(sorted(freq.items(), key=lambda x: x[1], reverse=True)[:30])

    return result


def generate_suggestions(overall, temporal, by_touchpoint, by_client, comments_analysis):
    """Gera sugestões de melhoria baseadas nos dados."""
    suggestions = []

    # Baseado no NPS geral
    score = overall.get("score")
    if score is not None:
        if score >= 75:
            suggestions.append({
                "category": "Geral",
                "priority": "Média",
                "title": "Manter excelência e expandir base de promotores",
                "description": (
                    f"Com NPS de {score}, a Branddi está na Zona de Excelência. "
                    "Recomenda-se criar um programa de indicação (referral) aproveitando "
                    "a alta satisfação dos clientes promotores para gerar novos negócios."
                ),
            })
        elif score >= 50:
            suggestions.append({
                "category": "Geral",
                "priority": "Alta",
                "title": "Converter passivos em promotores",
                "description": (
                    f"NPS de {score} indica qualidade, mas há espaço para melhoria. "
                    "Foco em entender o que impede os passivos de se tornarem promotores."
                ),
            })
        else:
            suggestions.append({
                "category": "Geral",
                "priority": "Crítica",
                "title": "Plano de ação urgente para detratores",
                "description": (
                    f"NPS de {score} requer ação imediata. Implementar follow-up "
                    "individual com cada detrator dentro de 24h."
                ),
            })

    # Baseado na evolução temporal
    if len(temporal) >= 2:
        recent = temporal[-1].get("score", 0) or 0
        previous = temporal[-2].get("score", 0) or 0
        if recent < previous:
            suggestions.append({
                "category": "Tendência",
                "priority": "Alta",
                "title": "NPS em queda - investigar causas",
                "description": (
                    f"O NPS caiu de {previous} para {recent} no último período. "
                    "Recomenda-se entrevistas qualitativas com clientes que deram notas "
                    "mais baixas recentemente para identificar a causa raiz."
                ),
            })
        elif recent > previous:
            suggestions.append({
                "category": "Tendência",
                "priority": "Baixa",
                "title": "NPS em alta - documentar boas práticas",
                "description": (
                    f"NPS subiu de {previous} para {recent}. Documentar as ações "
                    "que levaram à melhoria para replicar em outras áreas."
                ),
            })

    # Baseado em touchpoints
    low_touchpoints = [tp for tp in by_touchpoint if (tp.get("score") or 0) < 50 and tp.get("total", 0) >= 3]
    if low_touchpoints:
        tp_names = ", ".join([tp["touchpoint"] for tp in low_touchpoints[:3]])
        suggestions.append({
            "category": "Touchpoints",
            "priority": "Alta",
            "title": "Pontos de contato com baixa satisfação",
            "description": (
                f"Os touchpoints '{tp_names}' apresentam NPS abaixo de 50. "
                "Recomenda-se mapear a jornada do cliente nesses pontos e "
                "identificar gargalos específicos."
            ),
        })

    # Baseado em clientes
    high_risk = [c for c in by_client if c.get("churn_risk") == "Alto"]
    if high_risk:
        suggestions.append({
            "category": "Retenção",
            "priority": "Crítica",
            "title": f"{len(high_risk)} cliente(s) com alto risco de churn",
            "description": (
                "Clientes detratores devem receber contato proativo imediato. "
                "Sugestão: criar um fluxo de recuperação com ligação do CS em até 24h, "
                "oferta de reunião de alinhamento e plano de ação personalizado."
            ),
        })

    declining = [c for c in by_client if c.get("trend") == "down"]
    if declining:
        suggestions.append({
            "category": "Retenção",
            "priority": "Alta",
            "title": f"{len(declining)} cliente(s) com tendência de queda",
            "description": (
                "Mesmo clientes com notas ainda altas mas em tendência de queda "
                "merecem atenção preventiva. Agendar check-ins proativos."
            ),
        })

    # Baseado nos comentários
    detractor_comments = comments_analysis.get("comments_by_status", {}).get("DETRACTOR", {})
    if detractor_comments.get("count", 0) > 0:
        suggestions.append({
            "category": "Feedback",
            "priority": "Alta",
            "title": "Análise profunda de comentários de detratores",
            "description": (
                f"Existem {detractor_comments['count']} comentários de detratores. "
                "Recomenda-se categorizar os temas recorrentes e criar planos de ação "
                "específicos para cada tema identificado."
            ),
        })

    # Sugestões gerais de campanhas
    pct_passives = overall.get("pct_passives", 0)
    if pct_passives and pct_passives > 15:
        suggestions.append({
            "category": "Campanhas",
            "priority": "Média",
            "title": "Campanha de engajamento para passivos",
            "description": (
                f"Com {pct_passives}% de passivos, há oportunidade significativa. "
                "Criar campanha de 'surprise & delight' - pequenas ações inesperadas "
                "que encantem: envio de cases de sucesso personalizados, convites para "
                "eventos exclusivos, ou acesso antecipado a novos recursos."
            ),
        })

    suggestions.append({
        "category": "Campanhas",
        "priority": "Média",
        "title": "Programa de advocacy com promotores",
        "description": (
            "Promotores são o maior ativo de marketing. Sugestões: "
            "(1) Programa de indicação com benefícios; "
            "(2) Coleta de depoimentos e cases de sucesso; "
            "(3) Convite para co-criação de conteúdo; "
            "(4) Grupo exclusivo de clientes VIP."
        ),
    })

    suggestions.append({
        "category": "Processo",
        "priority": "Média",
        "title": "Implementar closed-loop feedback",
        "description": (
            "Garantir que 100% das respostas NPS recebam follow-up: "
            "Detratores em até 24h (ligação), Passivos em até 48h (email personalizado), "
            "Promotores em até 1 semana (agradecimento + convite para advocacy)."
        ),
    })

    return suggestions


def run_full_analysis(data_dir="data"):
    """Executa análise completa e retorna todos os resultados."""
    datasets = load_data(data_dir)
    responses = datasets.get("responses", [])

    if not responses:
        return {"error": "Nenhuma resposta encontrada. Execute a coleta de dados primeiro."}

    df = responses_to_dataframe(responses)

    print(f"Analisando {len(df)} registros de {df['person_id'].nunique()} clientes...")

    overall = analyze_overall(df)
    temporal_monthly = analyze_temporal(df, "M")
    temporal_weekly = analyze_temporal(df, "W")
    temporal_quarterly = analyze_temporal(df, "Q")
    by_touchpoint = analyze_by_touchpoint(df)
    by_client = analyze_by_client(df)
    comments = analyze_comments(df)
    suggestions = generate_suggestions(overall, temporal_monthly, by_touchpoint, by_client, comments)

    # Metadata
    company = datasets.get("company", {})
    touchpoints = datasets.get("touchpoints", [])

    analysis = {
        "generated_at": datetime.now().isoformat(),
        "company": {
            "name": company.get("name", company.get("dba", "Branddi")),
            "total_touchpoints": len(touchpoints) if isinstance(touchpoints, list) else 0,
        },
        "overall": overall,
        "temporal": {
            "monthly": temporal_monthly,
            "weekly": temporal_weekly,
            "quarterly": temporal_quarterly,
        },
        "by_touchpoint": by_touchpoint,
        "by_client": by_client,
        "comments": comments,
        "suggestions": suggestions,
        "summary": {
            "total_responses": overall.get("total", 0),
            "total_clients": df["person_id"].nunique(),
            "nps_score": overall.get("score"),
            "zone": overall.get("zone"),
            "high_risk_clients": len([c for c in by_client if c.get("churn_risk") == "Alto"]),
            "active_touchpoints": len(by_touchpoint),
            "total_comments": comments.get("total_comments", 0),
            "total_suggestions": len(suggestions),
        },
    }

    # Salva análise
    os.makedirs("data", exist_ok=True)
    with open(os.path.join(data_dir, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)

    print(f"Análise completa salva em {data_dir}/analysis.json")
    return analysis


if __name__ == "__main__":
    result = run_full_analysis()
    if "error" not in result:
        s = result["summary"]
        print(f"\n{'='*50}")
        print(f"NPS Branddi: {s['nps_score']} ({s['zone']})")
        print(f"Respostas: {s['total_responses']} | Clientes: {s['total_clients']}")
        print(f"Risco de churn: {s['high_risk_clients']} clientes")
        print(f"Sugestões geradas: {s['total_suggestions']}")
        print(f"{'='*50}")
