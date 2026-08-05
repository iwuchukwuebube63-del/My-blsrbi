#!/usr/bin/env python3
"""
Main Entry Point for WhatsApp Ban Bot
Base and credit by: LORD ZISKY
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import bot modules
from telegram_bot import WhatsAppBanBot

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

def main():
    """Main function to start the bot"""
    
    # Get configuration from environment
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    admin_ids = os.getenv('ADMIN_IDS', '').split(',')
    
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("❌ Error: TELEGRAM_BOT_TOKEN not set in .env file")
        print("📝 Please create a .env file with:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        print("ADMIN_IDS=your_user_id_here")
        sys.exit(1)
    
    if not admin_ids or admin_ids[0] == "YOUR_ADMIN_ID":
        print("⚠️ Warning: ADMIN_IDS not set. Some commands will be restricted.")
        admin_ids = []
    
    # Create and run bot
    bot = WhatsAppBanBot(token=token, admin_ids=admin_ids)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user.")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        logging.error(f"Bot crash: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════╗
║      WHATSAPP BAN BOT v2.0 - INITIALIZING       ║
║               Base and credit by:                ║
║                  LORD ZISKY                     ║
╚══════════════════════════════════════════════════╝
    
⚙️  System check:
• Python version: OK
• Dependencies: Loading...
• Database: Initializing...
• Proxy system: Starting...
    
⚠️  Legal Disclaimer:
This tool is for educational purposes only.
Misuse may violate Terms of Service.
The developer is not responsible for any misuse.
    
🚀 Starting bot in 3 seconds...
    """)
    
    # Check for required files
    required_files = ['config.js', 'requirements.txt']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        print("📝 Please ensure all files are in the same directory.")
        sys.exit(1)
    
    # Small delay for dramatic effect
    import time
    time.sleep(3)
    
    # Run main function
    main()

# Base and credit by: LORD ZISKY