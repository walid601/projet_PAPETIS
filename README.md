# PAPETIS DISTRIBUTION — Outil de prévision des ventes

Outil de prévision des ventes mensuelles à 12 mois glissants pour PAPETIS DISTRIBUTION.  
Développé dans le cadre d'un projet étudiant de contrôle de gestion.

---

## Fonctionnalités

- Import automatique d'un fichier Excel ou CSV de ventes historiques
- Calcul de la tendance par 3 méthodes : moindres carrés (MCO), moyennes mobiles, lissage exponentiel
- Calcul des coefficients saisonniers (modèle multiplicatif)
- Prévisions mensuelles sur 12 mois glissants
- Détection automatique des observations atypiques
- Comparaison des méthodes avec indicateur d'erreur MAPE
- Export des résultats au format Excel
- Visualisation graphique historique + prévisions

---

## Prérequis

- Python 3.9 ou supérieur
- pip

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/VOTRE_USERNAME/papetis-previsions.git
cd papetis-previsions
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

---

## Structure du projet

```
papetis-previsions/
│
├── data/
│   └── papetis_ventes_historiques.xlsx   ← fichier de données (à placer ici)
│
├── papetis_backend.py                    ← calculs statistiques et prévisions
├── app.py                                ← interface Streamlit (front-end)
├── requirements.txt                      ← dépendances Python
└── README.md
```

---

## Lancement

### Backend seul (calculs + export Excel)

```bash
python papetis_backend.py
```

Résultats générés dans le dossier courant :
- `previsions_papetis.xlsx` — fichier Excel avec 4 feuilles de résultats
- `graphique_previsions.png` — graphique des prévisions

### Interface Streamlit (recommandé)

```bash
streamlit run app.py
```

Ouvre automatiquement l'interface dans le navigateur à l'adresse `http://localhost:8501`.

---

## Fichier de données attendu

Le fichier Excel doit contenir :

| Feuille | Contenu |
|---|---|
| `Ventes globales` | Ventes mensuelles totales sur 60 mois (colonnes : Année, Mois, t, Ventes (kMAD)) |
| `Ventes par famille` | Ventilation par famille de produits |

Le fichier doit être placé dans le dossier `data/` avant de lancer le script.

---

## Dépendances (`requirements.txt`)

```
pandas>=1.5.0
numpy>=1.23.0
matplotlib>=3.6.0
openpyxl>=3.0.10
statsmodels>=0.13.0
streamlit>=1.20.0
plotly>=5.13.0
```

---

## Résultats attendus

Après exécution, le fichier `previsions_papetis.xlsx` contient :

- **Prévisions 2026** — les 12 prévisions mensuelles en kMAD
- **Historique & Tendances** — données corrigées + les 3 courbes de tendance
- **Coefficients Saisonniers** — les 12 coefficients ajustés (somme = 12)
- **Comparaison Méthodes** — MAPE de chaque méthode

---

## Auteurs

- **Étudiant A** — MAATIR abdessamad — Interface Streamlit, visualisation, documentation
- **Étudiant B** — ELGUEDDARI walid — Back-end, algorithmes statistiques, modélisation UML

Projet encadré par :  
Année universitaire : 2025–2026
