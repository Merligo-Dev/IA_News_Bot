#!/usr/bin/env python3
"""
Bot de veille IA (LLM & Génération d'Images) pour Telegram.
Exécuté automatiquement chaque jour via GitHub Actions.
Envoie deux messages distincts et complets avec liens directs cliquables.
"""

import os
import sys
import time
import re
import html
from datetime import datetime, timezone, timedelta
import requests
import feedparser
from dateutil import parser as date_parser

# Configuration des flux RSS spécialisés
RSS_FEEDS = [
    # --- Catégorie LLM & Modèles de Langage ---
    {"category": "LLM", "source": "OpenAI News", "url": "https://openai.com/news/rss.xml"},
    {"category": "LLM", "source": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"category": "LLM", "source": "Google DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml"},
    {"category": "LLM", "source": "Reddit r/LocalLLaMA", "url": "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day"},
    {"category": "LLM", "source": "ArXiv cs.CL (Langage)", "url": "https://rss.arxiv.org/rss/cs.CL"},

    # --- Catégorie Image & Vidéo Générative ---
    {"category": "Image", "source": "Stability AI News", "url": "https://stability.ai/news?format=rss"},
    {"category": "Image", "source": "Reddit r/StableDiffusion", "url": "https://www.reddit.com/r/StableDiffusion/top/.rss?t=day"},
    {"category": "Image", "source": "ComfyUI Releases", "url": "https://github.com/comfyanonymous/ComfyUI/releases.atom"},
    {"category": "Image", "source": "ArXiv cs.CV (Vision)", "url": "https://rss.arxiv.org/rss/cs.CV"},
]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

REDDIT_HEADERS = {
    "User-Agent": "python:ia-news-bot:v1.2 (by /u/MerligoDev)"
}


def fetch_recent_articles(hours_back: int = 36, max_per_feed: int = 5):
    """Récupère les articles récents des flux RSS avec headers adaptés."""
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    collected_articles = []

    print(f"[*] Récupération des flux RSS (dernières {hours_back} heures)...")

    for feed_info in RSS_FEEDS:
        url = feed_info["url"]
        category = feed_info["category"]
        source_name = feed_info["source"]

        headers = REDDIT_HEADERS if "reddit.com" in url else DEFAULT_HEADERS

        try:
            response = requests.get(url, headers=headers, timeout=12)
            if response.status_code == 429:
                print(f"[-] Rate limit (429) sur {source_name}, pause et retry...")
                time.sleep(2)
                response = requests.get(url, headers=headers, timeout=15)

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
                for date_field in ["published", "updated", "pubDate"]:
                    if hasattr(entry, date_field):
                        try:
                            pub_date = date_parser.parse(getattr(entry, date_field))
                            break
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


def sanitize_telegram_html(text: str) -> str:
    """Assure la conformité absolue du code HTML avec Telegram."""
    text = text.strip()
    # 1. Enlever d'éventuels blocs de code markdown ```html ... ```
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*\n?", "", text)
        text = re.sub(r"\n?\s*```$", "", text)
    text = text.strip()

    # 2. Remplacer les balises parasites <br>, <p> par des sauts de ligne
    text = re.sub(r"<(?:br|hr)\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p>", "", text, flags=re.IGNORECASE)

    # 3. Convertir d'éventuels résidus markdown classiques
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r'<a href="\2">\1</a>', text)

    # 4. Découpage par balises HTML autorisées
    allowed_tag_pattern = re.compile(
        r"(</?(?:b|i|u|s|code|pre|blockquote)>|<a\s+href=[\"'][^\"']*[\"']>|</a>)",
        re.IGNORECASE
    )

    tokens = allowed_tag_pattern.split(text)
    sanitized_parts = []
    open_tags = []

    for token in tokens:
        if allowed_tag_pattern.fullmatch(token):
            tag_lower = token.lower()
            if tag_lower.startswith("</"):
                tag_name = tag_lower[2:-1].strip()
                if open_tags and open_tags[-1] == tag_name:
                    open_tags.pop()
                    sanitized_parts.append(token)
                elif tag_name in open_tags:
                    while open_tags and open_tags[-1] != tag_name:
                        sanitized_parts.append(f"</{open_tags.pop()}>")
                    if open_tags:
                        open_tags.pop()
                    sanitized_parts.append(token)
            elif tag_lower.startswith("<a"):
                # Interdiction de balises <a> imbriquées (erreur Telegram 400)
                if "a" in open_tags:
                    while open_tags and open_tags[-1] != "a":
                        sanitized_parts.append(f"</{open_tags.pop()}>")
                    if open_tags:
                        open_tags.pop()
                    sanitized_parts.append("</a>")

                # Extraction et échappement sécurisé de l'URL
                m = re.search(r'href=[\"\']([^\"\']*)[\"\']', token, re.IGNORECASE)
                if m:
                    raw_url = m.group(1).strip()
                    clean_url = html.escape(html.unescape(raw_url), quote=True)
                    open_tags.append("a")
                    sanitized_parts.append(f'<a href="{clean_url}">')
            else:
                tag_name = tag_lower[1:-1].strip()
                open_tags.append(tag_name)
                sanitized_parts.append(token)
        else:
            unescaped = html.unescape(token)
            escaped = html.escape(unescaped, quote=False)
            sanitized_parts.append(escaped)

    while open_tags:
        sanitized_parts.append(f"</{open_tags.pop()}>")

    return "".join(sanitized_parts)


