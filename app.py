# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
import io

# ── Configuration de la page ──────────────────────────────────────────────────
st.set_page_config(
    page_title="PAPETIS — Prévisions des ventes",
    page_icon="📊",
    layout="wide"
)

st.title("📊 PAPETIS DISTRIBUTION — Outil de prévision des ventes")
st.caption("Prévisions mensuelles à 12 mois glissants · Modèle multiplicatif")

# ══════════════════════════════════════════════════════════════════════════════
# 1. IMPORT DU FICHIER
# ══════════════════════════════════════════════════════════════════════════════
st.header("1. Importer les données")

uploaded_file = st.file_uploader(
    "Déposez le fichier papetis_ventes_historiques.xlsx",
    type=["xlsx", "csv"]
)

if uploaded_file is None:
    st.info("Veuillez importer le fichier Excel ou CSV pour commencer.")
    st.stop()

# Chargement
try:
    if uploaded_file.name.endswith(".csv"):
        df_global = pd.read_csv(uploaded_file)
        df_global = df_global.rename(columns=lambda c: c.strip())
    else:
        df_global = pd.read_excel(uploaded_file, sheet_name="Ventes globales",
                                   header=3, engine="openpyxl")

    df_global = df_global.dropna(subset=['Ventes (kMAD)'])
    df_global = df_global.rename(columns={'Année': 'Annee', 'Ventes (kMAD)': 'Ventes'})
    df_global['Ventes'] = pd.to_numeric(df_global['Ventes'], errors='coerce').astype(float)
    st.success(f"Fichier chargé : {len(df_global)} mois détectés.")
except Exception as e:
    st.error(f"Erreur lors du chargement : {e}")
    st.stop()

ventes_brutes = df_global['Ventes'].copy()

# ══════════════════════════════════════════════════════════════════════════════
# 2. DÉTECTION DES ANOMALIES
# ══════════════════════════════════════════════════════════════════════════════
st.header("2. Détection des observations atypiques")

stats_mensuelles = df_global.groupby('Mois')['Ventes'].agg(['mean', 'std']).reset_index()
stats_mensuelles.columns = ['Mois', 'Moyenne_du_Mois', 'Std_du_Mois']
df_analyse = pd.merge(df_global, stats_mensuelles, on='Mois').sort_values(by='t').reset_index(drop=True)
df_analyse['Ecart_Absolu'] = (df_analyse['Ventes'] - df_analyse['Moyenne_du_Mois']).abs()

top_2 = df_analyse.nlargest(2, 'Ecart_Absolu')
indices_anomalies = df_analyse['t'].isin(top_2['t'])

col1, col2 = st.columns(2)
for i, (_, row) in enumerate(top_2.iterrows()):
    with (col1 if i == 0 else col2):
        st.warning(
            f"**Anomalie détectée** — Année {int(row['Annee'])}, Mois {int(row['Mois'])} (t={int(row['t'])})\n\n"
            f"Valeur observée : **{row['Ventes']:.0f} kMAD**  \n"
            f"Moyenne du mois : **{row['Moyenne_du_Mois']:.0f} kMAD**  \n"
            f"Écart : **{row['Ecart_Absolu']:.0f} kMAD**"
        )

df_analyse.loc[indices_anomalies, 'Ventes'] = df_analyse.loc[indices_anomalies, 'Moyenne_du_Mois']
st.caption("Les 2 anomalies ont été remplacées par la moyenne de leur mois respectif.")

# ══════════════════════════════════════════════════════════════════════════════
# 3. CHOIX DE LA MÉTHODE
# ══════════════════════════════════════════════════════════════════════════════
st.header("3. Choisir la méthode de prévision")

methode = st.selectbox(
    "Méthode de calcul de la tendance",
    ["Moindres carrés (MCO)", "Moyennes mobiles (MM12)", "Lissage exponentiel (LES)"],
    index=0
)

# ── Calcul des 3 tendances ────────────────────────────────────────────────────
X = df_analyse['t'].values
Y = df_analyse['Ventes'].values

a, b = np.polyfit(X, Y, 1)
df_analyse['Tendance_MCO'] = a * X + b

