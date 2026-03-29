from groq import Groq
import tweepy
import requests
import random
import datetime
import base64
import time
import os
import config

# Setup Groq
client = Groq(api_key=config.GROQ_API_KEY)

# Load brand voice
def load_brand_voice():
    try:
        with open("brand_voice.md", "r") as f:
            return f.read()
    except:
        return ""

BRAND_VOICE = load_brand_voice()

# Setup Twitter
twitter = tweepy.Client(
    consumer_key=config.TWITTER_API_KEY,
    consumer_secret=config.TWITTER_API_SECRET,
    access_token=config.TWITTER_ACCESS_TOKEN,
    access_token_secret=config.TWITTER_ACCESS_SECRET
)

# Setup Reddit (optional)
reddit = None
try:
    import praw
    if config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_ID != "YOUR_REDDIT_CLIENT_ID":
        reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            username=config.REDDIT_USERNAME,
            password=config.REDDIT_PASSWORD,
            user_agent=f"FrontleAgent/1.0 by u/{config.REDDIT_USERNAME}"
        )
        print("✅ Reddit connected")
    else:
        print("⚠️  Reddit credentials not set — skipping Reddit")
except Exception as e:
    print(f"⚠️  Reddit setup failed: {e}")


def pick_product():
    products = list(config.PRODUCTS.keys())
    return random.choice(products)


def generate_tweet(product_key):
    product = config.PRODUCTS[product_key]

    prompt = f"""
You are writing a tweet for {config.APP_NAME}, an app that helps car buyers.

BRAND VOICE GUIDE:
{BRAND_VOICE}

Write a single tweet about how {product['name']} helps people {product['hook']}.

Rules:
- Maximum 240 characters including the URL
- Include 1-2 relevant hashtags
- End with this URL: {product['url']}
- Follow the brand voice guide above exactly
- Do NOT use quotes around the tweet
- Output only the tweet text, nothing else
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def generate_facebook_caption(product_key):
    product = config.PRODUCTS[product_key]
    prompt = f"""
You are writing a Facebook post for {config.APP_NAME}, an app that helps car buyers.

BRAND VOICE GUIDE:
{BRAND_VOICE}

Write a Facebook post about how {product['name']} helps people {product['hook']}.

Rules:
- 3-5 sentences, storytelling style, like you're talking to a friend
- End with this URL: {product['url']}
- Include 2-3 relevant hashtags at the end
- Follow the brand voice guide above exactly
- Do NOT use quotes around the post
- Output only the post text, nothing else
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def generate_instagram_caption(product_key):
    product = config.PRODUCTS[product_key]
    prompt = f"""
You are writing an Instagram caption for {config.APP_NAME}, an app that helps car buyers.

BRAND VOICE GUIDE:
{BRAND_VOICE}

Write an Instagram caption about how {product['name']} helps people {product['hook']}.

Rules:
- Hook in the first line to stop the scroll
- 2-3 short punchy sentences
- End with this URL: {product['url']}
- Include 5-8 relevant hashtags at the end
- Follow the brand voice guide above exactly
- Do NOT use quotes around the caption
- Output only the caption text, nothing else
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def generate_youtube_title_and_description(product_key):
    product = config.PRODUCTS[product_key]
    prompt = f"""
You are writing a YouTube Shorts title and description for {config.APP_NAME}, an app that helps car buyers.

BRAND VOICE GUIDE:
{BRAND_VOICE}

Write a YouTube title and description about how {product['name']} helps people {product['hook']}.

Rules:
- Title: under 60 characters, curiosity-driven, SEO-friendly
- Description: 2-3 sentences, end with {product['url']}
- Follow the brand voice guide above exactly
- Output in this exact format:
TITLE: [title here]
DESCRIPTION: [description here]
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.choices[0].message.content.strip()
    title, description = "", ""
    for line in text.split("\n"):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("DESCRIPTION:"):
            description = line.replace("DESCRIPTION:", "").strip()
    return title, description


