# 🤖 Bot de Veille IA (LLM & Génération d'Images) pour Telegram

Un bot automatisé, 100% gratuit et sans serveur, qui analyse quotidiennement les flux d'actualités sur les **LLM** et l'**IA Générative d'Images**, génère une synthèse intelligente via **Google Gemini Flash**, et l'envoie chaque matin sur votre compte ou canal **Telegram**.

---

## 📋 Fonctionnalités

* **Multi-sources ciblées** : OpenAI News, Hugging Face Blog, DeepMind, Stability AI, ComfyUI, ArXiv (cs.CL & cs.CV), Reddit (r/LocalLLaMA, r/StableDiffusion).
* **Synthèse intelligente par IA** : Filtrage des doublons, mise en contexte des avancées réelles et classification claire (LLM vs Images/Vidéos).
* **Format Telegram élégant** : Titres en gras, résumés percutants et liens directs vers les sources.
* **100% Gratuit & Autonome** : Hébergé et exécuté gratuitement chaque jour via **GitHub Actions** (aucune machine ou VPS à gérer).

---

## 🚀 Guide d'installation étape par étape (10 minutes)

### Étape 1 : Créer votre bot Telegram

1. Ouvrez Telegram et cherchez le compte officiel **[@BotFather](https://t.me/BotFather)**.
2. Envoyez la commande `/newbot`.
3. Donnez un nom à votre bot (ex: `Mon Bot Veille IA`) puis un nom d'utilisateur se terminant par `bot` (ex: `ma_veille_ia_bot`).
4. **Notez le Token HTTP API** fourni (ex: `7123456789:AAFn...`). C'est votre `TELEGRAM_BOT_TOKEN`.
5. Lancez votre bot en cliquant sur son lien et en appuyant sur **Démarrer** (`/start`).

---

### Étape 2 : Récupérer votre identifiant Telegram (`CHAT_ID`)

* **Pour recevoir les actus en message privé :**
  1. Cherchez **[@userinfobot](https://t.me/userinfobot)** sur Telegram et appuyez sur Démarrer.
  2. Le bot vous répond avec votre `Id` numérique (ex: `123456789`). C'est votre `TELEGRAM_CHAT_ID`.
* **Pour recevoir les actus dans un canal ou groupe :**
  1. Créez un canal ou groupe Telegram, ajoutez votre bot comme **Administrateur**.
  2. Vous pouvez utiliser le bot **[@RawDataBot](https://t.me/RawDataBot)** pour récupérer l'ID du groupe/canal (il commence généralement par un tiret, ex: `-100123456789`).

---

### Étape 3 : Obtenir une clé d'API Gemini (Gratuit)

1. Rendez-vous sur **[Google AI Studio](https://aistudio.google.com/)**.
2. Connectez-vous avec votre compte Google et cliquez sur **Get API key**.
3. Créez une nouvelle clé et copiez-la. C'est votre `GEMINI_API_KEY`.

---

### Étape 4 : Déployer sur votre compte GitHub

1. Créez un nouveau dépôt sur [GitHub](https://github.com/new) (en mode **Public** ou **Privé**).
2. Dans le dossier de ce projet, initialisez git et poussez le code vers votre dépôt :

```bash
git init
git add .
git commit -m "Initial commit - Bot de veille IA"
git branch -M main
git remote add origin https://github.com/VOTRE_PSEUDO/VOTRE_DEPOT.git
git push -u origin main
```

---

### Étape 5 : Configurer les Secrets GitHub

1. Sur votre dépôt GitHub, allez dans l'onglet **Settings** > **Secrets and variables** > **Actions**.
2. Cliquez sur **New repository secret** et ajoutez ces 3 variables :
   * `GEMINI_API_KEY` : La clé API Google AI Studio.
   * `TELEGRAM_BOT_TOKEN` : Le token fourni par @BotFather.
   * `TELEGRAM_CHAT_ID` : Votre ID Telegram personnel ou celui du canal.

---

### Étape 6 : Tester le bot immédiatement !

1. Allez dans l'onglet **Actions** de votre dépôt GitHub.
2. Dans le menu de gauche, cliquez sur **Veille IA Quotidienne**.
3. Cliquez sur le bouton déroulant **Run workflow** à droite, puis validez.
4. En moins de 30 secondes, GitHub Actions exécutera le script et vous recevrez votre premier condensé de veille directement sur Telegram !

Le bot s'exécutera ensuite automatiquement chaque matin à 7h00 UTC (8h00 / 9h00 en France).

