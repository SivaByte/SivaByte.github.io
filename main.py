import feedparser
import openai
import os
import datetime
from github import Github

# --- CONFIGURATION ---
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = os.getenv('GITHUB_REPOSITORY')

# SOURCES: Tech & AI News
RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.producthunt.com/feed",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.theverge.com/rss/index.xml"
]

# THE PROMPT
SYSTEM_PROMPT = """
You are a cynical, expert tech editor. 
Summarize this news into a blog post entry.
Output ONLY the HTML for the article inside a <article> tag.
Format:
<article>
  <h3>[Catchy Title Here]</h3>
  <p class="meta">[Date] • [Source Name]</p>
  <p>[Summary paragraph 1]</p>
  <div class="verdict"><strong>Verdict:</strong> [One sentence opinion]</div>
  <a href="[Original Link]" class="btn">Read Source &rarr;</a>
</article>
"""

# THE WEBSITE TEMPLATE
HTML_HEADER = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The AI Daily</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <style>
        body { max-width: 800px; margin: 0 auto; padding: 20px; }
        article { margin-bottom: 40px; padding: 20px; border-bottom: 1px solid #333; }
        .meta { color: #888; font-size: 0.9em; }
        .verdict { background: #1a1a1a; padding: 10px; border-left: 4px solid #00aaaa; margin: 15px 0; }
        .btn { text-decoration: none; color: #00aaaa; font-weight: bold; }
    </style>
</head>
<body>
    <nav><ul><li><strong>THE AI DAILY</strong></li></ul></nav>
    <main>
    <h1>Latest Intelligence</h1>
    """

def fetch_and_post():
    # 1. Get News
    print("Fetching news...")
    news_items = []
    for feed in RSS_FEEDS:
        try:
            d = feedparser.parse(feed)
            for entry in d.entries[:2]: # Grab top 2 from each source
                news_items.append(entry)
        except: pass

    if not news_items: return

    # 2. Generate HTML
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    new_html = ""
    print(f"Processing {len(news_items)} articles...")
    
    # Process just the top 3 to start (save API costs)
    for article in news_items[:3]:
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Title: {article.title}\nLink: {article.link}\nSummary: {getattr(article, 'summary', '')}"}
                ]
            )
            new_html += response.choices[0].message.content + "\n"
        except: pass

    # 3. Update Website
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    try:
        contents = repo.get_contents("index.html")
        old_html = contents.decoded_content.decode("utf-8")
        sha = contents.sha
        if "" in old_html:
            parts = old_html.split("")
            final_html = parts[0] + "\n" + new_html + parts[1]
        else:
            final_html = HTML_HEADER.replace("", "\n" + new_html) + "</main></body></html>"
    except:
        final_html = HTML_HEADER.replace("", "\n" + new_html) + "</main></body></html>"
        sha = None

    if sha:
        repo.update_file("index.html", "Update news", final_html, sha)
    else:
        repo.create_file("index.html", "Init site", final_html)

if __name__ == "__main__":
    fetch_and_post()
