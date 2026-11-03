#!/usr/bin/env python3
"""
Bot de veille IA (LLM & Génération d'Images) pour Telegram.
Exécuté automatiquement chaque jour via GitHub Actions.
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
import requests
import feedparser
from dateutil import parser as date_parser

# Configuration des flux RSS spécialisés
RSS_FEEDS = [
    # --- LLM & Modèles de Langage ---
    {"category": "LLM", "source": "OpenAI News", "url": "https://openai.com/news/rss.xml"},
    {"category": "LLM", "source": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"category": "LLM", "source": "Google DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml"},
    {"category": "LLM", "source": "Reddit r/LocalLLaMA", "url": "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day"},
    
    # --- Image & Vidéo Générative ---
    {"category": "Image", "source": "Stability AI News", "url": "https://stability.ai/news?format=rss"},
    {"category": "Image", "source": "Reddit r/StableDiffusion", "url": "https://www.reddit.com/r/StableDiffusion/top/.rss?t=day"},
    {"category": "Image", "source": "ComfyUI Releases", "url": "https://github.com/comfyanonymous/ComfyUI/releases.atom"},
    
    # --- Recherche & Open Source Global ---
    {"category": "Research", "source": "ArXiv cs.CL (Langage)", "url": "https://rss.arxiv.org/rss/cs.CL"},
    {"category": "Research", "source": "ArXiv cs.CV (Vision)", "url": "https://rss.arxiv.org/rss/cs.CV"},
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) IANewsBot/1.0"


def fetch_recent_articles(hours_back: int = 30, max_per_feed: int = 4):
    """Récupère les articles récents des flux RSS."""
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    collected_articles = []

    print(f"[*] Récupération des flux RSS (dernières {hours_back} heures)...")

    for feed_info in RSS_FEEDS:
        url = feed_info["url"]
        category = feed_info["category"]
        source_name = feed_info["source"]

        try:
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(url, headers=headers, timeout=12)
            if response.status_code != 200:
                print(f"[-] Erreur HTTP {response.status_code} sur {source_name}")
                continue

            feed = feedparser.parse(response.content)
            count = 0

            for entry in feed.entries:
                if count >= max_per_feed:
                    break

                # Extraction de la date de publication
                pub_date = None
                if hasattr(entry, "published"):
                    try:
                        pub_date = date_parser.parse(entry.published)
                    except Exception:
                        pass
                elif hasattr(entry, "updated"):
                    try:
                        pub_date = date_parser.parse(entry.updated)
                    except Exception:
                        pass

                # Normalisation en UTC
                if pub_date:
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    else:
                        pub_date = pub_date.astimezone(timezone.utc)

                    if pub_date < cutoff_time:
                        continue

                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "")[:350].strip()

                if title and link:
                    collected_articles.append({
                        "category": category,
                        "source": source_name,
                        "title": title,
                        "link": link,
                        "summary": summary
                    })
                    count += 1

            print(f"[+] {source_name}: {count} articles récupérés.")

        except Exception as e:
            print(f"[-] Erreur lors de la lecture de {source_name}: {e}")

    return collected_articles


def generate_telegram_summary_gemini(articles, gemini_api_key: str):
    """Appelle l'API Gemini pour générer une synthèse au format HTML Telegram."""
    if not articles:
        return "Aucune nouvelle actualité majeure détectée lors des dernières 24h."

    articles_text = ""
    for idx, art in enumerate(articles, 1):
        articles_text += (
            f"[{idx}] Catégorie: {art['category']} | Source: {art['source']}\n"
            f"Titre: {art['title']}\n"
            f"Lien: {art['link']}\n"
            f"Extrait: {art['summary']}\n\n"
        )

    prompt = f"""
Tu es un analyste expert en intelligence artificielle générative (LLM, modèles d'images et de vidéo).
Voici une sélection brute d'articles et actualités des dernières 24 heures :

{articles_text}

Ta mission est de rédiger un condensé quotidien de veille pour un canal Telegram.
RÈGLES DE FORMATAGE IMPORTANTES POUR TELEGRAM :
- Écris en français clair, percutant et professionnel.
- Utilise UNIQUEMENT les balises HTML supportées par Telegram : <b>gras</b>, <i>italique</i>, et <a href="URL">titre du lien</a>.
- N'utilise PAS de balises Markdown (pas d'étoiles **, ni de crochets [lien](url)). Uniquement du HTML valide.
- Ne répète pas les informations en doublon. Sélectionne les plus importantes (environ 5 à 8 actus clés au total).

STRUCTURE DU MESSAGE :
📢 <b>VEILLE IA DU JOUR | {datetime.now().strftime('%d/%m/%Y')}</b>

🧠 <b>LLM & Modèles de Langage</b>
- Pour chaque actualité majeure : <b>Titre ou Sujet</b> : explication concise de l'impact en 1 à 2 phrases. (<a href="URL">Lien</a>)

🎨 <b>IA Image & Vidéo Générative</b>
- Pour chaque actualité majeure : <b>Titre ou Sujet</b> : explication concise de l'impact en 1 à 2 phrases. (<a href="URL">Lien</a>)

💡 <b>Le point clé du jour</b>
(Une courte phrase de synthèse sur la tendance ou la percée marquante du jour).
"""

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048
        }
    }

    print("[*] Génération de la synthèse avec Gemini...")
    response = requests.post(api_url, json=payload, timeout=45)
    
    # En cas de modèle 2.5 non disponible, repli sur 1.5-flash
    if response.status_code != 200:
        print(f"[-] Erreur {response.status_code} avec gemini-2.5-flash, essai avec gemini-1.5-flash...")
        fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
        response = requests.post(fallback_url, json=payload, timeout=45)

    if response.status_code != 200:
        raise RuntimeError(f"Erreur API Gemini: {response.status_code} - {response.text}")

    data = response.json()
    summary = data["candidates"][0]["content"]["parts"][0]["text"]
    return summary


