#!/usr/bin/env python3
"""
Récupère les gares SNCF manquantes depuis l'API SNCF Open Data (liste-des-gares)
et les insère dans la table gare.

Usage: python3 fill_missing_gares.py
"""

import psycopg2
import urllib.request
import urllib.parse
import json

DB = {
    "host": "localhost",
    "port": 5434,
    "dbname": "obrail",
    "user": "obrail_user",
    "password": "obrail_pass",
}

SNCF_API = (
    "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets"
    "/liste-des-gares/records"
)


def fetch_all_gares() -> dict[str, dict]:
    """Récupère toutes les gares voyageurs de l'API SNCF (paginées)."""
    result = {}
    offset = 0
    limit = 100
    while True:
        params = urllib.parse.urlencode({
            "where": 'voyageurs="O"',
            "select": "code_uic,libelle,commune,x_wgs84,y_wgs84",
            "limit": limit,
            "offset": offset,
        })
        url = f"{SNCF_API}?{params}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            print(f"Erreur API offset={offset}: {e}")
            break

        rows = data.get("results", [])
        if not rows:
            break
        for r in rows:
            uic = str(r.get("code_uic", "")).strip()
            if uic:
                result[uic] = {
                    "nom": r.get("libelle", "").strip().title(),
                    "ville": r.get("commune", "").strip().title(),
                    "lat": r.get("y_wgs84"),
                    "lon": r.get("x_wgs84"),
                }
        print(f"  Fetched {len(result)} gares…", end="\r")
        if len(rows) < limit:
            break
        offset += limit
    print()
    return result


def main():
    print("Connexion à la DB…")
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    # Récupère tous les id_gare + UIC manquants
    cur.execute("""
        SELECT DISTINCT t.id_gare_depart AS id_gare,
               SPLIT_PART(t.id_gare_depart, '-', 2) AS uic
        FROM trajet t
        LEFT JOIN gare g ON t.id_gare_depart = g.id_gare
        WHERE g.id_gare IS NULL
          AND t.id_gare_depart LIKE 'StopPoint:%'
        UNION
        SELECT DISTINCT t.id_gare_arrivee AS id_gare,
               SPLIT_PART(t.id_gare_arrivee, '-', 2) AS uic
        FROM trajet t
        LEFT JOIN gare g ON t.id_gare_arrivee = g.id_gare
        WHERE g.id_gare IS NULL
          AND t.id_gare_arrivee LIKE 'StopPoint:%'
        ORDER BY uic
    """)
    missing = cur.fetchall()
    missing_uics = {uic for _, uic in missing}
    print(f"{len(missing)} id_gare à insérer ({len(missing_uics)} UIC distincts)")

    print("Téléchargement du référentiel SNCF…")
    gares_api = fetch_all_gares()
    print(f"{len(gares_api)} gares voyageurs trouvées dans l'API")

    inserted = 0
    skipped = 0

    for id_gare, uic in missing:
        info = gares_api.get(uic)
        if not info or not info["nom"]:
            skipped += 1
            continue

        ville = info["ville"] or info["nom"]
        try:
            # Upsert localisation d'abord (FK)
            cur.execute("""
                INSERT INTO localisation (code_pays, nom_pays, ville)
                VALUES ('FR', 'France', %s)
                ON CONFLICT DO NOTHING
            """, (ville,))
            cur.execute("""
                INSERT INTO gare (
                    id_gare, nom_officiel, ville, code_pays,
                    type_liaison, latitude, longitude
                ) VALUES (%s, %s, %s, 'FR', 'nationale', %s, %s)
                ON CONFLICT (id_gare) DO NOTHING
            """, (
                id_gare,
                info["nom"],
                ville,
                info["lat"],
                info["lon"],
            ))
            if cur.rowcount:
                inserted += 1
        except Exception as e:
            print(f"\nINSERT error {id_gare}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nTerminé : {inserted} gares insérées, {skipped} non trouvées dans l'API.")


if __name__ == "__main__":
    main()
