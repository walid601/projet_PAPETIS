# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

# ============================================================
# 1. CHARGEMENT DYNAMIQUE DU FICHIER EXCEL
# ============================================================
DOSSIER_ACTUEL = os.path.dirname(os.path.abspath(__file__))
chemin_excel = os.path.join(DOSSIER_ACTUEL, "data", "papetis_ventes_historiques.xlsx")

try:
    df_global = pd.read_excel(chemin_excel, sheet_name="Ventes globales", header=3, engine="openpyxl")
    df_global = df_global.dropna(subset=['Ventes (kMAD)'])
    df_global = df_global.rename(columns={'Année': 'Annee', 'Ventes (kMAD)': 'Ventes'})
    df_global['Ventes'] = pd.to_numeric(df_global['Ventes'], errors='coerce').astype(float)

    print("-" * 60)
    print("STATUT : Fichier chargé avec succès (60 mois détectés).")
    print("-" * 60)

    ventes_brutes = df_global['Ventes'].copy()

    # ============================================================
    # 2. DÉTECTION ET CORRECTION DES 2 OBSERVATIONS ATYPIQUES
    # ============================================================
    stats_mensuelles = df_global.groupby('Mois')['Ventes'].agg(['mean', 'std']).reset_index()
    stats_mensuelles.columns = ['Mois', 'Moyenne_du_Mois', 'Std_du_Mois']

    df_analyse = pd.merge(df_global, stats_mensuelles, on='Mois').sort_values(by='t').reset_index(drop=True)
    df_analyse['Ecart_Absolu'] = (df_analyse['Ventes'] - df_analyse['Moyenne_du_Mois']).abs()

    top_2_anomalies = df_analyse.nlargest(2, 'Ecart_Absolu')
    indices_anomalies = df_analyse['t'].isin(top_2_anomalies['t'])

    print("=" * 60)
    print("RÉSULTAT : LES 2 OBSERVATIONS ATYPIQUES DÉTECTÉES")
    print("=" * 60)
    print(df_analyse[indices_anomalies][['Annee', 'Mois', 't', 'Ventes', 'Moyenne_du_Mois']])
    print("-" * 60)

    # Imputation par la moyenne du mois
    df_analyse.loc[indices_anomalies, 'Ventes'] = df_analyse.loc[indices_anomalies, 'Moyenne_du_Mois']
    print("INFO : Les 2 anomalies ont été remplacées par la moyenne de leur mois.")
    print("-" * 60)

    # ============================================================
    # 3. MÉTHODE 1 : TENDANCE PAR MOINDRES CARRÉS ORDINAIRES (MCO)
    # ============================================================
    X_hist = df_analyse['t'].values
    Y_hist = df_analyse['Ventes'].values

    a, b = np.polyfit(X_hist, Y_hist, 1)
    df_analyse['Tendance_MCO'] = a * X_hist + b

    print("=" * 60)
    print("MÉTHODE 1 : TENDANCE MCO")
    print("=" * 60)
    print(f"Équation : Ventes = {a:.2f} × t + {b:.2f}")
    print("-" * 60)

    # ============================================================
    # 4. MÉTHODE 2 : MOYENNES MOBILES CENTRÉES (fenêtre = 12 mois)
    # ============================================================
    df_analyse['Tendance_MM'] = df_analyse['Ventes'].rolling(window=12, center=True).mean()
    print("MÉTHODE 2 : Moyennes mobiles centrées (fenêtre=12) calculées.")
    print("-" * 60)

    # ============================================================
    # 5. MÉTHODE 3 : LISSAGE EXPONENTIEL SIMPLE
    # ============================================================
    modele_les = SimpleExpSmoothing(df_analyse['Ventes']).fit(optimized=True)
    df_analyse['Tendance_LES'] = modele_les.fittedvalues
    alpha_optimal = modele_les.params['smoothing_level']
    print(f"MÉTHODE 3 : Lissage exponentiel simple (alpha optimal = {alpha_optimal:.4f}) calculé.")
    print("-" * 60)

    # ============================================================
    # 6. COEFFICIENTS SAISONNIERS (Modèle Multiplicatif sur MCO)
    # ============================================================
    df_analyse['Rapport_Saisonnier'] = df_analyse['Ventes'] / df_analyse['Tendance_MCO']
    coeffs_saisonniers = df_analyse.groupby('Mois')['Rapport_Saisonnier'].mean().reset_index()

    somme_coeffs = coeffs_saisonniers['Rapport_Saisonnier'].sum()
    coeffs_saisonniers['Coeff_Ajuste'] = coeffs_saisonniers['Rapport_Saisonnier'] * (12.0 / somme_coeffs)

    print("=" * 60)
    print("COEFFICIENTS SAISONNIERS AJUSTÉS (Somme = 12.00)")
    print("=" * 60)
    for _, row in coeffs_saisonniers.iterrows():
        print(f"  Mois {int(row['Mois']):02d} : {row['Coeff_Ajuste']:.4f}")
    print("-" * 60)

    # ============================================================
    # 7. PRÉVISIONS SUR 12 MOIS (t = 61 à 72 → Année 2026)
    # ============================================================
    t_futur = np.arange(61, 73)
    mois_futur = [(t - 1) % 12 + 1 for t in t_futur]

    df_previsions = pd.DataFrame({'t': t_futur, 'Mois': mois_futur})
    df_previsions['Tendance'] = a * df_previsions['t'] + b
    df_previsions = pd.merge(
        df_previsions,
        coeffs_saisonniers[['Mois', 'Coeff_Ajuste']],
        on='Mois'
    ).sort_values(by='t').reset_index(drop=True)
    df_previsions['Prevision'] = df_previsions['Tendance'] * df_previsions['Coeff_Ajuste']

    print("=" * 60)
    print("PRÉVISIONS PAPETIS DISTRIBUTION — 2026 (kMAD)")
    print("=" * 60)
    noms_mois = ['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc']
    for _, row in df_previsions.iterrows():
        print(f"  {noms_mois[int(row['Mois'])-1]} 2026 : {row['Prevision']:.1f} kMAD")
    print("-" * 60)

    # ============================================================
    # 8. INDICATEURS D'ERREUR — MAPE pour les 3 méthodes
    # ============================================================
    def calculer_mape(y_reel, y_pred):
        mask = (y_reel != 0) & (~np.isnan(y_pred))
        return np.mean(np.abs((y_reel[mask] - y_pred[mask]) / y_reel[mask])) * 100

    mape_mco = calculer_mape(df_analyse['Ventes'].values, df_analyse['Tendance_MCO'].values)
    mape_mm  = calculer_mape(df_analyse['Ventes'].values, df_analyse['Tendance_MM'].values)
    mape_les = calculer_mape(df_analyse['Ventes'].values, df_analyse['Tendance_LES'].values)

    print("=" * 60)
    print("COMPARAISON DES MÉTHODES — MAPE (% d'erreur moyen)")
    print("=" * 60)
    print(f"  MCO (moindres carrés)    : {mape_mco:.2f}%")
    print(f"  Moyennes mobiles (MM12)  : {mape_mm:.2f}%")
    print(f"  Lissage exponentiel (LES): {mape_les:.2f}%")
    meilleure = min([("MCO", mape_mco), ("MM12", mape_mm), ("LES", mape_les)], key=lambda x: x[1])
    print(f"  >> Meilleure methode : {meilleure[0]} avec {meilleure[1]:.2f}% d'erreur")
    print("-" * 60)

    # ============================================================
    # 9. GRAPHIQUE FINAL — Historique + Tendances + Prévisions
    # ============================================================
    fig, ax = plt.subplots(figsize=(16, 7))

    # Série historique brute (anomalies incluses pour visualisation)
    ax.plot(range(1, 61), ventes_brutes.values,
            color='#AAAAAA', linewidth=1.2, linestyle='--', label='Historique brut (avec anomalies)')

    # Série corrigée
    ax.plot(df_analyse['t'], df_analyse['Ventes'],
            color='#2C7BB6', linewidth=2, label='Historique corrigé')

    # Tendance MCO
    ax.plot(df_analyse['t'], df_analyse['Tendance_MCO'],
            color='#D7191C', linewidth=1.5, linestyle='-.', label=f'Tendance MCO (MAPE={mape_mco:.1f}%)')

    # Moyennes mobiles
    ax.plot(df_analyse['t'], df_analyse['Tendance_MM'],
            color='#F29C24', linewidth=1.5, linestyle=':', label=f'Moyennes mobiles 12 (MAPE={mape_mm:.1f}%)')

    # Lissage exponentiel
    ax.plot(df_analyse['t'], df_analyse['Tendance_LES'],
            color='#7B2D8B', linewidth=1.5, linestyle=':', label=f'Lissage exponentiel α={alpha_optimal:.2f} (MAPE={mape_les:.1f}%)')

    # Prévisions 2026
    ax.plot(df_previsions['t'], df_previsions['Prevision'],
            color='#1A9641', linewidth=2.5, marker='o', markersize=5, label='Prévisions 2026 (MCO × Saisonnalité)')

    # Zone de prévision ombrée
    ax.axvspan(60.5, 72.5, alpha=0.08, color='green', label='Zone de prévision')

    # Ligne de séparation historique / prévision
    ax.axvline(x=60.5, color='black', linewidth=1.5, linestyle='--')
    ax.text(60.8, ax.get_ylim()[0] * 1.01, '→ Prévisions', fontsize=9, color='black')

    # Marquage des anomalies corrigées
    for _, row in top_2_anomalies.iterrows():
        ax.scatter(row['t'], ventes_brutes.iloc[int(row['t']) - 1],
                   color='red', zorder=5, s=80, marker='x')
    anomalie_patch = mpatches.Patch(color='red', label='Observations atypiques (×)')
    handles, labels = ax.get_legend_handles_labels()
    handles.append(anomalie_patch)

    ax.set_title("PAPETIS DISTRIBUTION — Prévisions des ventes à 12 mois (Modèle Multiplicatif)", fontsize=14, fontweight='bold')
    ax.set_xlabel("Index temporel (t) — Jan 2021 = t1", fontsize=11)
    ax.set_ylabel("Ventes (kMAD)", fontsize=11)
    ax.legend(handles=handles, loc='upper left', fontsize=8)
    ax.grid(True, linestyle=':', alpha=0.5)
    plt.tight_layout()

    plt.savefig('graphique_previsions.png', dpi=300, bbox_inches='tight')
    print("Graphique sauvegardé : graphique_previsions.png")
    plt.show()

    # ============================================================
    # 10. EXPORT EXCEL — Toutes les feuilles de résultats
    # ============================================================
    def exporter_resultats(df_previsions, df_analyse, coeffs_saisonniers):
        with pd.ExcelWriter('previsions_papetis.xlsx', engine='openpyxl') as writer:
            df_previsions[['t', 'Mois', 'Tendance', 'Coeff_Ajuste', 'Prevision']].to_excel(
                writer, sheet_name='Prévisions 2026', index=False)
            df_analyse[['Annee', 'Mois', 't', 'Ventes', 'Tendance_MCO',
                         'Tendance_MM', 'Tendance_LES']].to_excel(
                writer, sheet_name='Historique & Tendances', index=False)
            coeffs_saisonniers.to_excel(
                writer, sheet_name='Coefficients Saisonniers', index=False)
            # Feuille comparaison MAPE
            df_mape = pd.DataFrame({
                'Méthode': ['MCO', 'Moyennes Mobiles (12)', 'Lissage Exponentiel'],
                'MAPE (%)': [round(mape_mco, 2), round(mape_mm, 2), round(mape_les, 2)]
            })
            df_mape.to_excel(writer, sheet_name='Comparaison Méthodes', index=False)
        print("Export Excel terminé : previsions_papetis.xlsx")

    exporter_resultats(df_previsions, df_analyse, coeffs_saisonniers)

except FileNotFoundError:
    print(f"ERREUR : Fichier introuvable → {chemin_excel}")
    print("Vérifiez que le fichier est bien dans le dossier 'data/'.")
except Exception as e:
    print(f"ERREUR CRITIQUE : {str(e)}")