# Quick setup script for Halle Appointment Bot

set -e

echo "======================================================"
echo "🤖 Halle Appointment Bot - Setup"
echo "======================================================"
echo

# Check Python
echo "✓ Checking Python..."
python3 --version

# Create virtual environment
echo
echo "✓ Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo
echo "✓ Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo
echo "✓ Installing Playwright browsers..."
playwright install chromium

# Setup .env file
echo
if [ ! -f .env ]; then
    echo "✓ Creating .env file..."
    cp .env.example .env
    echo
    echo "⚠️  Please edit .env and add your Telegram credentials:"
    echo "    - TELEGRAM_BOT_TOKEN: Get from @BotFather on Telegram"
    echo "    - TELEGRAM_CHAT_ID: Your Telegram Chat ID"
    echo
    echo "    See README.md for detailed instructions"
else
    echo "✓ .env file already exists"
fi

echo
echo "======================================================"
echo "✅ Setup complete!"
echo "======================================================"
echo
echo "Next steps:"
echo "1. Edit .env with your Telegram credentials"
echo "2. Run: source venv/bin/activate"
echo "3. Test scraper: python test_scraper.py"
echo "4. Start bot: python bot.py"
echo
