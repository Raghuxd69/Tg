import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters

# Define global proxy configuration
proxy_config = {
    'http': None,
    'https': None,
}

# Define global proxy authentication configuration
proxy_auth = {
    'username': None,
    'password': None
}

# Define global user credentials
user_credentials = {
    'email': None,
    'password': None
}

# Function to generate a GUID (or similar unique identifier)
def generate_guid():
    return 'unique-guid'

# Function to get a random User-Agent
def get_random_ua():
    return 'Crunchyroll/3.59.0 Android/14 okhttp/4.12.0'

# Define your bot's token here
TOKEN = '7475688323:AAHVzrao_wLgIl-QqfowuoAbtZE2oTVv5jQ'

def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Set Proxy", callback_data='set_proxy')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Welcome! Use /check to get subscription benefits.', reply_markup=reply_markup)

def set_proxy(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Please send your proxy in the format: `proxy:port:user:password`")

    # Store state to track that the user is setting a proxy
    context.user_data['setting_proxy'] = True

def handle_message(update: Update, context: CallbackContext):
    if context.user_data.get('setting_proxy'):
        proxy_info = update.message.text

        # Extract and validate proxy information
        parts = proxy_info.split(':')
        if len(parts) == 4:
            proxy_host, proxy_port, proxy_user, proxy_pass = parts
            proxy_url = f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'

            # Set the proxy configuration
            proxy_config['http'] = proxy_url
            proxy_config['https'] = proxy_url
            proxy_auth['username'] = proxy_user
            proxy_auth['password'] = proxy_pass

            update.message.reply_text(f'Proxy set to: {proxy_url}')
            
            # Ask user for their Crunchyroll credentials
            update.message.reply_text('Please send your Crunchyroll credentials in the format: `email:password`')
            context.user_data['awaiting_credentials'] = True
            
            # Reset state
            context.user_data['setting_proxy'] = False
        else:
            update.message.reply_text('Invalid proxy format. Please use the format: `proxy:port:user:password`')
    elif context.user_data.get('awaiting_credentials'):
        credentials = update.message.text.split(':')
        if len(credentials) == 2:
            user_credentials['email'], user_credentials['password'] = credentials
            update.message.reply_text('Credentials set. Use /check to perform the web check.')
            context.user_data['awaiting_credentials'] = False
        else:
            update.message.reply_text('Invalid format. Please send your Crunchyroll credentials in the format: `email:password`')
    else:
        update.message.reply_text('Use /start to interact with the bot.')

def check_proxy(proxies):
    test_url = 'https://www.google.com'
    try:
        response = requests.get(test_url, proxies=proxies, auth=(proxy_auth['username'], proxy_auth['password']), timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False

def check(update: Update, context: CallbackContext):
    if not proxy_config['http'] or not proxy_config['https']:
        update.message.reply_text('Please set a proxy first using the "Set Proxy" button in the /start menu.')
        return
    
    if not user_credentials['email'] or not user_credentials['password']:
        update.message.reply_text('Please provide your Crunchyroll credentials first.')
        return

    device_id = generate_guid()
    ua = get_random_ua()
    email = user_credentials['email']
    password = user_credentials['password']
    grant_type = 'password'
    scope = 'offline_access'
    device_name = 'realme Narzo 30'
    device_type = 'Google Pixel 8 Pro'
    
    headers = {
        'Authorization': 'Basic d2piMV90YThta3Y3X2t4aHF6djc6MnlSWlg0Y0psX28yMzRqa2FNaXRTbXNLUVlGaUpQXzU=',
        'x-datadog-sampling-priority': '0',
        'etp-anonymous-id': device_id,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip',
        'User-Agent': ua
    }

    token_url = 'https://beta-api.crunchyroll.com/auth/v1/token'
    data = {
        'username': email,  # Use email as the username
        'password': password,
        'grant_type': grant_type,
        'scope': scope,
        'device_id': device_id,
        'device_name': device_name,
        'device_type': device_type
    }

    try:
        response = requests.post(token_url, headers=headers, data=data, proxies=proxy_config, auth=(proxy_auth['username'], proxy_auth['password']))
        if response.status_code == 200:
            response_json = response.json()
            if 'access_token' in response_json:
                access_token = response_json['access_token']
            else:
                update.message.reply_text('Invalid credentials or token error')
                return
        else:
            update.message.reply_text('Request failed')
            return
    except requests.RequestException as e:
        update.message.reply_text(f'An error occurred: {e}')
        return

    me_url = 'https://beta-api.crunchyroll.com/accounts/v1/me'
    headers['Authorization'] = f'Bearer {access_token}'

    try:
        response = requests.get(me_url, headers=headers, proxies=proxy_config, auth=(proxy_auth['username'], proxy_auth['password']))
        if response.status_code == 200:
            response_json = response.json()
            if 'external_id' in response_json:
                external_id = response_json['external_id']
            else:
                update.message.reply_text('Failed to retrieve external_id')
                return
        else:
            update.message.reply_text('Request failed')
            return
    except requests.RequestException as e:
        update.message.reply_text(f'An error occurred: {e}')
        return

    benefits_url = f'https://beta-api.crunchyroll.com/subs/v1/subscriptions/{external_id}/benefits'
    try:
        response = requests.get(benefits_url, headers=headers, proxies=proxy_config, auth=(proxy_auth['username'], proxy_auth['password']))
        if response.status_code == 200:
            response_json = response.json()
            if 'fan' in response_json or 'premium' in response_json or 'no_ads' in response_json:
                update.message.reply_text('Subscription benefits found: ' + json.dumps(response_json, indent=2))
            elif 'subscription.not_found' in response_json or 'Subscription Not Found' in response_json:
                update.message.reply_text('Subscription not found')
            else:
                update.message.reply_text('No benefits found or subscription not found')
        else:
            update.message.reply_text('Request failed')
    except requests.RequestException as e:
        update.message.reply_text(f'An error occurred: {e}')

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("check", check))
    dp.add_handler(CallbackQueryHandler(set_proxy, pattern='^set_proxy$'))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