df_analyse['Tendance_MM'] = df_analyse['Ventes'].rolling(window=12, center=True).mean()

modele_les = SimpleExpSmoothing(df_analyse['Ventes']).fit(optimized=True)
df_analyse['Tendance_LES'] = modele_les.fittedvalues
alpha = modele_les.params['smoothing_level']

# Sélection de la tendance active
tendance_col = {
    "Moindres carrés (MCO)": "Tendance_MCO",
    "Moyennes mobiles (MM12)": "Tendance_MM",
    "Lissage exponentiel (LES)": "Tendance_LES"
}[methode]

# MAPE
def mape(y_reel, y_pred):
    mask = (y_reel != 0) & (~np.isnan(y_pred))
    return np.mean(np.abs((y_reel[mask] - y_pred[mask]) / y_reel[mask])) * 100

mape_mco = mape(Y, df_analyse['Tendance_MCO'].values)
mape_mm  = mape(Y, df_analyse['Tendance_MM'].values)
mape_les = mape(Y, df_analyse['Tendance_LES'].values)

c1, c2, c3 = st.columns(3)
c1.metric("MAPE — MCO", f"{mape_mco:.1f}%",
          delta="meilleur" if mape_mco == min(mape_mco, mape_mm, mape_les) else None,
          delta_color="inverse")
c2.metric("MAPE — MM12", f"{mape_mm:.1f}%",
          delta="meilleur" if mape_mm == min(mape_mco, mape_mm, mape_les) else None,
          delta_color="inverse")
c3.metric("MAPE — LES", f"{mape_les:.1f}%",
          delta="meilleur" if mape_les == min(mape_mco, mape_mm, mape_les) else None,
          delta_color="inverse")

# ── Coefficients saisonniers ──────────────────────────────────────────────────
df_analyse['Rapport'] = df_analyse['Ventes'] / df_analyse['Tendance_MCO']
coeffs = df_analyse.groupby('Mois')['Rapport'].mean().reset_index()
somme = coeffs['Rapport'].sum()
coeffs['Coeff'] = coeffs['Rapport'] * (12.0 / somme)

# ══════════════════════════════════════════════════════════════════════════════
# 4. PRÉVISIONS + SCÉNARIOS
# ══════════════════════════════════════════════════════════════════════════════
st.header("4. Paramètres des scénarios")

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    pess = st.slider("Scénario pessimiste (%)", min_value=-30, max_value=0, value=-10, step=1)
with col_s2:
    st.markdown("<br><p style='text-align:center;font-weight:600'>Central (base)</p>", unsafe_allow_html=True)
with col_s3:
    opti = st.slider("Scénario optimiste (%)", min_value=0, max_value=30, value=10, step=1)

# Calcul prévisions
t_futur = np.arange(61, 73)
mois_futur = [(t - 1) % 12 + 1 for t in t_futur]
df_prev = pd.DataFrame({'t': t_futur, 'Mois': mois_futur})
df_prev['Tendance'] = a * df_prev['t'] + b
df_prev = pd.merge(df_prev, coeffs[['Mois', 'Coeff']], on='Mois').sort_values('t').reset_index(drop=True)
df_prev['Central']    = df_prev['Tendance'] * df_prev['Coeff']
df_prev['Pessimiste'] = df_prev['Central'] * (1 + pess / 100)
df_prev['Optimiste']  = df_prev['Central'] * (1 + opti / 100)

noms_mois = ['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc']
df_prev['Mois_Label'] = df_prev['Mois'].apply(lambda m: noms_mois[m - 1] + " 2026")

# ══════════════════════════════════════════════════════════════════════════════
# 5. GRAPHIQUE
# ══════════════════════════════════════════════════════════════════════════════
st.header("5. Visualisation")

fig = go.Figure()

# Historique brut
fig.add_trace(go.Scatter(
    x=list(range(1, 61)), y=ventes_brutes.values,
    name="Historique brut", line=dict(color="#AAAAAA", dash="dot", width=1.2),
    opacity=0.6
))

