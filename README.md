# SGA — Système de Gestion Académique

Application web de gestion académique développée avec Dash et Python, déployée sur Render avec une base de données PostgreSQL.

Lien de l'application : https://sga-academique.onrender.com  
Compte de démonstration : `admin` / `admin123`

---

## Apercu

Le SGA permet à des établissements d'enseignement de gérer leurs étudiants, leurs cours, leurs séances, leurs notes et leurs présences au travers d'une interface web moderne et responsive.

---

## Fonctionnalites

- **Authentification** : connexion sécurisée avec hachage bcrypt, gestion des rôles (admin / enseignant), inscription avec validation
- **Tableau de bord** : vue d'ensemble avec indicateurs clés (étudiants, cours, notes, absences)
- **Etudiants** : ajout, modification, désactivation, import/export Excel, fiche détaillée par étudiant
- **Cours** : création et gestion des cours avec code, libellé, volume horaire, couleur et enseignant référent
- **Séances** : planification des séances par cours avec date, durée, thème et salle
- **Présences** : saisie des présences par séance, suivi des absences et retards justifiés
- **Notes** : saisie manuelle ou import Excel, détection des doublons, modification et suppression
- **Rapports** : export PDF des résultats par étudiant ou par cours
- **Analyse statistique** : analyses univariées, bivariées et multivariées sur les données académiques
- **Page de bienvenue** : page d'accueil personnalisée à la connexion avec statistiques en temps réel

---

## Stack technique

| Composant | Technologie |
|---|---|
| Framework web | Dash 2.17.1 (Plotly) |
| Backend | Python 3.11, Flask |
| Base de données | PostgreSQL (SQLAlchemy 2.0) |
| Authentification | bcrypt |
| Visualisations | Plotly 5.22.0 |
| Export Excel | openpyxl, pandas |
| Export PDF | ReportLab |
| Serveur WSGI | Gunicorn |
| Déploiement | Render |

---

## Structure du projet

```
sga-academique/
├── app.py                  # Point d'entrée, routeur principal, callbacks globaux
├── auth.py                 # Fonctions d'authentification (login, register)
├── models.py               # Modèles SQLAlchemy (User, Student, Course, ...)
├── config.py               # Configuration (clé secrète, titre)
├── requirements.txt        # Dépendances Python
├── render.yaml             # Configuration de déploiement Render
├── Procfile                # Commande de démarrage Gunicorn
│
├── pages/
│   ├── welcome.py          # Page de bienvenue après connexion
│   ├── login.py            # Connexion et inscription
│   ├── dashboard.py        # Tableau de bord
│   ├── students.py         # Gestion des étudiants
│   ├── courses.py          # Gestion des cours
│   ├── sessions.py         # Gestion des séances et présences
│   ├── grades.py           # Saisie et import des notes
│   ├── analytics.py        # Analyses statistiques
│   ├── reports.py          # Génération de rapports PDF
│   └── components.py       # Composants réutilisables (sidebar, topbar, card...)
│
├── utils/
│   ├── db.py               # Initialisation et accès à la base de données
│   ├── excel_helper.py     # Génération et parsing de fichiers Excel
│   ├── pdf_gen.py          # Génération de rapports PDF
│   └── format.py           # Formatage des nombres en français
│
└── assets/
    └── style.css           # Feuille de styles globale
```

---

## Modeles de donnees

### User
| Champ | Type | Description |
|---|---|---|
| id | Integer | Clé primaire |
| username | String | Identifiant unique |
| email | String | Adresse email unique |
| password | String | Hash bcrypt |
| role | String | `admin` ou `teacher` |
| full_name | String | Nom complet |
| is_active | Boolean | Compte actif |

### Student
| Champ | Type | Description |
|---|---|---|
| id | Integer | Clé primaire |
| student_code | String | Code unique (ex : ETU-2024-001) |
| first_name | String | Prénom |
| last_name | String | Nom |
| email | String | Email unique |
| birth_date | Date | Date de naissance |
| is_active | Boolean | Inscrit actif |