def post_tweet(text):
    try:
        twitter.create_tweet(text=text)
        print(f"✅ Twitter: {text[:60]}...")
        return True
    except Exception as e:
        print(f"❌ Twitter failed: {e}")
        return False


# ── Facebook ──────────────────────────────────────────────────────────────────

def post_to_facebook(caption, image_path=None):
    if not config.FACEBOOK_PAGE_ID or config.FACEBOOK_PAGE_ID == "YOUR_FACEBOOK_PAGE_ID":
        print("⚠️  Facebook credentials not set — skipping")
        return False
    try:
        token = config.FACEBOOK_PAGE_ACCESS_TOKEN
        page_id = config.FACEBOOK_PAGE_ID

        if image_path:
            with open(image_path, "rb") as f:
                resp = requests.post(
                    f"https://graph.facebook.com/v19.0/{page_id}/photos",
                    data={"caption": caption, "access_token": token},
                    files={"source": f}
                )
        else:
            resp = requests.post(
                f"https://graph.facebook.com/v19.0/{page_id}/feed",
                data={"message": caption, "access_token": token}
            )

        if resp.status_code == 200:
            print(f"✅ Facebook posted: {caption[:60]}...")
            return True
        else:
            print(f"❌ Facebook failed: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Facebook error: {e}")
        return False


# ── Instagram ─────────────────────────────────────────────────────────────────

def upload_image_to_cloudinary(image_path):
    """Upload image to Cloudinary to get a public URL for Instagram."""
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=config.CLOUDINARY_CLOUD_NAME,
            api_key=config.CLOUDINARY_API_KEY,
            api_secret=config.CLOUDINARY_API_SECRET
        )
        result = cloudinary.uploader.upload(image_path)
        url = result["secure_url"]
        print(f"✅ Image uploaded to Cloudinary: {url}")
        return url
    except Exception as e:
        print(f"❌ Cloudinary error: {e}")
        return None


def post_to_instagram(caption, image_path=None):
    if not config.INSTAGRAM_ACCOUNT_ID or config.INSTAGRAM_ACCOUNT_ID == "YOUR_INSTAGRAM_ACCOUNT_ID":
        print("⚠️  Instagram credentials not set — skipping")
        return False
    if not image_path:
        print("⚠️  Instagram requires an image — skipping")
        return False
    try:
        token = config.FACEBOOK_PAGE_ACCESS_TOKEN
        ig_id = config.INSTAGRAM_ACCOUNT_ID

        # Need a public image URL — upload to Cloudinary first
        image_url = upload_image_to_cloudinary(image_path)
        if not image_url:
            return False

        # Step 1: Create media container
        container_resp = requests.post(
            f"https://graph.facebook.com/v19.0/{ig_id}/media",
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": token
            }
        )
        if container_resp.status_code != 200:
            print(f"❌ Instagram container failed: {container_resp.text}")
            return False

        container_id = container_resp.json()["id"]

        # Step 2: Publish
        publish_resp = requests.post(
            f"https://graph.facebook.com/v19.0/{ig_id}/media_publish",
            data={"creation_id": container_id, "access_token": token}
        )
        if publish_resp.status_code == 200:
            print(f"✅ Instagram posted: {caption[:60]}...")
            return True
        else:
            print(f"❌ Instagram publish failed: {publish_resp.text}")
            return False
    except Exception as e:
        print(f"❌ Instagram error: {e}")
        return False


# ── Reddit ────────────────────────────────────────────────────────────────────