def send_to_telegram(message: str, bot_token: str, chat_id: str):
    """Envoie le message sur Telegram en gérant la limite de 4096 caractères."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Telegram limite chaque message à 4096 caractères
    max_len = 4000
    chunks = []
    
    if len(message) <= max_len:
        chunks = [message]
    else:
        parts = message.split("\n\n")
        current_chunk = ""
        for p in parts:
            if len(current_chunk) + len(p) + 2 < max_len:
                current_chunk += p + "\n\n"
            else:
                chunks.append(current_chunk.strip())
                current_chunk = p + "\n\n"
        if current_chunk:
            chunks.append(current_chunk.strip())

    print(f"[*] Envoi de {len(chunks)} message(s) vers Telegram (chat_id: {chat_id})...")

    for i, chunk in enumerate(chunks, 1):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        res = requests.post(url, json=payload, timeout=15)
        
        # En cas d'erreur HTML (ex: balise non fermée par le LLM), envoi de secours en texte brut
        if res.status_code != 200:
            print(f"[-] Erreur HTML Telegram ({res.text}), tentative d'envoi en texte brut...")
            payload.pop("parse_mode")
            res = requests.post(url, json=payload, timeout=15)

        if res.status_code != 200:
            print(f"[-] Échec d'envoi Telegram chunk {i}: {res.status_code} - {res.text}")
        else:
            print(f"[+] Chunk {i}/{len(chunks)} envoyé avec succès sur Telegram.")
        time.sleep(1)


def main():
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not gemini_api_key or not telegram_bot_token or not telegram_chat_id:
        print("[-] ERREUR: Variables d'environnement manquantes.")
        print("Assurez-vous de définir : GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")
        sys.exit(1)

    # 1. Récupération des flux
    articles = fetch_recent_articles(hours_back=30)
    print(f"[*] Total d'articles trouvés : {len(articles)}")

    # 2. Synthèse via LLM
    summary = generate_telegram_summary_gemini(articles, gemini_api_key)

    # 3. Envoi sur Telegram
    send_to_telegram(summary, telegram_bot_token, telegram_chat_id)
    print("[*] Veille terminée avec succès !")


if __name__ == "__main__":
    main()