### Course
| Champ | Type | Description |
|---|---|---|
| id | Integer | Clé primaire |
| code | String | Code cours (ex : INF101) |
| label | String | Libellé |
| total_hours | Integer | Volume horaire |
| teacher | String | Nom de l'enseignant |
| color | String | Couleur hexadécimale |

### Session
| Champ | Type | Description |
|---|---|---|
| id | Integer | Clé primaire |
| course_id | Integer | Clé étrangère vers Course |
| date | Date | Date de la séance |
| duration | Integer | Durée en minutes |
| theme | String | Thème abordé |
| room | String | Salle |

### Grade
| Champ | Type | Description |
|---|---|---|
| id | Integer | Clé primaire |
| student_id | Integer | Clé étrangère vers Student |
| course_id | Integer | Clé étrangère vers Course |
| score | Float | Note sur 20 |
| coefficient | Float | Coefficient |
| label | String | Libellé de l'évaluation |

### Attendance
| Champ | Type | Description |
|---|---|---|
| id | Integer | Clé primaire |
| session_id | Integer | Clé étrangère vers Session |
| student_id | Integer | Clé étrangère vers Student |
| is_absent | Boolean | Absent |
| is_late | Boolean | En retard |
| justified | Boolean | Absence justifiée |

---

## Installation locale

### Prérequis

- Python 3.11 ou supérieur
- PostgreSQL installé et en cours d'exécution

### Etapes

**1. Clonage du dépôt**

```bash
git clone https://github.com/awa-gueye/Data_visualisation_SGA.git
```

**2. Création d'un environnement virtuel**

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

**3. Installations des dépendances**

```bash
pip install -r requirements.txt
```

**4. Configuration des variables d'environnement**

Création d'un fichier `.env` à la racine du projet :

```env
DATABASE_URL=postgresql://user:password@localhost:5432/sga_db
SECRET_KEY=votre_cle_secrete_aleatoire
```

**5. Création la base de données PostgreSQL**

```sql
CREATE DATABASE sga_db;
CREATE USER sga_user WITH PASSWORD 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON DATABASE sga_db TO sga_user;
```

**6. Lancement de l'application**

```bash
python app.py
```

L'application est accessible sur http://localhost:8050.  
La base de données est initialisée automatiquement au premier démarrage avec un compte `admin / admin123`.

---

## Deploiement sur Render

Le projet est configuré pour un déploiement automatique sur Render via le fichier `render.yaml`.

### Variables d'environnement requises

| Variable | Description |
|---|---|
| `DATABASE_URL` | URL de connexion PostgreSQL (Internal Database URL) |
| `SECRET_KEY` | Clé secrète Flask (générée automatiquement par Render) |
| `PYTHON_VERSION` | Version Python (3.11.0) |

### Etapes de déploiement

1. Créer un compte sur render.com
2. Connecter le dépôt GitHub
3. Créer un nouveau service Web en pointant sur le dépôt
4. Render détecte automatiquement `render.yaml` et configure le service
5. Créer une base de données PostgreSQL sur Render et lier son URL interne à la variable `DATABASE_URL`
6. Tout push sur la branche `main` déclenche un redéploiement automatique

### Commande de démarrage

```bash
gunicorn app:server --workers 2 --threads 4 --bind 0.0.0.0:$PORT --timeout 120
```
---

## Utilisation

### Connexion

Se connecter avec les identifiants admin par défaut : `admin` / `admin123`.  
Il est fortement recommandé de changer ce mot de passe après la première connexion.

### Import Excel

Les modèles Excel pour l'import des notes et des étudiants sont téléchargeables directement depuis l'interface via le bouton "Télécharger le template".

### Génération de rapports PDF

Les rapports individuels et collectifs sont générables depuis la page "Rapports". Ils incluent les notes, les moyennes et le taux d'absence par étudiant.

---

## Securite

- Les mots de passe sont hachés avec bcrypt (coût 12)
- Les sessions sont stockées côté client avec une clé secrète Flask
- Les routes sont protégées par un garde d'authentification dans le routeur principal
- Les requêtes SQL utilisent SQLAlchemy ORM (protection contre les injections SQL)

---

## Licence

Projet académique — usage éducatif.
