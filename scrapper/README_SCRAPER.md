# Instagram Video Scraper

A powerful Instagram scraper built with Playwright that extracts trending words, hashtags, mentions, and metadata from Instagram videos.

## Features

- **Trending Words Extraction**: Automatically identifies trending words, hashtags, and mentions
- **Video Metadata**: Extracts likes, views, timestamps, and other engagement metrics
- **Caption Analysis**: Analyzes video captions for trending content
- **Comment Mining**: Extracts and analyzes comments for trending topics
- **JSON Output**: Returns structured data in JSON format
- **Async Support**: Built with asyncio for efficient scraping
- **Mobile Emulation**: Uses mobile user agent for better Instagram compatibility

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers**:
   ```bash
   playwright install
   ```

## Usage

### Basic Usage

```python
import asyncio
from scrapper import scrape_instagram_video

async def main():
    # Scrape a single Instagram video
    video_url = "https://www.instagram.com/p/VIDEO_ID/"
    result = await scrape_instagram_video(video_url)
    
    # Print results
    print(json.dumps(result, indent=2))

# Run the scraper
asyncio.run(main())
```

### Advanced Usage

```python
import asyncio
from scrapper import InstagramScraper

async def main():
    async with InstagramScraper(headless=False) as scraper:
        # Scrape multiple videos
        urls = [
            "https://www.instagram.com/p/VIDEO1_ID/",
            "https://www.instagram.com/p/VIDEO2_ID/"
        ]
        
        for url in urls:
            result = await scraper.extract_trending_words_from_video(url)
            print(f"Video: {result['video_id']}")
            print(f"Trending words: {len(result['trending_words'])}")

asyncio.run(main())
```

### Command Line Usage

```bash
# Run the example
python example_usage.py

# Run the scraper directly
python scrapper.py
```

## Output Format

The scraper returns JSON data with the following structure:

```json
{
  "video_url": "https://www.instagram.com/p/VIDEO_ID/",
  "video_id": "VIDEO_ID",
  "timestamp": 1640995200.0,
  "trending_words": [
    {
      "word": "#viral",
      "type": "hashtag",
      "context": "...this video is going #viral on instagram...",
      "frequency": 3
    },
    {
      "word": "trending",
      "type": "trending_keyword",
      "context": "...this is trending right now...",
      "frequency": 2
    }
  ],
  "metadata": {
    "likes": 1500,
    "views": 5000,
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "caption": "Check out this amazing video! #viral #trending",
  "comments_count": 25,
  "sample_comments": ["Amazing!", "This is viral!"],
  "extraction_status": "success"
}
```

## Configuration

### Scraper Options

- `headless`: Run browser in headless mode (default: True)
- `slow_mo`: Delay between actions in milliseconds (default: 100)

### Trending Word Patterns

The scraper automatically detects:

- **Hashtags**: `#viral`, `#trending`, `#popular`
- **Mentions**: `@username`, `@influencer`
- **Trending Keywords**: `viral`, `trending`, `popular`, `hot`, `famous`
- **News Keywords**: `breaking`, `news`, `update`, `latest`
- **Reaction Words**: `amazing`, `incredible`, `unbelievable`, `wow`

## Error Handling

The scraper includes comprehensive error handling:

- Network timeouts and connection issues
- Instagram page structure changes
- Missing or inaccessible content
- Rate limiting and blocking

All errors are logged and included in the output with `extraction_status: "error"`.

## Best Practices

1. **Rate Limiting**: Add delays between requests to avoid being blocked
2. **User Agents**: The scraper uses mobile user agents for better compatibility
3. **Headless Mode**: Use headless mode for production, non-headless for debugging
4. **Error Handling**: Always check `extraction_status` in results
5. **Respect Terms**: Follow Instagram's terms of service and robots.txt

## Troubleshooting

### Common Issues

1. **Browser not starting**: Ensure Playwright is installed (`playwright install`)
2. **Page not loading**: Check internet connection and Instagram accessibility
3. **No data extracted**: Instagram may have changed page structure
4. **Rate limiting**: Add longer delays between requests

### Debug Mode

Run with `headless=False` to see what the scraper is doing:

```python
result = await scrape_instagram_video(url, headless=False)
```

## Dependencies

- `playwright`: Browser automation
- `asyncio`: Async programming support
- `json`: Data serialization
- `re`: Regular expressions for text parsing
- `logging`: Debugging and monitoring

## License

This project is for educational purposes. Please respect Instagram's terms of service.

## Contributing

Feel free to submit issues and enhancement requests!
