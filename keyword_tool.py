
import sys
import os
import json
import yaml # New import
from collections import defaultdict
import google.generativeai as genai
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

def get_strategic_themes_from_llm(keywords: list, brand_name: str, gemini_api_key: str) -> list:
    """Uses the Gemini API to analyze a list of keywords and suggest ad group themes."""
    # (This function remains the same as the previous version)
    print("\n🧠 Contacting AI Strategist (Gemini API) to generate ad group themes...")
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    keyword_string = ", ".join(keywords)
    prompt = f"""
    You are an expert Google Ads strategist for a brand named '{brand_name}'.
    Analyze this list of keywords: --- {keyword_string} ---
    Based on user intent, product types, and common search patterns in this list,
    suggest 5 to 7 strategic ad group themes.
    Your response MUST be a valid JSON object with a single key "themes" which is a list of strings.
    Example: {{"themes": ["Theme Name 1", "Theme Name 2"]}}
    """
    try:
        response = model.generate_content(prompt)
        json_response = json.loads(response.text.strip('```json\n').strip('```'))
        themes = json_response.get("themes", [])
        print(f"✅ AI Strategist recommended themes: {themes}")
        return themes
    except Exception as e:
        print(f"❌ Error contacting Gemini API: {e}. Using fallback themes.")
        return ["General", "Competitors", "Local Searches", "Equipment", "Questions"]

def get_ad_group_for_keyword(keyword: str, brand_name: str, competitor_names: list, locations: list, llm_themes: list) -> str:
    """Assigns a keyword to a strategic ad group using dynamic brand and location names."""
    kw_lower = keyword.lower()
    
    if brand_name.lower() in kw_lower:
        return "Brand Terms"

    if any(competitor.lower() in kw_lower for competitor in competitor_names):
        return "Competitor Terms"

    if any(loc.lower() in kw_lower for loc in locations) or any(trig in kw_lower for trig in ["near me", "nearby"]):
        return next((theme for theme in llm_themes if "local" in theme.lower() or "near" in theme.lower()), "Location-Based Terms")
        
    if any(trig in kw_lower for trig in ["best", "what is", "how to"]):
        return next((theme for theme in llm_themes if "informational" in theme.lower() or "question" in theme.lower()), "Informational & Long-Tail")

    for theme in llm_themes:
        triggers = [word for word in theme.lower().split() if len(word) > 2]
        if any(trigger in kw_lower for trigger in triggers):
            return theme
            
    return "General Product & Category Terms"

def get_keyword_ideas(client, customer_id, seed_keywords, page_url):
    """Fetches keyword ideas from the Google Ads API."""
    print("\n📈 Contacting Google Ads API to fetch keywords...")
    try:
        # (API call logic is the same)
        keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
        googleads_service = client.get_service("GoogleAdsService")
        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = customer_id
        request.language = googleads_service.language_constant_path("1000") # English
        request.geo_target_constants = ["geoTargetConstants/2356"] # India
        if seed_keywords: request.keyword_seed.keywords.extend(seed_keywords)
        if page_url: request.url_seed.url = page_url
        response = keyword_plan_idea_service.generate_keyword_ideas(request=request)
        print("✅ Keywords fetched successfully.")
        return response.results
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex.error.code().name}")
        sys.exit(1)

def print_structured_plan(ad_groups: dict, currency_symbol: str):
    """Prints the final, structured keyword plan."""
    # (This function is updated to use the currency symbol from the config)
    group_order = sorted(ad_groups.keys())
    print("\n\n--- AI-POWERED SEARCH CAMPAIGN PLAN ---")
    for group_name in group_order:
        keywords_data = ad_groups[group_name]
        print(f"\n📂 Ad Group: {group_name}")
        print("-" * (len(group_name) + 12))
        print(f"{'Keyword':<50} {'Avg Monthly Searches':<25} {'Competition':<15} {'Est. CPC Range':<20}")
        print("=" * 110)
        sorted_keywords = sorted(keywords_data, key=lambda x: x['avg_monthly_searches'], reverse=True)
        for kw_data in sorted_keywords:
            cpc_range = f"{currency_symbol}{kw_data['low_cpc']:.2f} - {currency_symbol}{kw_data['high_cpc']:.2f}"
            print(f"{kw_data['keyword']:<50} {kw_data['avg_monthly_searches']:<25} {kw_data['competition']:<15} {cpc_range:<20}")

if __name__ == "__main__":
    # Load all inputs from the config.yaml file
    config_file_path = "config.yaml"
    try:
        with open(config_file_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Configuration file not found at '{config_file_path}'. Please make sure it's in the same folder as the script.")
        sys.exit(1)

    # Assign variables from config file
    brand_name = config['brand_info']['name']
    competitor_website = config['brand_info']['competitor_website']
    competitor_names = config['brand_info']['competitor_names']
    service_locations = config['brand_info']['service_locations']
    seed_keywords = config['discovery_inputs']['seed_keywords']
    customer_id = str(config['settings']['google_ads_customer_id'])
    gemini_api_key = os.getenv("GEMINI_API_KEY", config['settings']['gemini_api_key'])
    min_volume = config['settings']['min_search_volume']
    currency = config['settings']['currency_symbol']

    # Load Google Ads Client
    try:
        gads_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "google-ads.yaml")
        googleads_client = GoogleAdsClient.load_from_storage(gads_config_path)
    except FileNotFoundError:
        print("❌ 'google-ads.yaml' not found. Please ensure it's in the script's folder.")
        sys.exit(1)

    # --- Main Workflow ---
    raw_ideas = get_keyword_ideas(googleads_client, customer_id, seed_keywords, competitor_website)
    
    filtered_ideas = [idea for idea in raw_ideas if (idea.keyword_idea_metrics.avg_monthly_searches or 0) >= min_volume]
    print(f"\n🔎 Filtered down to {len(filtered_ideas)} keywords with at least {min_volume} monthly searches.")

    filtered_keyword_texts = [idea.text for idea in filtered_ideas]
    llm_themes = get_strategic_themes_from_llm(filtered_keyword_texts, brand_name, gemini_api_key)

    ad_groups = defaultdict(list)
    for idea in filtered_ideas:
        metrics = idea.keyword_idea_metrics
        ad_group_name = get_ad_group_for_keyword(idea.text, brand_name, competitor_names, service_locations, llm_themes)
        ad_groups[ad_group_name].append({
            "keyword": idea.text,
            "avg_monthly_searches": metrics.avg_monthly_searches or 0,
            "competition": metrics.competition.name,
            "low_cpc": metrics.low_top_of_page_bid_micros / 1000000 if metrics.low_top_of_page_bid_micros else 0.0,
            "high_cpc": metrics.high_top_of_page_bid_micros / 1000000 if metrics.high_top_of_page_bid_micros else 0.0
        })

    print_structured_plan(ad_groups, currency)