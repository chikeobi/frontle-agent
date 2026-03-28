from google import genai
import tweepy
import requests
import random
import datetime
import base64
import config

# Setup Gemini
client = genai.Client(api_key=config.GEMINI_API_KEY)

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
    tones = ["bold and confrontational", "funny and relatable", "educational and helpful"]
    tone = random.choice(tones)

    prompt = f"""
You are a viral social media expert for {config.APP_NAME}, an app that helps car buyers.

Write a single tweet that is {tone} about how {product['name']} helps people {product['hook']}.

Rules:
- Maximum 240 characters including the URL
- No hashtags longer than 2 words
- Include 1-2 relevant hashtags
- End with this URL: {product['url']}
- Make it punchy and shareable
- Do NOT use quotes around the tweet
- Output only the tweet text, nothing else

Topic ideas to pick from:
- Dealerships markup prices by thousands
- Finance managers are trained to upsell you
- Your credit score doesn't have to destroy your car deal
- Most people overpay by $3,000-$5,000 at dealerships
- You can lower your car payment without refinancing
- Bad credit doesn't mean bad deal
"""
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    return response.text.strip()


def generate_social_caption(product_key):
    """Longer caption for Facebook/Instagram."""
    product = config.PRODUCTS[product_key]
    tones = ["bold and honest", "helpful and educational", "relatable and conversational"]
    tone = random.choice(tones)

    prompt = f"""
You are a social media expert for {config.APP_NAME}, an app that helps car buyers.

Write a {tone} Facebook/Instagram caption about how {product['name']} helps people {product['hook']}.

Rules:
- 3-5 sentences max
- End with this URL: {product['url']}
- Include 3-5 relevant hashtags at the end
- Do NOT use quotes around the caption
- Output only the caption text, nothing else

Topic ideas:
- Dealerships markup prices by thousands
- Finance managers are trained to upsell you
- Your credit score doesn't have to destroy your car deal
- Most people overpay by $3,000-$5,000 at dealerships
- You can lower your car payment without refinancing
- Bad credit doesn't mean bad deal
"""
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    return response.text.strip()


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

def upload_image_to_imgur(image_path):
    """Upload image to Imgur to get a public URL for Instagram."""
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://api.imgur.com/3/image",
                headers={"Authorization": f"Client-ID {config.IMGUR_CLIENT_ID}"},
                files={"image": f}
            )
        if resp.status_code == 200:
            url = resp.json()["data"]["link"]
            print(f"✅ Image uploaded to Imgur: {url}")
            return url
        else:
            print(f"❌ Imgur upload failed: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Imgur error: {e}")
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

        # Need a public image URL — upload to Imgur first
        if not config.IMGUR_CLIENT_ID or config.IMGUR_CLIENT_ID == "YOUR_IMGUR_CLIENT_ID":
            print("⚠️  Imgur not configured — skipping Instagram")
            return False

        image_url = upload_image_to_imgur(image_path)
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

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    text = response.text.strip()

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
    caption = generate_social_caption(product_key)
    print(f"📝 Tweet: {tweet}")

    # Generate image
    print("\n🎨 Generating image...")
    image_path = generate_image(product_key)

    # Post everywhere
    print("\n📤 Posting...")
    post_tweet(tweet)
    post_to_facebook(caption, image_path)
    post_to_instagram(caption, image_path)

    # Reddit — 1 random subreddit per run
    subreddit = random.choice(list(REDDIT_POSTS.keys()))
    print(f"\n📢 Posting to {subreddit}...")
    post_to_reddit(subreddit)

    print("\n" + "=" * 50)
    print("✅ Agent run complete\n")


if __name__ == "__main__":
    run_agent()