# Historique corrigé
fig.add_trace(go.Scatter(
    x=df_analyse['t'].tolist(), y=df_analyse['Ventes'].tolist(),
    name="Historique corrigé", line=dict(color="#2C7BB6", width=2)
))

# Tendance active
tendance_colors = {
    "Moindres carrés (MCO)": "#D7191C",
    "Moyennes mobiles (MM12)": "#F29C24",
    "Lissage exponentiel (LES)": "#7B2D8B"
}
fig.add_trace(go.Scatter(
    x=df_analyse['t'].tolist(), y=df_analyse[tendance_col].tolist(),
    name=f"Tendance ({methode})", line=dict(color=tendance_colors[methode], dash="dash", width=1.5)
))

# Anomalies
anom_t = df_analyse.loc[indices_anomalies, 't'].tolist()
anom_v = [ventes_brutes.iloc[t - 1] for t in anom_t]
fig.add_trace(go.Scatter(
    x=anom_t, y=anom_v, mode="markers",
    name="Anomalies", marker=dict(color="red", size=10, symbol="x")
))

# Zone de prévision
fig.add_vrect(x0=60.5, x1=72.5, fillcolor="green", opacity=0.05, line_width=0)
fig.add_vline(x=60.5, line_dash="dash", line_color="black", line_width=1.5,
              annotation_text="Horizon de prévision →", annotation_position="top right")

# Scénarios
fig.add_trace(go.Scatter(
    x=df_prev['t'].tolist(), y=df_prev['Central'].tolist(),
    name="Prévision centrale", line=dict(color="#1A9641", width=2.5),
    mode="lines+markers", marker=dict(size=6)
))
fig.add_trace(go.Scatter(
    x=df_prev['t'].tolist() + df_prev['t'].tolist()[::-1],
    y=df_prev['Optimiste'].tolist() + df_prev['Pessimiste'].tolist()[::-1],
    fill='toself', fillcolor='rgba(26,150,65,0.12)',
    line=dict(color='rgba(255,255,255,0)'),
    name=f"Zone scénarios ({pess}% / +{opti}%)", showlegend=True
))

fig.update_layout(
    title="PAPETIS DISTRIBUTION — Prévisions des ventes à 12 mois (modèle multiplicatif)",
    xaxis_title="Index temporel (t) — Jan 2021 = t1",
    yaxis_title="Ventes (kMAD)",
    legend=dict(orientation="h", yanchor="bottom", y=-0.3),
    height=500,
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 6. TABLEAU DES PRÉVISIONS
# ══════════════════════════════════════════════════════════════════════════════
st.header("6. Tableau des prévisions 2026")

df_display = df_prev[['Mois_Label', 'Pessimiste', 'Central', 'Optimiste']].copy()
df_display.columns = ['Mois', f'Pessimiste ({pess}%)', 'Central (base)', f'Optimiste (+{opti}%)']
df_display = df_display.set_index('Mois')
for col in df_display.columns:
    df_display[col] = df_display[col].map(lambda x: f"{x:.1f} kMAD")
st.dataframe(df_display, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 7. EXPORT EXCEL
# ══════════════════════════════════════════════════════════════════════════════
st.header("7. Exporter les résultats")

def generer_excel():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_prev[['Mois_Label', 'Pessimiste', 'Central', 'Optimiste']].to_excel(
            writer, sheet_name='Prévisions 2026', index=False)
        df_analyse[['Annee', 'Mois', 't', 'Ventes', 'Tendance_MCO',
                    'Tendance_MM', 'Tendance_LES']].to_excel(
            writer, sheet_name='Historique & Tendances', index=False)
        coeffs.to_excel(writer, sheet_name='Coefficients Saisonniers', index=False)
        pd.DataFrame({
            'Méthode': ['MCO', 'Moyennes Mobiles (12)', 'Lissage Exponentiel'],
            'MAPE (%)': [round(mape_mco, 2), round(mape_mm, 2), round(mape_les, 2)]
        }).to_excel(writer, sheet_name='Comparaison Méthodes', index=False)
    return output.getvalue()

st.download_button(
    label="⬇️ Télécharger les résultats (Excel)",
    data=generer_excel(),
    file_name="previsions_papetis.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
