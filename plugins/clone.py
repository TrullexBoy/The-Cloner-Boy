import asyncio
import re 
import logging
from pyrogram.enums import MessageMediaType
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from config import Config

logger = logging.getLogger(__name__)

CURRENT = {}
CHANNEL = {}
CANCEL = {}
DELAY = {}
FORWARDING = {}

@Client.on_message(filters.regex('cancel') & filters.chat(-1002243785887))
async def cancel_forward(bot, message):
    cancel = await message.reply("Trying to cancel forwarding...")
    if FORWARDING.get(message.from_user.id):
        CANCEL[message.from_user.id] = True
        await cancel.edit("Successfully Forward Canceled!")
    else:
        await cancel.edit("No Forward Countinue Currently!")
        
@Client.on_message((filters.forwarded | (filters.regex("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")) & filters.text) & filters.chat(-1002243785887) & filters.incoming)
async def send_for_forward(bot, message):
    if Config.ADMINS and not ((str(message.from_user.id) in Config.ADMINS) or (message.from_user.username in Config.ADMINS)):
        return await message.reply("You Are Not Allowed To Use This UserBot")    
    if message.text:
        regex = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(message.text)
        if not match:
            return await message.reply('Invalid link for forward!')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    elif message.forward_from_chat.type in [enums.ChatType.CHANNEL, enums.ChatType.GROUP]:
        last_msg_id = message.forward_from_message_id
        chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    else:
        return

    try:
        source_chat = await bot.get_chat(chat_id)
    except Exception as e:
        return await message.reply(f'Error - {e}')

    if source_chat.type not in [enums.ChatType.CHANNEL, enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply("I can forward only channels and groups.")

    # last_msg_id is same to total messages
    if FORWARDING.get(message.from_user.id):
        return await message.reply('Wait until previous process complete.')
    msg = await message.reply('Starting Forwarding...')
    try:
        chat = int(chat_id)
    except:
        chat = chat_id
    lst_msg_id = last_msg_id
    await forward_files(int(lst_msg_id), chat, msg, bot, message.from_user.id)
    
                    
@Client.on_message(filters.chat(-1002243785887) & filters.command(['set_skip']))
async def set_skip_number(bot, message):
    try:
        _, skip = message.text.split(" ")
    except:
        return await message.reply("Give me a skip number.")
    try:
        skip = int(skip)
    except:
        return await message.reply("Only support in numbers.")
    CURRENT[message.from_user.id] = int(skip)
    await message.reply(f"Successfully set <code>{skip}</code> skip number.")

@Client.on_message(filters.chat(-1002243785887) & filters.command(['set_delay'])) 
async def set_delay_number(bot, message):
    try:
        _, delay = message.text.split(" ")
    except:
        return await message.reply("Give me a delay in seconds.")
    try:
        delay = int(delay)
    except:
        return await message.reply("Only support in numbers.")
    DELAY[message.from_user.id] = int(delay)
    await message.reply(f"Successfully set <code>{delay}</code> delay in second.")

@Client.on_message(filters.chat(-1002243785887) & filters.command(['set_channel']))
async def set_target_channel(bot, message):    
    if Config.ADMINS and not ((str(message.from_user.id) in Config.ADMINS) or (message.from_user.username in Config.ADMINS)):
        return await message.reply("You Are Not Allowed To Use This UserBot")
    
    try:
        _, chat_id = message.text.split(" ")
    except:
        return await message.reply("Give me a target channel ID")
    try:
        chat_id = int(chat_id)
    except:
        return await message.reply("Give me a valid ID")

    try:
        chat = await bot.get_chat(chat_id)
    except:
        return await message.reply("Make me a admin in your target channel.")
    CHANNEL[message.from_user.id] = int(chat.id)
    await message.reply(f"Successfully set {chat.title} target channel.")


async def forward_files(lst_msg_id, chat, msg, bot, user_id):
    delay = DELAY.get(user_id) if DELAY.get(user_id) else 4
    forwarded = 0
    deleted = 0
    unsupported = 0
    fetched = 0
    to_channel = -1001569283029
    try:
        skip_idd = await bot.get_messages(-1001631481154, 8)
    except Exception as e:
        logger.exception(e)
        return await msg.edit(f"Error - {e}")
    skip_id = (str(skip_idd.text)).strip()
    try:
        current = int(skip_id)
    except:
        return await msg.edit("Skip Number Not a integer")
    current = int(skip_id)
    if current > lst_msg_id or current == lst_msg_id:
        return await msg.edit("First Set Skip Number")
    CANCEL[user_id] = False
    FORWARDING[user_id] = True
    # lst_msg_id is same to total messages

    try:
        async for message in bot.iter_messages(chat, lst_msg_id, current):
            if CANCEL.get(user_id):
                await msg.edit(f"Successfully Forward Canceled!")
                break
            if forwarded == 500:
                #await msg.edit(f'Forward Completed!\n\nTotal Messages: <code>{lst_msg_id}</code>\nCompleted Messages: <code>{current} / {lst_msg_id}</code>\nFetched Messages: <code>{fetched}</code>\nTotal Forwarded Files: <code>{forwarded}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon Media Files: <code>{unsupported}</code>')
                #await bot.edit_message_text(-1001631481154, 8, f"{current}")
                break
            current += 1
            fetched += 1
            if current % 20 == 0:
                await msg.edit_text(text=f'''Forward Processing...\n\nTotal Messages: <code>{lst_msg_id}</code>\nCompleted Messages: <code>{current} / {lst_msg_id}</code>\nForwarded Files: <code>{forwarded}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon Media Files: <code>{unsupported}</code>\nDelay Second: <code>{delay}</code>\n\n send "<code>cancel</code>" for stop''')
            if message.empty:
                deleted += 1
                continue
            try:
                if message.media:
                    if message.media not in [
                        MessageMediaType.PHOTO,
                        MessageMediaType.DOCUMENT,
                        MessageMediaType.AUDIO,
                        MessageMediaType.STICKER,
                        MessageMediaType.VIDEO]:
                        continue 
                    media = getattr(message, message.media.value, None)
                    if media:
                        try:
                            await bot.send_cached_media(
                                chat_id=to_channel,
                                file_id=media.file_id,
                                caption=message.caption
                            )
                        except FloodWait as e:
                            await asyncio.sleep(e.value)  # Wait "value" seconds before continuing
                            await bot.send_cached_media(
                                chat_id=to_channel,
                                file_id=media.file_id,
                                caption=message.caption
                            )
                else:
                    try:
                        await bot.copy_message(
                            chat_id=to_channel,
                            from_chat_id=chat,
                            caption='**{message.caption}**',
                            message_id=message.id,
                            parse_mode=enums.ParseMode.MARKDOWN
                        )
                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                        await bot.copy_message(
                            chat_id=to_channel,
                            from_chat_id=chat,
                            caption='**{message.caption}**',
                            message_id=message.id,
                            parse_mode=enums.ParseMode.MARKDOWN
                        )
            except Exception as e:
                if "The media caption" in str(e):
                    continue
                logger.exception(e)
                return await msg.reply(f"Forward Canceled!\n\nError - {e}")               
            forwarded += 1
            await asyncio.sleep(delay)            
    except Exception as e:
        logger.exception(e)
        await msg.reply(f"Forward Canceled!\n\nError - {e}")
    else:
        await msg.edit(f'Forward Completed!\n\nTotal Messages: <code>{lst_msg_id}</code>\nCompleted Messages: <code>{current} / {lst_msg_id}</code>\nFetched Messages: <code>{fetched}</code>\nTotal Forwarded Files: <code>{forwarded}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon Media Files: <code>{unsupported}</code>')
        #if (str(skip_idd.text)).strip() == str(current):
            #return await msg.reply("First Set Skip Number")
        #else:
        await bot.edit_message_text(-1001631481154, 8, f"{current}")
        FORWARDING[user_id] = False
