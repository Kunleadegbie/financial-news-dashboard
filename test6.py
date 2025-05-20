import streamlit as st
import feedparser
from textblob import TextBlob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sec_edgar_downloader import Downloader
import os
from openai import OpenAI

# API key loading
openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("openai_key")
if not openai_api_key:
    st.error("⚠️ OpenAI API key not found. Please set the 'OPENAI_API_KEY' environment variable or add 'openai_key' to Streamlit Secrets.")
    st.stop()

from openai import OpenAI
client = OpenAI(api_key=openai_api_key)


# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

# Summarizer function
def summarize_text(text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial news summarizer."},
                {"role": "user", "content": f"Summarize this financial news headline in 20 words:\n{text}"}
            ],
            max_tokens=50,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Summarization error: {str(e)}"

# Function to fetch and analyze news feed
def get_news_sentiment(feed_url):
    feed = feedparser.parse(feed_url)
    articles = []
    for entry in feed.entries[:20]:
        title = entry.title
        published = entry.published if 'published' in entry else 'N/A'
        sentiment = TextBlob(title).sentiment.polarity
        summary = summarize_text(title)
        articles.append({
            'Title': title,
            'Published': published,
            'Sentiment Score': sentiment,
            'Summary': summary
        })
    return pd.DataFrame(articles)

# App config
st.set_page_config(page_title="FinPulse | Financial News & Sentiment")
st.title("📈 FinPulse: Financial News & Sentiment Dashboard")

# Sidebar config
st.sidebar.header("🛠️ Settings")

# Predefined list of financial RSS feeds
rss_feeds = {
    "Yahoo Finance (AAPL, TSLA, MSFT, NVDA, AMZN)": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,TSLA,MSFT,NVDA,AMZN&region=US&lang=en-US",
    "Reuters Business News": "http://feeds.reuters.com/reuters/businessNews",
    "MarketWatch Top Stories": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "Investing.com Latest News": "https://www.investing.com/rss/news.rss",
    "Bloomberg Global Markets": "https://www.bloomberg.com/feed/podcast/etf-report.xml",
    "CNBC Top News": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
}

# Dropdown to select RSS feed
selected_feed = st.sidebar.selectbox("📡 Select News Feed", list(rss_feeds.keys()))

# Get corresponding URL from selection
feed_url = rss_feeds[selected_feed]

# Watchlist input
watchlist_input = st.sidebar.text_input("🔍 Watchlist Tickers (comma-separated)", "AAPL,TSLA,MSFT,NVDA,AMZN")
watchlist = [x.strip().upper() for x in watchlist_input.split(',')]

# Fetch news button
if st.sidebar.button("🔄 Refresh News"):
    news_df = get_news_sentiment(feed_url)
    st.session_state['news_df'] = news_df

# Load data if not yet loaded
if 'news_df' not in st.session_state:
    st.session_state['news_df'] = get_news_sentiment(feed_url)

news_df = st.session_state['news_df']

# Market Mood Gauge
st.subheader("📊 Market Mood")
fig, ax = plt.subplots(figsize=(4, 2))
average_sentiment = news_df['Sentiment Score'].mean()
ax.barh(['Sentiment'], [average_sentiment],
        color='green' if average_sentiment >= 0 else 'red')
ax.set_xlim(-1, 1)
ax.set_xlabel("Sentiment Score")
st.pyplot(fig)

# Top Bullish/Bearish News
st.subheader("🔥 Top Bullish & Bearish Headlines")
col1, col2 = st.columns(2)

with col1:
    st.write("**Top 5 Bullish**")
    st.dataframe(news_df.sort_values(by='Sentiment Score', ascending=False).head(5))

with col2:
    st.write("**Top 5 Bearish**")
    st.dataframe(news_df.sort_values(by='Sentiment Score', ascending=True).head(5))

# Watchlist News
st.subheader("📌 Watchlist News")
watchlist_news = news_df[news_df['Title'].str.contains('|'.join(watchlist), case=False)]
st.dataframe(watchlist_news)

# Sector Mapping
sector_map = {
    'AAPL': 'Technology',
    'TSLA': 'Automotive',
    'MSFT': 'Technology',
    'NVDA': 'Semiconductors',
    'AMZN': 'E-Commerce'
}

def get_sector(title):
    for ticker, sector in sector_map.items():
        if ticker in title:
            return sector
    return 'Other'

news_df['Sector'] = news_df['Title'].apply(get_sector)

# Sector Sentiment Heatmap
st.subheader("📊 Sector Sentiment Heatmap")
sector_sentiment = news_df.groupby('Sector')['Sentiment Score'].mean().reset_index()

fig, ax = plt.subplots(figsize=(6, 2))
heatmap_data = sector_sentiment.pivot_table(values='Sentiment Score', index='Sector')
sns.heatmap(heatmap_data, annot=True, cmap='coolwarm', center=0, ax=ax)
st.pyplot(fig)

# SEC Filings Downloader
st.sidebar.subheader("📥 Download SEC Filings")
ticker_input = st.sidebar.text_input("SEC Filing Ticker", "AAPL")

if st.sidebar.button("📥 Download Filings"):
    os.makedirs("sec_filings", exist_ok=True)
    dl = Downloader("kadegbie@gmail.com", "sec_filings")
    dl.get("10-K", ticker_input, limit=5)
    st.sidebar.success(f"Downloaded latest 10-K filings for {ticker_input}.")

# Full News Feed Table
st.subheader("📰 Full News Feed")
st.dataframe(news_df)
