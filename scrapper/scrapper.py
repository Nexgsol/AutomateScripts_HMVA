import asyncio
import json
import re
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import logging

from playwright.async_api import (
    async_playwright, Browser, Page, BrowserContext
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstagramScraper:
    """
    Instagram scraper for extracting trending words from videos using
    Playwright
    """
    
    def __init__(self, headless: bool = True, slow_mo: int = 100):
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Common trending words patterns
        self.trending_patterns = [
            r'#\w+',  # Hashtags
            r'@\w+',  # Mentions
            r'\b(viral|trending|popular|hot|famous|buzz)\b',  # Trending
            r'\b(breaking|news|update|latest)\b',  # News keywords
            r'\b(amazing|incredible|unbelievable|wow)\b',  # Reaction
        ]
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def start(self):
        """Start the browser and create context"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo
            )
            
            # Create context with mobile user agent for better compatibility
            mobile_ua = (
                'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) '
                'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 '
                'Mobile/15E148 Safari/604.1'
            )
            self.context = await self.browser.new_context(
                user_agent=mobile_ua,
                viewport={'width': 375, 'height': 812},
                locale='en-US',
                timezone_id='America/New_York'
            )
            
            self.page = await self.context.new_page()
            logger.info("Browser started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    async def close(self):
        """Close browser and cleanup"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    async def extract_trending_words_from_video(self, video_url: str) -> Dict[str, Any]:
        """
        Extract trending words from an Instagram video
        
        Args:
            video_url: Instagram video URL
            
        Returns:
            Dictionary containing extracted trending words and metadata
        """
        try:
            logger.info(f"Processing video: {video_url}")
            
            # Navigate to the video
            await self.page.goto(video_url, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Try dismissing cookie/login overlays if visible (best-effort)
            await self._best_effort_dismiss_modals()
            
            # Extract via DOM selectors (may fail due to login wall)
            video_data = await self._extract_video_metadata()
            caption_text = await self._extract_caption()
            
            # Fallback: parse JSON-LD and meta tags for description/caption
            if not caption_text:
                caption_text = await self._extract_via_jsonld_and_meta()
            
            # Comments are usually blocked without login; keep best-effort empty
            comments: List[str] = []
            
            # Extract trending words from all text sources
            all_text = caption_text
            trending_words = self._extract_trending_words(all_text)
            
            # Create result structure
            result = {
                "video_url": video_url,
                "video_id": self._extract_video_id(video_url),
                "timestamp": time.time(),
                "trending_words": trending_words,
                "metadata": video_data,
                "caption": caption_text,
                "comments_count": len(comments),
                "sample_comments": comments[:5],
                "extraction_status": "success"
            }
            
            logger.info(
                f"Successfully extracted {len(trending_words)} trending words"
            )
            return result
            
        except Exception as e:
            logger.error(f"Error extracting trending words: {e}")
            return {
                "video_url": video_url,
                "timestamp": time.time(),
                "trending_words": [],
                "extraction_status": "error",
                "error_message": str(e)
            }
    
    async def _extract_video_metadata(self) -> Dict[str, Any]:
        """Extract video metadata like likes, views, etc."""
        try:
            metadata: Dict[str, Any] = {}
            
            # Views (best-effort; likely not visible when logged out)
            try:
                views_element = await self.page.locator(
                    "xpath=//span[contains(., 'views') or contains(., 'view')]"
                ).first
                if await views_element.count():
                    text = await views_element.text_content()
                    if text:
                        metadata['views'] = self._parse_count(text)
            except Exception:
                metadata['views'] = None
            
            # Timestamp
            try:
                time_element = await self.page.locator("time").first
                if await time_element.count():
                    metadata['timestamp'] = await time_element.get_attribute(
                        'datetime'
                    )
            except Exception:
                metadata['timestamp'] = None
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")
            return {}
    
    async def _extract_caption(self) -> str:
        """Extract video caption text via visible DOM (best-effort)"""
        try:
            caption_selectors = [
                'div[data-testid="post-caption"] span',
                'div[class*="caption"] span',
                'article span',
                'div[role="button"] span'
            ]
            
            for selector in caption_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        caption_text = await el.text_content()
                        if caption_text and len(caption_text.strip()) > 5:
                            return caption_text.strip()
                except Exception:
                    continue
            
            return ""
            
        except Exception as e:
            logger.warning(f"Could not extract caption: {e}")
            return ""
    
    async def _extract_via_jsonld_and_meta(self) -> str:
        """Fallback: extract caption/description from JSON-LD and meta tags."""
        try:
            # Prefer JSON-LD VideoObject description when present
            scripts = await self.page.locator(
                'script[type="application/ld+json"]'
            ).all()
            for script in scripts:
                try:
                    content = await script.text_content()
                    if not content:
                        continue
                    data = json.loads(content)
                    # Some pages embed a list of JSON-LD blocks
                    blocks = data if isinstance(data, list) else [data]
                    for block in blocks:
                        if (
                            isinstance(block, dict)
                            and block.get('@type') in ['VideoObject', 'ImageObject']
                        ):
                            description = block.get('description')
                            if description and description.strip():
                                return description.strip()
                except Exception:
                    continue
            
            # Fallback to meta description / og:description
            for meta_name in [
                'meta[name="description"]',
                'meta[property="og:description"]'
            ]:
                try:
                    el = await self.page.query_selector(meta_name)
                    if el:
                        content = await el.get_attribute('content')
                        if content and content.strip():
                            return content.strip()
                except Exception:
                    continue
            
            return ""
        except Exception:
            return ""
    
    async def _best_effort_dismiss_modals(self) -> None:
        """Try to dismiss cookie/login modals without failing the run."""
        try:
            candidates = [
                "button:has-text('Only allow essential cookies')",
                "button:has-text('Allow all cookies')",
                "text=Only allow essential cookies",
                "text=Allow all cookies",
                "button:has-text('Not Now')",
                "button:has-text('Not now')",
            ]
            for sel in candidates:
                try:
                    btn = self.page.locator(sel).first
                    if await btn.count():
                        await btn.click(timeout=1000)
                        await asyncio.sleep(0.3)
                except Exception:
                    continue
        except Exception:
            return
    
    async def _extract_comments(self) -> List[str]:
        """Extract comments from the video (likely empty when logged out)."""
        try:
            comments: List[str] = []
            return comments
        except Exception:
            return []
    
    def _extract_trending_words(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract trending words from text using regex patterns
        
        Args:
            text: Text to analyze
            
        Returns:
            List of dictionaries containing trending words and their context
        """
        trending_words: List[Dict[str, Any]] = []
        
        if not text:
            return trending_words
        
        # Extract hashtags
        hashtags = re.findall(r'#\w+', text)
        for hashtag in hashtags:
            trending_words.append({
                "word": hashtag,
                "type": "hashtag",
                "context": self._get_context(text, hashtag),
                "frequency": text.count(hashtag)
            })
        
        # Extract mentions
        mentions = re.findall(r'@\w+', text)
        for mention in mentions:
            trending_words.append({
                "word": mention,
                "type": "mention",
                "context": self._get_context(text, mention),
                "frequency": text.count(mention)
            })
        
        # Extract trending keywords
        text_lower = text.lower()
        for pattern in self.trending_patterns[2:]:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                trending_words.append({
                    "word": match,
                    "type": "trending_keyword",
                    "context": self._get_context(text, match),
                    "frequency": text_lower.count(match)
                })
        
        # Fallback: extract keywords by frequency if nothing found above
        if not trending_words:
            # Basic stopwords list
            stopwords = set([
                'the','a','an','and','or','but','if','in','on','at','to','for','of',
                'is','are','was','were','be','been','with','by','as','it','this',
                'that','these','those','i','you','he','she','we','they','them',
                'me','my','your','our','their','from','up','down','over','under',
                'not','no','so','too','very','just','than','then','there','here'
            ])
            words = re.findall(r"[A-Za-z\u00C0-\u017F']{3,}", text_lower)
            freq: Dict[str, int] = {}
            for w in words:
                if w in stopwords:
                    continue
                freq[w] = freq.get(w, 0) + 1
            # Take top 10
            top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
            for w, f in top:
                trending_words.append({
                    "word": w,
                    "type": "keyword",
                    "context": self._get_context(text, w),
                    "frequency": f
                })
        
        # De-duplicate by max frequency
        unique_words: Dict[str, Dict[str, Any]] = {}
        for word_data in trending_words:
            key = word_data["word"].lower()
            cur = unique_words.get(key)
            if cur is None or word_data["frequency"] > cur["frequency"]:
                unique_words[key] = word_data
        
        # Sort by frequency (descending)
        sorted_words = sorted(
            unique_words.values(), key=lambda x: x["frequency"], reverse=True
        )
        
        return sorted_words
    
    def _get_context(self, text: str, word: str, context_length: int = 50) -> str:
        """Get context around a word in the text"""
        try:
            index = text.lower().find(word.lower())
            if index == -1:
                return ""
            
            start = max(0, index - context_length)
            end = min(len(text), index + len(word) + context_length)
            
            context = text[start:end]
            if start > 0:
                context = "..." + context
            if end < len(text):
                context = context + "..."
            
            return context.strip()
            
        except Exception:
            return ""
    
    def _parse_count(self, count_text: str) -> Optional[int]:
        """Parse count text (e.g., '1.2K', '500') to integer"""
        if not count_text:
            return None
        
        try:
            count_text = count_text.strip().lower()
            
            # Handle K (thousands)
            if 'k' in count_text:
                number = float(count_text.replace('k', ''))
                return int(number * 1000)
            
            # Handle M (millions)
            if 'm' in count_text:
                number = float(count_text.replace('m', ''))
                return int(number * 1000000)
            
            # Handle regular numbers
            return int(re.sub(r'[^\d]', '', count_text))
                
        except Exception:
            return None
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from Instagram URL"""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            # Handle posts and reels
            for key in ['p', 'reel', 'reels']:
                if key in path_parts:
                    idx = path_parts.index(key)
                    if idx + 1 < len(path_parts):
                        return path_parts[idx + 1]
            
            return None
            
        except Exception:
            return None


async def scrape_instagram_video(video_url: str, headless: bool = True) -> Dict[str, Any]:
    """
    Convenience function to scrape a single Instagram video
    
    Args:
        video_url: Instagram video URL
        headless: Whether to run browser in headless mode
        
    Returns:
        Dictionary containing extracted trending words and metadata
    """
    async with InstagramScraper(headless=headless) as scraper:
        return await scraper.extract_trending_words_from_video(video_url)


async def scrape_multiple_videos(
    video_urls: List[str], headless: bool = True
) -> List[Dict[str, Any]]:
    """
    Scrape multiple Instagram videos
    
    Args:
        video_urls: List of Instagram video URLs
        headless: Whether to run browser in headless mode
        
    Returns:
        List of dictionaries containing extracted trending words and metadata
    """
    async with InstagramScraper(headless=headless) as scraper:
        results: List[Dict[str, Any]] = []
        for url in video_urls:
            result = await scraper.extract_trending_words_from_video(url)
            results.append(result)
            await asyncio.sleep(2)
        return results


# Example usage and testing
async def main():
    """Example usage of the Instagram scraper"""
    # Example video URL (replace with actual Instagram video URL)
    video_url = "https://www.instagram.com/p/EXAMPLE_VIDEO_ID/"
    
    try:
        # Scrape single video
        result = await scrape_instagram_video(video_url, headless=False)
        
        # Print results in JSON format
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Save results to file
        with open(
            'instagram_scraping_results.json', 'w', encoding='utf-8'
        ) as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        print("\nResults saved to instagram_scraping_results.json")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