REDDIT_POSTS = {
    "r/askcarsales": {
        "product_key": "dealership",
        "prompt": """Write a helpful Reddit post for r/askcarsales from the perspective of a car buyer who learned how to avoid overpaying at dealerships.

The post should:
- Be genuinely helpful advice about negotiating or understanding dealer markups
- Sound like a real person sharing what they learned, not an ad
- Be 3-5 short paragraphs
- Naturally mention that tools like {url} exist to help buyers, only once, at the end
- NOT be salesy or promotional
- Title should be a question or insight other buyers would find useful

Format:
TITLE: [title here]
BODY:
[body here]"""
    },
    "r/personalfinance": {
        "product_key": "subprime",
        "prompt": """Write a helpful Reddit post for r/personalfinance about how people with bad or subprime credit can still get a reasonable car deal.

The post should:
- Give real, actionable advice about car buying with bad credit
- Sound like someone who figured this out the hard way, not an ad
- Be 3-5 short paragraphs
- Mention {url} naturally once at the end as a resource
- NOT be salesy
- Title should be something r/personalfinance readers would click on

Format:
TITLE: [title here]
BODY:
[body here]"""
    },
    "r/povertyfinance": {
        "product_key": "switch",
        "prompt": """Write a helpful Reddit post for r/povertyfinance about how people can lower their monthly car payment without refinancing by switching to a cheaper vehicle.

The post should:
- Give practical, empathetic advice for people struggling with high car payments
- Sound like someone helping a friend, not an ad
- Be 3-5 short paragraphs
- Mention {url} naturally once at the end as a free resource
- NOT be salesy or preachy
- Title should resonate with someone stressed about bills

Format:
TITLE: [title here]
BODY:
[body here]"""
    },
    "r/cars": {
        "product_key": "dealership",
        "prompt": """Write a helpful Reddit post for r/cars about what most people don't know about dealership pricing and how to avoid common traps.

The post should:
- Be educational and informative about how car pricing actually works
- Sound like an enthusiast or informed buyer, not an ad
- Be 3-5 short paragraphs
- Mention {url} naturally once at the end
- NOT be promotional or salesy
- Title should be something r/cars readers would find interesting

Format:
TITLE: [title here]
BODY:
[body here]"""
    }
}


def generate_reddit_post(subreddit_name):
    config_data = REDDIT_POSTS[subreddit_name]
    product_key = config_data["product_key"]
    product = config.PRODUCTS[product_key]
    prompt = config_data["prompt"].format(url=product["url"])

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.choices[0].message.content.strip()

    lines = text.split('\n')
    title = ""
    body_lines = []
    in_body = False
    for line in lines:
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)

    body = '\n'.join(body_lines).strip()
    return title, body


def post_to_reddit(subreddit_name):
    if not reddit:
        print(f"⚠️  Skipping Reddit ({subreddit_name}) — not configured")
        return False
    try:
        title, body = generate_reddit_post(subreddit_name)
        subreddit = reddit.subreddit(subreddit_name.replace("r/", ""))
        subreddit.submit(title, selftext=body)
        print(f"✅ Reddit posted to {subreddit_name}: {title[:60]}...")
        return True
    except Exception as e:
        print(f"❌ Reddit ({subreddit_name}) failed: {e}")
        return False


# ── Image generation ──────────────────────────────────────────────────────────

def generate_image(product_key):
    prompts = [
        "Bold infographic showing car dealership price breakdown, modern flat design, red and white colors",
        "Person celebrating saving money on car purchase, thumbs up, bright colors, cartoon style",
        "Car keys with dollar signs, money saved concept, clean modern design",
        "Shocked face looking at car dealership invoice, comic style, bold colors",
        "Happy family driving away in new car, money floating around, vibrant illustration"
    ]
    prompt = random.choice(prompts)
    try:
        response = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            headers={
                "Authorization": f"Bearer {config.STABILITY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "text_prompts": [{"text": prompt, "weight": 1}],
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 30
            }
        )
        if response.status_code == 200:
            image_data = response.json()["artifacts"][0]["base64"]
            filename = f"image_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            with open(filename, "wb") as f:
                f.write(base64.b64decode(image_data))
            print(f"✅ Image saved: {filename}")
            return filename
        else:
            print(f"❌ Image generation failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Image error: {e}")
        return None


