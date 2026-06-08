# 📈 Outil de Prévision des Ventes — PAPETIS DISTRIBUTION

Prototype fonctionnel d'aide à la décision conçu pour l'analyse de la saisonnalité et la génération de prévisions mensuelles à horizon de 12 mois glissants (Année 2026).

## 🚀 Fonctionnalités Implémentées
- **Importation automatisée (No-Touch)** du fichier historique des ventes de l'entreprise.
- **Détection et correction par imputation** des 2 observations atypiques (Chocs logistiques/conjoncturels).
- **Modélisation de la tendance** via trois méthodes statistiques :
  - Moindres Carrés Ordinaires (MCO)
  - Moyennes Mobiles Centrées (MM12)
  - Lissage Exponentiel Simple (LES)
- **Arbitrage et calcul d'indicateurs de performance** (Calcul du MAPE pour chaque modèle).
- **Ajustement Saisonnier** basé sur un modèle multiplicatif global.
- **Visualisation graphique avancée** intégrant l'historique brut, l'historique corrigé, les tendances et les prévisions.
- **Exportation automatisée** des résultats sur un classeur Excel multi-feuilles et génération d'un rendu image haute résolution.

## 🛠️ Configuration et Installation
1. S'assurer de disposer d'un environnement **Python 3.11 ou supérieur**.
2. Installer les dépendances nécessaires à l'aide du gestionnaire de paquets :
   ```bash
   pip install pandas numpy openpyxl matplotlib statsmodels