def html_to_plain_text_with_links(html_text: str) -> str:
    """En cas de repli secours, convertit les liens HTML en liens textuels cliquables."""
    # Convertit <a href="URL">Titre</a> -> Titre (URL)
    text = re.sub(r'<a\s+href=[\"\']([^\"\']*)[\"\']>([^<]*)</a>', r'\2 (\1)', html_text, flags=re.IGNORECASE)
    # Supprime toutes les autres balises HTML
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()


def call_gemini(prompt: str, gemini_api_key: str) -> str:
    """Effectue un appel à Gemini avec repli sur 1.5-flash."""
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
    }

    response = requests.post(api_url, json=payload, timeout=45)
    if response.status_code != 200:
        fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
        response = requests.post(fallback_url, json=payload, timeout=45)

    if response.status_code != 200:
        raise RuntimeError(f"Erreur API Gemini: {response.status_code} - {response.text}")

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def generate_category_summary(articles, category_name: str, emoji: str, gemini_api_key: str) -> str:
    """Génère un message détaillé dédié à une catégorie spécifique avec liens cliquables."""
    if not articles:
        return f"{emoji} <b>VEILLE IA | {category_name.upper()}</b>\n\nAucune nouvelle mise à jour majeure dans cette catégorie aujourd'hui."

    articles_text = ""
    for idx, art in enumerate(articles, 1):
        articles_text += (
            f"[{idx}] Source: {art['source']}\n"
            f"Titre: {art['title']}\n"
            f"Lien exact: {art['link']}\n"
            f"Extrait: {art['summary']}\n\n"
        )

    prompt = f"""
Tu es un journaliste et expert technique en intelligence artificielle.
Voici les actualités brutes récentes concernant la catégorie : {category_name}

{articles_text}

Ta mission est de rédiger un condensé complet et soigné pour Telegram.
RÈGLES CAPITALES DE LIENS ET FORMATAGE :
1. LE TITRE DE CHAQUE ARTICLE DOIT ÊTRE UN LIEN CLIQUABLE EN BLEU :
   Format obligatoire pour chaque actualité :
   🔹 <a href="URL_EXACTE"><b>Titre traduit ou résumé percutant</b></a> (Source)
   Impact : explication claire et précise en 1 ou 2 phrases de la nouveauté.
   🔗 <a href="URL_EXACTE">Consulter la source ↗</a>

2. UTILISE UNIQUEMENT LE HTML TELEGRAM : <b>, <i>, <a href="...">.
3. N'utilise JAMAIS de Markdown (pas de crochets [texte](url), pas d'étoiles **).
4. N'entoure JAMAIS le texte de blocs de code ```html.
5. Écris toute perluète (&) sous la forme &amp; (ex: R&amp;D).
6. Sélectionne les 4 à 6 actualités les plus pertinentes de cette liste.

STRUCTURE ATTENDUE :
{emoji} <b>VEILLE IA : {category_name.upper()} | {datetime.now().strftime('%d/%m/%Y')}</b>

(Insère ici les 4 à 6 actualités au format ci-dessus, séparées par un saut de ligne)

💡 <b>Analyse &amp; Tendance Clé :</b>
(Une courte réflexion de 2 phrases sur ce que ces annonces signifient concrètement pour l'écosystème).
"""
    return call_gemini(prompt, gemini_api_key)


def send_to_telegram(message: str, bot_token: str, chat_id: str):
    """Envoie un message sur Telegram avec assainissement HTML et gestion de taille."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    max_len = 3900
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

    for i, raw_chunk in enumerate(chunks, 1):
        clean_chunk = sanitize_telegram_html(raw_chunk)

        payload = {
            "chat_id": chat_id,
            "text": clean_chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        res = requests.post(url, json=payload, timeout=15)
        
        # En cas d'erreur de parse HTML, repli intelligent conservant les liens en clair
        if res.status_code != 200:
            print(f"[-] Erreur HTML Telegram ({res.text}), repli avec liens cliquables textuels...")
            payload["text"] = html_to_plain_text_with_links(clean_chunk)
            payload.pop("parse_mode")
            res = requests.post(url, json=payload, timeout=15)

        if res.status_code != 200:
            print(f"[-] Échec d'envoi Telegram chunk {i}: {res.status_code} - {res.text}")
        else:
            print(f"[+] Message envoyé avec succès sur Telegram.")
        time.sleep(1)


def main():
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not gemini_api_key or not telegram_bot_token or not telegram_chat_id:
        print("[-] ERREUR: Variables d'environnement manquantes.")
        sys.exit(1)

    # 1. Récupération des flux
    articles = fetch_recent_articles(hours_back=36)
    print(f"[*] Total d'articles trouvés : {len(articles)}")

    llm_articles = [a for a in articles if a["category"] in ["LLM", "Research"]]
    img_articles = [a for a in articles if a["category"] in ["Image", "Research"]]

    # 2. Génération et envoi du Message 1 : LLM & Modèles de Langage
    print("[*] Génération de la veille LLM...")
    llm_summary = generate_category_summary(llm_articles, "LLM & Modèles de Langage", "🧠", gemini_api_key)
    print("[*] Envoi du message LLM sur Telegram...")
    send_to_telegram(llm_summary, telegram_bot_token, telegram_chat_id)
    time.sleep(2)

    # 3. Génération et envoi du Message 2 : IA Image & Vidéo Générative
    print("[*] Génération de la veille Image & Vidéo Générative...")
    img_summary = generate_category_summary(img_articles, "IA Générative Images & Vidéo", "🎨", gemini_api_key)
    print("[*] Envoi du message Image & Vidéo sur Telegram...")
    send_to_telegram(img_summary, telegram_bot_token, telegram_chat_id)

    print("[*] Veille terminée avec succès !")


if __name__ == "__main__":
    main()
