# OBRAIL-BDD — Base de données ferroviaires européennes

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![PostGIS](https://img.shields.io/badge/PostGIS-3.4-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-Proprietary-red)

## Contexte

Ce projet s'inscrit dans le cadre du **MSPR (Mission de Préparation à la Rentrée)**, formation DIADS/DIA.
Il constitue le socle de données de la plateforme **OBRAIL Europe** — un observatoire des données ferroviaires à l'échelle européenne.

---

## Vue d'ensemble

La base de données OBRAIL stocke et structure les données relatives au réseau ferroviaire européen :

- **Trajets** : horaires, durées, émissions CO₂, classification jour/nuit
- **Opérateurs** : compagnies ferroviaires (SNCF, Deutsche Bahn, Thalys, Eurostar, etc.)
- **Lignes & Gares** : infrastructure avec géolocalisation (PostGIS)
- **Imports** : historique des chargements de données avec suivi de statut
- **Pays** : référentiel géographique des pays couverts

---

## Architecture de la base

```
┌─────────────────────────────────────────────┐
│           PostgreSQL 15 + PostGIS           │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ trajets  │  │ gares    │  │  opérateurs│ │
│  │          │──│          │  │            │ │
│  └────┬─────┘  └────┬─────┘  └─────┬──────┘ │
│       │             │              │        │
│  ┌────┴─────┐  ┌────┴─────┐   ┌────┴───────┐│
│  │ lignes   │  │ pays     │   │  imports   ││
│  │          │  │          │   │            ││
│  └──────────┘  └──────────┘   └────────────┘│
│                                             │
└─────────────────────────────────────────────┘
```

### Modélisation

| Table | Description | Colonnes clés |
|---|---|---|
| `trajets` | Trajets ferroviaires avec données temporelles et CO₂ | `id_trajet`, `id_service`, `depart`, `arrivee`, `duree_minutes`, `type_calcul`, `emission_co2_kg` |
| `operateurs` | Compagnies ferroviaires | `id_operateur`, `nom`, `nb_trajets`, `nb_lignes` |
| `lignes` | Lignes commerciales | `id_ligne`, `nom_ligne` |
| `gares` | Gares avec géolocalisation PostGIS | `id_gare`, `nom`, `ville`, `code_pays`, `coordonnees` |
| `pays` | Pays couverts | `code_pays`, `nom_pays` |
| `imports` | Historique des chargements de données | `id_import`, `date_import`, `nb_lignes_importees`, `statut`, `message` |

---

## Stack Technique

- **SGBD** : PostgreSQL 15
- **Extension spatiale** : PostGIS 3.4
- **Container** : Docker via `postgis/postgis:15-3.4`
- **Initialisation** : Script SQL injecté au premier démarrage via `docker-entrypoint-initdb.d/`

---

## Démarrage rapide

### Prérequis

- Docker & Docker Compose installés
- Port `5434` disponible sur la machine hôte

### Lancer la base

```powershell
cd OBRAIL-BDD
docker-compose up -d
```

La base est initialisée automatiquement avec le schéma et les données depuis `db/init_obrail_db.sql`.

### Se connecter à la base

```powershell
docker exec -it obrail_db psql -U obrail_user -d obrail
```

### Connexion depuis l'API

```
Host: localhost
Port: 5434
Database: obrail
User: obrail_user
Password: obrail_pass
```

---

## Dockerfile personnalisé

Une image personnalisée est disponible pour empaqueter le script d'initialisation directement dans l'image :

```dockerfile
FROM postgis/postgis:15-3.4
COPY db/init_obrail_db.sql /docker-entrypoint-initdb.d/
```

### Build de l'image

```powershell
docker build -t obrail-bdd:latest .
docker run -d -p 5434:5432 --name obrail_db obrail-bdd:latest
```

---

## CI/CD — Build automatisé de l'image

Un workflow GitHub Actions est configuré pour construire et pousser automatiquement l'image sur **GitHub Container Registry (GHCR)** à chaque push sur `main` ou `develop`.

### Workflow

| Événement | Déclencheur | Action |
|---|---|---|
| Push sur `main` | Branch | Build + push tag `main` |
| Push sur `develop` | Branch | Build + push tag `develop` |
| Tag `v1.2.0` | Tag | Build + push tag `1.2.0` |
| Pull Request | PR | Build uniquement (pas de push) |

### Récupérer l'image depuis GHCR

```powershell
docker pull ghcr.io/mspr-3/obrail-bdd:main
```

---

## Schéma de la base

Le schéma est entièrement défini dans `db/init_obrail_db.sql` et comprend :

- Création des types PostgreSQL personnalisés (statuts d'import, etc.)
- Tables avec contraintes de clés étrangères
- Index pour les performances (sur `id_trajet`, `id_operateur`, `code_pays`, etc.)
- Colonnes géographiques PostGIS pour les gares

---

## Volumes & Persistance

Les données sont persistées dans un volume Docker nommé `obrail_pgdata` :

```yaml
volumes:
  obrail_pgdata:
    driver: local
```

Pour réinitialiser la base :

```powershell
docker-compose down -v  # Supprime le volume et les données
docker-compose up -d    # Recrée la base proprement
```

---

## Intégration avec les autres composants

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  OBRAIL-Frontend │───▶│   OBRAIL-API     │────▶│   OBRAIL-BDD     │
│  (React/Vite)    │     │  (FastAPI)       │     │  (PostgreSQL)    │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

- **OBRAIL-API** se connecte en direct à cette base via `asyncpg`
- **OBRAIL-Frontend** ne communique qu'avec l'API, jamais directement avec la BDD

---

## Scripts d'installation

Un script `setup.ps1` (Windows PowerShell) est fourni pour automatiser l'installation et le démarrage de la base de données sur un environnement Windows.

```powershell
.\setup.ps1
```


---

## Licence

Projet pédagogique. Utilisation interne — DIADS/DIA.