# ── YouTube ───────────────────────────────────────────────────────────────

def post_to_youtube(caption, image_path=None, title=None):
    if not image_path:
        print("⚠️  YouTube requires an image — skipping")
        return False
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from moviepy import ImageClip
        import os

        # Build a short video from the image
        clip = ImageClip(image_path, duration=15)
        clip = clip.with_fps(1)
        video_path = image_path.replace(".png", ".mp4")
        clip.write_videofile(video_path, codec="libx264", audio=False, logger=None)

        creds = Credentials(
            token=None,
            refresh_token=config.YOUTUBE_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config.YOUTUBE_CLIENT_ID,
            client_secret=config.YOUTUBE_CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )

        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": (title or caption)[:100],
                    "description": caption,
                    "tags": ["car buying", "save money", "dealership", "frontle"],
                    "categoryId": "22"
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            },
            media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
        )
        response = request.execute()
        print(f"✅ YouTube posted: {response.get('id')}")
        os.remove(video_path)
        return True
    except Exception as e:
        print(f"❌ YouTube failed: {e}")
        return False


# ── Telegram Approval ─────────────────────────────────────────────────────

def telegram_send(text):
    requests.post(
        f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
        data={"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    )

def telegram_approve(content_type, text, timeout_minutes=15):
    """Send content for approval. Returns True if approved, False if rejected/timeout."""
    msg = f"📋 <b>APPROVAL NEEDED — {content_type}</b>\n\n{text}\n\n✅ Reply <b>YES</b> to post\n❌ Reply <b>NO</b> to skip\n\n⏱ You have {timeout_minutes} minutes"
    telegram_send(msg)

    deadline = time.time() + (timeout_minutes * 60)
    last_update_id = None

    while time.time() < deadline:
        resp = requests.get(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates",
            params={"timeout": 30, "offset": last_update_id}
        ).json()

        for update in resp.get("result", []):
            last_update_id = update["update_id"] + 1
            msg_text = update.get("message", {}).get("text", "").strip().upper()
            if msg_text == "YES":
                telegram_send(f"✅ Approved! Posting {content_type}...")
                return True
            elif msg_text == "NO":
                telegram_send(f"❌ Skipped {content_type}.")
                return False

        time.sleep(10)

    telegram_send(f"⏱ Timeout — skipping {content_type}.")
    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def run_agent():
    print(f"\n🚗 Frontle Agent starting — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    product_key = pick_product()
    product = config.PRODUCTS[product_key]
    print(f"📦 Product: {product['name']}")

    # Generate content
    print("\n✍️  Generating content...")
    tweet = generate_tweet(product_key)
    fb_caption = generate_facebook_caption(product_key)
    ig_caption = generate_instagram_caption(product_key)
    yt_title, yt_description = generate_youtube_title_and_description(product_key)
    print(f"📝 Tweet: {tweet}")

    # Generate image
    print("\n🎨 Generating image...")
    image_path = generate_image(product_key)

    # Send for approval and post
    print("\n📤 Sending for Telegram approval...")

    if telegram_approve("Facebook", fb_caption):
        post_to_facebook(fb_caption, image_path)

    if telegram_approve("Instagram", ig_caption):
        post_to_instagram(ig_caption, image_path)

    if telegram_approve("YouTube", f"Title: {yt_title}\n\n{yt_description}"):
        post_to_youtube(yt_description, image_path, title=yt_title)

    # Reddit — 1 random subreddit per run
    subreddit = random.choice(list(REDDIT_POSTS.keys()))
    reddit_title, reddit_body = generate_reddit_post(subreddit) if reddit else ("", "")
    if reddit and telegram_approve(f"Reddit ({subreddit})", f"{reddit_title}\n\n{reddit_body[:300]}..."):
        post_to_reddit(subreddit)

    print("\n" + "=" * 50)
    print("✅ Agent run complete\n")


if __name__ == "__main__":
    run_agent()
