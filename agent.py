from google import genai
import tweepy
import requests
import random
import datetime
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

def post_tweet(text):
    try:
        response = twitter.create_tweet(text=text)
        print(f"✅ Tweet posted: {text[:60]}...")
        return True
    except Exception as e:
        print(f"❌ Tweet failed: {e}")
        return False

def generate_image_prompt(product_key):
    product = config.PRODUCTS[product_key]
    prompts = [
        f"Bold infographic showing car dealership price breakdown, modern flat design, red and white colors",
        f"Person celebrating saving money on car purchase, thumbs up, bright colors, cartoon style",
        f"Car keys with dollar signs, money saved concept, clean modern design",
        f"Shocked face looking at car dealership invoice, comic style, bold colors",
        f"Happy family driving away in new car, money floating around, vibrant illustration"
    ]
    return random.choice(prompts)

def generate_image(product_key):
    prompt = generate_image_prompt(product_key)
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
            import base64
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

def run_agent():
    print(f"\n🚗 Frontle Agent starting — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # Pick a product to promote
    product_key = pick_product()
    product = config.PRODUCTS[product_key]
    print(f"📦 Product: {product['name']}")

    # Generate and post tweet
    print("✍️  Generating tweet...")
    tweet = generate_tweet(product_key)
    print(f"📝 Tweet: {tweet}")
    post_tweet(tweet)

    # Generate image (uses Stability AI credits)
    print("🎨 Generating image...")
    image = generate_image(product_key)

    print("=" * 50)
    print("✅ Agent run complete\n")

if __name__ == "__main__":
    run_agent()