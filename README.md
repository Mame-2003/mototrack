# MotoTrack

MotoTrack est une plateforme web IoT de gestion de motos de livraison. Elle associe un tableau de bord Django, une API REST, une carte Leaflet et un boîtier ESP32 + GPS NEO-6M.

Le projet reste volontairement simple à présenter : une application Django, une base PostgreSQL et deux rôles (responsable et livreur).

## Fonctions principales

- Gestion des motos, livreurs, affectations et missions.
- Une seule affectation active par moto et par livreur.
- OTP à 6 chiffres généré automatiquement pour chaque mission.
- Validation OTP avec création d'une preuve horodatée.
- API GPS protégée par l'en-tête `X-API-Key`.
- Carte Leaflet avec positions récentes, rafraîchissement et historique.
- API REST authentifiée par session ou jeton.
- Interface responsive pour responsable et livreur.
- PostgreSQL local en test, Supabase PostgreSQL en production.

## Structure

```text
MotoTrack/
├── arduino/mototrack_esp32.ino
├── core/
│   ├── management/commands/seed_demo.py
│   ├── migrations/0001_initial.py
│   ├── admin.py, models.py, forms.py
│   ├── serializers.py, permissions.py
│   ├── api_views.py, api_urls.py, views.py
│   └── tests.py
├── mototrack/
│   ├── settings.py, urls.py
│   └── asgi.py, wsgi.py
├── static/css/app.css
├── static/js/app.js, map.js
├── templates/
├── .env.example
├── render.yaml
├── requirements.txt
└── manage.py
```

## 1. Installation locale

### Prérequis

- Python 3.11 ou 3.12
- PostgreSQL 15 ou supérieur
- Git (facultatif)
- Un ordinateur et l'ESP32 sur le même Wi-Fi

Dans PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Créer PostgreSQL local

Ouvrir `psql` avec le compte administrateur PostgreSQL :

```sql
CREATE USER mototrack WITH PASSWORD 'mototrack';
CREATE DATABASE mototrack OWNER mototrack;
GRANT ALL PRIVILEGES ON DATABASE mototrack TO mototrack;
```

Vérifier cette ligne dans `.env` :

```env
DATABASE_URL=postgresql://mototrack:mototrack@localhost:5432/mototrack
DB_SSL=False
```

### Initialiser Django

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Pour obtenir rapidement des comptes et données de démonstration :

```powershell
python manage.py seed_demo
```

Comptes de démonstration :

- Responsable : `responsable` / `MotoTrack2026!`
- Livreur : `livreur` / `MotoTrack2026!`

La commande réinitialise aussi ces deux mots de passe si les comptes existent déjà.

Changez ces mots de passe avant toute démonstration publique.

## 2. Test sur le même réseau Wi-Fi

L'ordinateur serveur, le téléphone de test et l'ESP32 doivent utiliser le même réseau Wi-Fi.

### Trouver l'adresse IP du PC

Sous Windows :

```powershell
ipconfig
```

Repérer l'`Adresse IPv4` de la carte Wi-Fi, par exemple `192.168.1.20`. Ajouter cette adresse dans `.env` :

```env
ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.20
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://192.168.1.20:8000
```

Lancer Django en écoute réseau :

```powershell
python manage.py runserver 0.0.0.0:8000
```

Depuis un téléphone, ouvrir `http://192.168.1.20:8000`. Si la page ne répond pas, autoriser Python ou le port TCP 8000 dans le pare-feu Windows.

## 3. Tester l'API GPS avec Postman

1. Créer une moto et noter son identifiant numérique.
2. Choisir une valeur `GPS_API_KEY` dans `.env`.
3. Envoyer une requête `POST` vers :

```text
http://127.0.0.1:8000/api/gps/positions/
```

Headers :

```text
Content-Type: application/json
X-API-Key: changer-cette-cle-gps
```

Body JSON :

```json
{
  "moto_id": 1,
  "latitude": 14.7167000,
  "longitude": -17.4677000,
  "date": "2026-06-13",
  "heure": "14:30:00"
}
```

Une réponse HTTP `201 Created` confirme l'enregistrement. La position apparaît dans **Suivi GPS**.

Test équivalent avec PowerShell :

```powershell
$headers = @{"X-API-Key"="changer-cette-cle-gps"}
$body = '{"moto_id":1,"latitude":14.7167,"longitude":-17.4677}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/gps/positions/" -Headers $headers -ContentType "application/json" -Body $body
```

## 4. ESP32 + NEO-6M

Le firmware se trouve dans `arduino/mototrack_esp32.ino`.

### Branchement conseillé

| NEO-6M | ESP32 |
|---|---|
| VCC | 3.3V ou 5V selon le module |
| GND | GND |
| TX | GPIO 16 (RX2) |
| RX | GPIO 17 (TX2) |

Dans l'IDE Arduino :

1. Installer le support de carte ESP32.
2. Installer `TinyGPSPlus` et `ArduinoJson`.
3. Modifier `WIFI_SSID`, `WIFI_PASSWORD`, `API_KEY` et `MOTO_ID`.
4. En local, utiliser `http://IP_DU_PC:8000/api/gps/positions/`.
5. Téléverser le programme et ouvrir le moniteur série à 115200 bauds.
6. Tester à l'extérieur : le NEO-6M peut demander plusieurs minutes pour son premier signal.

L'URL `localhost` ne doit jamais être utilisée dans l'ESP32 : elle désignerait l'ESP32 lui-même.

## 5. API REST

