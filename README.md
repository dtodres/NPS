# NPS Branddi

Sistema automatizado de coleta, análise e geração de relatórios NPS (Net Promoter Score) para a Branddi, integrado com a plataforma [WeHelp](https://www.wehelpsoftware.com).

## Funcionalidades

- **Coleta automática** de respostas NPS via API WeHelp
- **Análise completa**: geral, temporal (semanal/mensal/trimestral), por touchpoint, por cliente
- **Detecção de risco de churn** baseada em scores e tendências
- **Análise de comentários** com frequência de palavras
- **Sugestões de melhoria** geradas automaticamente
- **Relatórios em HTML e Excel**
- **Gráficos**: evolução NPS, distribuição, histograma de notas, comparativo de touchpoints
- **Execução diária** via GitHub Actions

## Setup

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar credenciais no .env
cp .env.example .env
# Editar .env com suas credenciais WeHelp
```

## Uso

```bash
# Pipeline completo: coleta + análise + relatório
python main.py

# Apenas coleta de dados
python main.py --collect

# Apenas geração de relatório (usa dados já coletados)
python main.py --report

# Modo agendado (executa diariamente às 08:00)
python main.py --schedule
```

## Estrutura

```
├── main.py                  # Pipeline principal
├── src/
│   ├── wehelp_client.py     # Cliente API WeHelp
│   ├── analyzer.py          # Motor de análise NPS
│   ├── charts.py            # Geração de gráficos
│   └── report_generator.py  # Gerador HTML/Excel
├── templates/
│   └── report.html          # Template do relatório
├── reports/                  # Relatórios gerados
├── data/                     # Dados coletados (JSON)
└── .github/workflows/
    └── daily_report.yml     # GitHub Actions diário
```

## GitHub Actions

O workflow `daily_report.yml` executa diariamente às 08:00 (BRT). Configure os secrets no repositório:

- `WEHELP_CLIENT_ID`
- `WEHELP_CLIENT_SECRET`
- `WEHELP_SESSION_COOKIE`

## Métricas Analisadas

| Métrica | Descrição |
|---------|-----------|
| NPS Score | Cálculo padrão: %Promotores - %Detratores |
| Zona NPS | Excelência (75+), Qualidade (50-74), Aperfeiçoamento (0-49), Crítica (<0) |
| Tendência | Comparação temporal entre períodos |
| Risco de Churn | Alto (0-6), Médio (7-8), Baixo (9-10) |
| Taxa de Comentários | Volume e conteúdo dos feedbacks |
