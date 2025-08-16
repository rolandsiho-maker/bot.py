import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from apscheduler.schedulers.background import BackgroundScheduler

# --- Configuration et variables globales ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CODE = "SIHO ISAAC ROLAND 840106"
ADMIN_SESSION_TIMEOUT = 30 * 60  # 30 minutes
ADMIN_USERNAME = "@ZACKCASH22"
CHANNEL_LINK = "https://t.me/+6ya0mglfi4A2NGZk"
BOT_ACTIVE_START_HOUR = 7
BOT_ACTIVE_END_HOUR = 0  # Représente 00h00, la logique doit gérer cela

# États de conversation
GET_PLAYER_ID, ADMIN_MENU, VERIFY_ADMIN, MANAGE_USERS, SEARCH_USER = range(5)

# Fichiers de données
USERS_FILE = 'data/users.json'
PENDING_VERIFICATIONS_FILE = 'data/pending_verifications.json'
MESSAGES_PROGRAMMES_FILE = 'data/messages_programmes.json'
ADMINS_FILE = 'data/admins.json'

# Scheduler pour les messages quotidiens
scheduler = BackgroundScheduler()

# --- Fonctions utilitaires ---

# Crée les dossiers et fichiers si non existants
if not os.path.exists('data'):
    os.makedirs('data')

def load_data(file_name):
    if not os.path.exists(file_name):
        with open(file_name, 'w') as f:
            json.dump({}, f)
    with open(file_name, 'r') as f:
        return json.load(f)

def save_data(file_name, data):
    with open(file_name, 'w') as f:
        json.dump(data, f, indent=4)

def is_admin(user_id):
    admins = load_data(ADMINS_FILE)
    return str(user_id) in admins and admins[str(user_id)]['session_end'] > datetime.now().timestamp()

# --- Fonctions du bot ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name

    users = load_data(USERS_FILE)

    if user_id in users:
        # Utilisateur déjà enregistré
        keyboard = [[InlineKeyboardButton("Accéder aux bots", callback_data='access_bots')]]
        await update.message.reply_text(
            f"Bonjour {user_name}, ravi de te revoir !",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Nouvel utilisateur
        users[user_id] = {'name': user_name, 'joined_date': datetime.now().isoformat(), 'status': 'new'}
        save_data(USERS_FILE, users)

        keyboard = [
            [InlineKeyboardButton("Oui, vérifier mon inscription", callback_data='verify_promo')],
            [InlineKeyboardButton("Non, je n'ai pas de code", callback_data='no_code')]
        ]
        await update.message.reply_text(
            f"Bonjour {user_name}, bienvenue dans notre communauté !\nRejoins notre canal officiel : {CHANNEL_LINK}\nEs-tu déjà inscrit avec le code promo SANA33 ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return ConversationHandler.END

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    # Suppression du message précédent
    try:
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    except Exception as e:
        print(f"Erreur lors de la suppression du message : {e}")

    if query.data == 'verify_promo':
        await query.message.reply_text("Veuillez envoyer votre ID de joueur pour vérification.")
        return GET_PLAYER_ID
    
    elif query.data == 'no_code':
        await query.message.reply_text(f"Aucun problème ! Pour obtenir le code promo et vous inscrire, contactez {ADMIN_USERNAME}.")
        return ConversationHandler.END
        
    elif query.data == 'access_bots':
        # Logique pour accéder au menu des bots
        await query.message.reply_text("Voici le menu des bots...")
        return ConversationHandler.END
    
    elif query.data == 'exit':
        await query.message.reply_text("Vous avez quitté le menu.")
        return ConversationHandler.END

    return ConversationHandler.END
    
async def get_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    player_id = update.message.text
    user_id = str(update.effective_user.id)
    
    pending_verifications = load_data(PENDING_VERIFICATIONS_FILE)
    
    pending_verifications[user_id] = {
        'player_id': player_id,
        'username': update.effective_user.username or update.effective_user.first_name,
        'submitted_at': datetime.now().isoformat()
    }
    save_data(PENDING_VERIFICATIONS_FILE, pending_verifications)
    
    await update.message.reply_text("Vérification en cours... Un administrateur va examiner votre demande.")
    
    return ConversationHandler.END

async def admin_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_admin(update.effective_user.id):
        await update.message.reply_text("Vous êtes déjà connecté en tant qu'administrateur. Voici le menu.")
        # Afficher le menu admin
        return ADMIN_MENU
    else:
        await update.message.reply_text("Veuillez entrer le code d'accès administrateur.")
        return VERIFY_ADMIN

async def verify_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == ADMIN_CODE:
        user_id = str(update.effective_user.id)
        admins = load_data(ADMINS_FILE)
        admins[user_id] = {
            'username': update.effective_user.username,
            'session_end': (datetime.now() + timedelta(minutes=30)).timestamp()
        }
        save_data(ADMINS_FILE, admins)
        
        await update.message.reply_text("Accès administrateur accordé pour 30 minutes. Voici le menu admin.")
        # Afficher le menu admin
        return ADMIN_MENU
    else:
        await update.message.reply_text("Code incorrect. Veuillez réessayer.")
        return ConversationHandler.END

async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Logique pour le menu admin
    pass

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), MessageHandler(filters.TEXT & ~filters.COMMAND, admin_entry)],
        states={
            GET_PLAYER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_player_id)],
            VERIFY_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_admin)],
            ADMIN_MENU: [CallbackQueryHandler(handle_admin_menu)],
        },
        fallbacks=[CommandHandler('start', start), CommandHandler('exit', lambda u, c: ConversationHandler.END)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    print("Le bot est en cours d'exécution...")
    application.run_polling()

if __name__ == '__main__':
    main()
