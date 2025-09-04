#!/usr/bin/env python3
"""
Example usage of the Instagram scraper
"""

import asyncio
import json
from scrapper import scrape_instagram_video, scrape_multiple_videos


async def example_single_video():
    """Example: Scrape a single Instagram video"""
    # Replace with actual Instagram video URL
    video_url = "https://www.instagram.com/reels/DNanqXwsNrD/"
    
    try:
        print(f"Scraping video: {video_url}")
        result = await scrape_instagram_video(video_url, headless=False)
        
        # Print results
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Save to file
        with open('single_video_results.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        print("Results saved to single_video_results.json")
        
    except Exception as e:
        print(f"Error: {e}")


async def example_multiple_videos():
    """Example: Scrape multiple Instagram videos"""
    # Replace with actual Instagram video URLs
    video_urls = [
        "https://www.instagram.com/p/VIDEO1_ID/",
        "https://www.instagram.com/p/VIDEO2_ID/",
        "https://www.instagram.com/p/VIDEO3_ID/"
    ]
    
    try:
        print(f"Scraping {len(video_urls)} videos...")
        results = await scrape_multiple_videos(video_urls, headless=False)
        
        # Print results
        for i, result in enumerate(results):
            print(f"\n--- Video {i+1} ---")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Save to file
        with open('multiple_videos_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        print("\nAll results saved to multiple_videos_results.json")
        
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run examples"""
    print("Instagram Scraper Examples")
    print("=" * 30)
    
    # Example 1: Single video
    print("\n1. Scraping single video...")
    await example_single_video()
    
    # Example 2: Multiple videos
    print("\n2. Scraping multiple videos...")
    await example_multiple_videos()


if __name__ == "__main__":
    asyncio.run(main())
