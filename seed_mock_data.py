"""Seed mock data: 15 imports with realistic blood bank data."""

import random
import sqlite3
from datetime import datetime, timedelta

from src.config import SQLITE_DB_PATH
from src.history_store import init_db

random.seed(42)

TIPOS_HEMO = [
    "CHD - Concentrado de Hemacias Desleucocitado",
    "CH - Concentrado de Hemacias",
    "PFC - Plasma Fresco Congelado",
    "CRIO - Crioprecipitado",
    "CP - Concentrado de Plaquetas",
    "CHF - Concentrado de Hemacias Fenotipado",
]

TIPOS_GS_RH = ["O/POS", "O/NEG", "A/POS", "A/NEG", "B/POS", "B/NEG", "AB/POS", "AB/NEG"]

# Weighted distribution (O+ and A+ are most common in Brazil)
GS_WEIGHTS = [38, 7, 34, 6, 8, 2, 4, 1]

RESPONSAVEIS = [
    "Maria Helena Silva",
    "Carlos Eduardo Santos",
    "Ana Paula Ferreira",
    "Joao Victor Oliveira",
    "Patricia Souza Lima",
]

COMPROVANTE_BASE = 1290000


def gerar_bolsas(n_bolsas, data_entrada):
    """Generate n realistic blood bags."""
    bolsas = []
    for _ in range(n_bolsas):
        tipo = random.choice(TIPOS_HEMO)
        gs_rh = random.choices(TIPOS_GS_RH, weights=GS_WEIGHTS, k=1)[0]

        # Volume depends on component type
        if "Plaqueta" in tipo or "CRIO" in tipo:
            volume = random.choice([40, 50, 60, 70])
        elif "Plasma" in tipo:
            volume = random.choice([180, 200, 220, 250])
        else:
            volume = random.randint(250, 380)

        # Expiry: CHD ~35 days, PFC ~1 year, CRIO ~1 year, CP ~5 days
        if "Plaqueta" in tipo or "CP" in tipo:
            days_valid = random.randint(2, 5)
        elif "Plasma" in tipo or "CRIO" in tipo:
            days_valid = random.randint(180, 365)
        else:
            days_valid = random.randint(20, 42)

        data_validade = data_entrada + timedelta(days=days_valid)
        num_bolsa = str(random.randint(24000000, 26999999))

        bolsas.append({
            "num_bolsa": num_bolsa,
            "tipo_hemocomponente": tipo,
            "gs_rh": gs_rh,
            "volume": volume,
            "data_validade": data_validade.strftime("%d/%m/%Y"),
        })
    return bolsas


def seed():
    init_db(SQLITE_DB_PATH)
    conn = sqlite3.connect(SQLITE_DB_PATH)

    # Clear existing mock data (keep real data if any)
    # We'll just add on top

    now = datetime.now()
    total_bolsas = 0

    for i in range(15):
        # Spread imports over last 30 days
        days_ago = random.randint(0, 29)
        hours = random.randint(7, 18)
        minutes = random.randint(0, 59)
        ts = now - timedelta(days=days_ago, hours=random.randint(0, 5))
        ts = ts.replace(hour=hours, minute=minutes, second=random.randint(0, 59))

        n_bolsas = random.randint(2, 8)
        data_entrada = ts.date()
        bolsas = gerar_bolsas(n_bolsas, data_entrada)

        # Comprovante numbers
        n_comprovantes = random.randint(1, 3)
        comp_nums = ", ".join(str(COMPROVANTE_BASE + random.randint(1, 9999)) for _ in range(n_comprovantes))

        filename = f"comprovante_expedicao_{ts.strftime('%Y%m%d')}_{i+1:02d}.pdf"

        # 13 out of 15 succeed, 2 have partial status
        if i in (5, 11):
            status = "parcial"
            error_msg = "1 bolsa com dados incompletos"
        else:
            status = "sucesso"
            error_msg = None

        cursor = conn.execute(
            "INSERT INTO import_records (timestamp, filename, comprovante_nums, "
            "bolsa_count, status, error_message) VALUES (?, ?, ?, ?, ?, ?)",
            (ts.isoformat(), filename, comp_nums, n_bolsas, status, error_msg),
        )
        import_id = cursor.lastrowid

        for b in bolsas:
            conn.execute(
                "INSERT INTO import_bolsas (import_id, num_bolsa, tipo_hemocomponente, "
                "gs_rh, volume, data_validade) VALUES (?, ?, ?, ?, ?, ?)",
                (import_id, b["num_bolsa"], b["tipo_hemocomponente"],
                 b["gs_rh"], b["volume"], b["data_validade"]),
            )

        total_bolsas += n_bolsas
        print(f"  Import {i+1:2d}: {filename} | {n_bolsas} bolsas | {status}")

    conn.commit()
    conn.close()
    print(f"\nDone! 15 imports, {total_bolsas} bolsas total.")


if __name__ == "__main__":
    seed()