| Méthode | Route | Accès |
|---|---|---|
| POST | `/api/auth/token/` | Identifiant/mot de passe |
| GET/POST | `/api/motos/` | Responsable |
| GET/POST | `/api/livreurs/` | Responsable |
| GET/POST | `/api/affectations/` | Responsable |
| GET/POST | `/api/missions/` | Selon rôle |
| POST | `/api/missions/{id}/valider_otp/` | Livreur concerné/responsable |
| POST | `/api/gps/positions/` | Clé GPS |
| GET | `/api/gps/latest/` | Utilisateur connecté |
| GET | `/api/gps/history/{moto_id}/` | Utilisateur connecté |
| GET | `/api/preuves/` | Selon rôle |
| GET | `/api/alerts/` | Alertes autorisées pour l’utilisateur |
| GET | `/api/alerts/unread-count/` | Nombre d’alertes non lues |
| POST | `/api/alerts/{id}/mark-read/` | Marquer une alerte comme lue |
| GET | `/api/driver/profile/` | Profil en lecture seule du livreur connecté |
| GET | `/api/driver/missions/` | Missions du livreur connecté |
| GET | `/api/driver/missions/{id}/` | Détail d’une mission autorisée |
| POST | `/api/driver/missions/{id}/validate-otp/` | Validation OTP |
| GET | `/api/driver/deliveries/` | Historique des livraisons |
| GET | `/api/driver/alerts/` | Alertes du livreur |
| POST | `/api/driver/alerts/{id}/mark-read/` | Marquer une alerte comme lue |

Pour obtenir un jeton :

```json
POST /api/auth/token/
{"username": "responsable", "password": "mot-de-passe"}
```

Puis envoyer `Authorization: Token VOTRE_JETON`.

## Alertes automatiques

MotoTrack crée automatiquement une alerte lorsqu’une position GPS sort des limites du Sénégal ou lorsqu’une mission est validée par OTP.

Pour vérifier les motos affectées qui n’ont envoyé aucune position depuis plus de dix minutes :

```powershell
python manage.py check_gps_alerts
```

Le délai peut être modifié dans `.env` :

```env
GPS_DISCONNECT_MINUTES=10
```

Sur Render, cette commande peut être exécutée par un Cron Job avec une fréquence adaptée. La déduplication empêche la création répétée d’une alerte non lue pour la même moto.

Les missions acceptent désormais une latitude et une longitude de destination. Le responsable peut aussi sélectionner la destination directement sur la carte du formulaire. La page de détail trace ensuite l’itinéraire entre la dernière position de la moto et le client.

## Espace Livreur

Après connexion, un compte livreur est redirigé vers `/mon-espace/`. Cet espace contient :

- tableau de bord personnel et statistiques ;
- profil professionnel en lecture seule ;
- moto actuellement affectée et dernier signal GPS ;
- missions filtrées par le compte connecté ;
- détail de mission, navigation Google Maps et validation OTP ;
- historique filtrable des livraisons ;
- preuve officielle téléchargeable en PDF ;
- alertes limitées aux missions assignées et annulées.

Les vues et API refusent les responsables et filtrent systématiquement les objets avec le livreur lié à l’utilisateur connecté.

## 6. Tests

Créer temporairement une base PostgreSQL de test accessible au compte configuré, puis :

```powershell
python manage.py check
python manage.py test
```

Les tests couvrent la double affectation, la validation OTP et la protection de l'API GPS.

## 7. Supabase PostgreSQL

1. Créer un projet sur Supabase.
2. Ouvrir **Project Settings > Database**.
3. Copier l'URI du **Transaction pooler** ou du **Session pooler**.
4. Remplacer `[YOUR-PASSWORD]` par le mot de passe de la base.
5. Dans Render, définir :

```env
DATABASE_URL=postgresql://postgres.PROJET:MOT_DE_PASSE@aws-0-region.pooler.supabase.com:6543/postgres
DB_SSL=True
```

Utiliser exclusivement la chaîne fournie par votre projet Supabase. Ne jamais publier le mot de passe dans Git.

## 8. Déploiement Render

Le fichier `render.yaml` décrit le service.

1. Envoyer le projet vers un dépôt GitHub.
2. Dans Render, choisir **New > Blueprint** et sélectionner le dépôt.
3. Renseigner `DATABASE_URL`, `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS`.
4. Exemple :

```env
ALLOWED_HOSTS=mototrack.onrender.com
CSRF_TRUSTED_ORIGINS=https://mototrack.onrender.com
```

5. Le build installe les dépendances, collecte les fichiers statiques et applique les migrations.
6. Après le premier déploiement, ouvrir le Shell Render :

```bash
python manage.py createsuperuser
```

Pour l'ESP32 en production :

```cpp
const char* API_URL = "https://mototrack.onrender.com/api/gps/positions/";
```

Le plan gratuit Render peut mettre le service en veille. Pour un suivi GPS continu, utiliser une offre sans mise en veille.

## 9. Passer du local à la production

Le code ne change pas. Seules les variables d'environnement changent :

| Variable | Local | Production |
|---|---|---|
| `DEBUG` | `True` | `False` |
| `DATABASE_URL` | PostgreSQL local | Supabase |
| `DB_SSL` | `False` | `True` |
| `ALLOWED_HOSTS` | IP locale | Domaine Render |
| `CSRF_TRUSTED_ORIGINS` | URL locale | URL HTTPS Render |
| `GPS_API_KEY` | Clé de test | Clé forte différente |

Redémarrer Django ou redéployer Render après toute modification.

## Sécurité et limites académiques

- Les mots de passe sont hachés par Django.
- Les pages utilisent session, CSRF et permissions par rôle.
- L'API GPS utilise une clé simple, adaptée au périmètre académique.
- En production réelle, on ajouterait rotation des clés, HTTPS imposé, limitation de débit, journal d'audit, stockage média externe et envoi OTP par SMS.
