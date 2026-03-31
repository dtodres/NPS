"""Cliente para a API da WeHelp - coleta de dados NPS."""

import os
import time
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("WEHELP_BASE_URL", "https://app.wehelpsoftware.com")
SESSION_COOKIE = os.getenv("WEHELP_SESSION_COOKIE", "")
CLIENT_ID = os.getenv("WEHELP_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("WEHELP_CLIENT_SECRET", "")


class WeHelpClient:
    """Cliente para API interna da WeHelp."""

    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self._setup_auth()

    def _setup_auth(self):
        """Configura autenticação - tenta v2 API primeiro, depois session cookie."""
        # Tenta API v2 com client credentials
        if CLIENT_ID and CLIENT_SECRET:
            try:
                resp = self.session.post(
                    f"{self.base_url}/api/v2/auth/token",
                    json={"clientId": CLIENT_ID, "clientSecret": CLIENT_SECRET},
                    timeout=10,
                )
                if resp.status_code == 200:
                    token = resp.json().get("token")
                    if token:
                        self.session.headers["Authorization"] = f"Bearer {token}"
                        self.auth_mode = "v2_token"
                        print("[AUTH] Conectado via API v2 token")
                        return
            except Exception:
                pass

            # Tenta Bearer com CLIENT_ID direto
            test_headers = {"Authorization": f"Bearer {CLIENT_ID}"}
            try:
                resp = self.session.get(
                    f"{self.base_url}/api/v2/survey-groups",
                    headers=test_headers,
                    timeout=10,
                )
                if resp.status_code == 200:
                    self.session.headers["Authorization"] = f"Bearer {CLIENT_ID}"
                    self.auth_mode = "v2_bearer"
                    print("[AUTH] Conectado via API v2 Bearer")
                    return
            except Exception:
                pass

        # Fallback: session cookie
        if SESSION_COOKIE:
            self.session.headers["Cookie"] = SESSION_COOKIE
            self.auth_mode = "session"
            print("[AUTH] Usando session cookie")
        else:
            self.auth_mode = "none"
            print(
                "[AUTH] AVISO: Sem autenticação configurada. "
                "Preencha WEHELP_SESSION_COOKIE no .env"
            )

    def _post(self, endpoint, data=None):
        """Faz POST para a API interna."""
        url = f"{self.base_url}/api/{endpoint}"
        resp = self.session.post(url, json=data or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ── Empresa ──────────────────────────────────────────────

    def get_company(self):
        """Retorna dados da empresa."""
        return self._post("company/get")

    # ── Unidades ─────────────────────────────────────────────

    def get_company_units(self):
        """Retorna todas as unidades da empresa."""
        return self._post("company-units/find-all")

    def get_nps_by_units(self, filters=None):
        """Retorna NPS por unidade de negócio."""
        return self._post("nps-company-units/find", filters or {})

    # ── Touchpoints ──────────────────────────────────────────

    def get_touchpoints(self):
        """Retorna todos os touchpoints configurados."""
        return self._post("touchpoints/find-all")

    # ── Respostas NPS ────────────────────────────────────────

    def get_responses_count(self, filters=None):
        """Conta total de respostas."""
        return self._post("responses/count", filters or {})

    def get_answered_count(self, filters=None):
        """Conta respostas respondidas."""
        return self._post("responses/count-answered", filters or {})

    def get_answered_responses(self, page=1, limit=50, filters=None):
        """Retorna respostas respondidas paginadas."""
        data = {"page": page, "limit": limit}
        if filters:
            data.update(filters)
        return self._post("responses/find-answered", data)

    def get_all_answered_responses(self, filters=None):
        """Coleta todas as respostas respondidas (com paginação automática)."""
        all_responses = []
        page = 1
        limit = 100

        while True:
            result = self.get_answered_responses(page=page, limit=limit, filters=filters)
            responses = result if isinstance(result, list) else result.get("data", result.get("items", []))

            if not responses:
                break

            all_responses.extend(responses)
            print(f"  Coletadas {len(all_responses)} respostas...")

            # Verifica se há mais páginas
            if isinstance(result, dict):
                total = result.get("total", result.get("count", 0))
                if total and len(all_responses) >= total:
                    break
                if result.get("next") is None and len(responses) < limit:
                    break

            if len(responses) < limit:
                break

            page += 1
            time.sleep(0.3)  # Rate limiting

        return all_responses

    def get_response_detail(self, response_id):
        """Retorna detalhe de uma resposta específica."""
        return self._post("responses/get", {"id": response_id})

    # ── Survey Groups ────────────────────────────────────────

    def get_survey_groups(self):
        """Retorna grupos de pesquisa."""
        return self._post("survey-groups/find-all")

    # ── Tags ─────────────────────────────────────────────────

    def get_tag_topics(self):
        """Retorna tópicos de tags."""
        return self._post("tag-topics/find-all")

    # ── Ticket Stages ────────────────────────────────────────

    def get_ticket_stages(self):
        """Retorna estágios de tickets."""
        return self._post("ticket-stages/find-all")


def fetch_and_save_data(output_dir="data"):
    """Coleta todos os dados da WeHelp e salva em JSON."""
    os.makedirs(output_dir, exist_ok=True)
    client = WeHelpClient()

    datasets = {}

    print("\n=== Coletando dados da WeHelp ===\n")

    # Empresa
    print("[1/7] Dados da empresa...")
    try:
        datasets["company"] = client.get_company()
    except Exception as e:
        print(f"  Erro: {e}")
        datasets["company"] = {}

    # Unidades
    print("[2/7] Unidades de negócio...")
    try:
        datasets["units"] = client.get_company_units()
    except Exception as e:
        print(f"  Erro: {e}")
        datasets["units"] = []

    # NPS por unidade
    print("[3/7] NPS por unidade...")
    try:
        datasets["nps_units"] = client.get_nps_by_units()
    except Exception as e:
        print(f"  Erro: {e}")
        datasets["nps_units"] = []

    # Touchpoints
    print("[4/7] Touchpoints...")
    try:
        datasets["touchpoints"] = client.get_touchpoints()
    except Exception as e:
        print(f"  Erro: {e}")
        datasets["touchpoints"] = []

    # Survey groups
    print("[5/7] Grupos de pesquisa...")
    try:
        datasets["survey_groups"] = client.get_survey_groups()
    except Exception as e:
        print(f"  Erro: {e}")
        datasets["survey_groups"] = []

    # Respostas
    print("[6/7] Respostas NPS (pode demorar)...")
    try:
        datasets["responses"] = client.get_all_answered_responses()
    except Exception as e:
        print(f"  Erro: {e}")
        datasets["responses"] = []

    # Tag topics
    print("[7/7] Tópicos de tags...")
    try:
        datasets["tag_topics"] = client.get_tag_topics()
    except Exception as e:
        print(f"  Erro: {e}")
        datasets["tag_topics"] = []

    # Salva tudo
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    for name, data in datasets.items():
        filepath = os.path.join(output_dir, f"{name}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        print(f"  Salvo: {filepath}")

    # Salva metadata
    meta = {
        "collected_at": datetime.now().isoformat(),
        "auth_mode": client.auth_mode,
        "counts": {k: len(v) if isinstance(v, list) else 1 for k, v in datasets.items()},
    }
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n=== Coleta finalizada: {sum(meta['counts'].values())} registros ===\n")
    return datasets


if __name__ == "__main__":
    fetch_and_save_data()
