from telegram import Update
from telegram.constants import ParseMode
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, PicklePersistence, CallbackQueryHandler
import logging
import aiohttp
import aiofiles
import asyncio
import math
import os
import json
import io
import telegram
from PIL import ImageDraw, ImageFont, Image

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_photo("https://i.ibb.co/R0Xmf2M/sss.png", caption=f'Hi <b>{update.message.from_user.first_name}</b>!,\n\nI am the all new <b>Magic AI Bot</b>,Ai Artwork telegram generator bot that generates hyperrealistic artworks in a matter of minutes.\
                                    \n\nYou can use the <b>/magic</b> followed by the prompt you want to generate your image with\
                                        \n\neg.\n<i><b>/magic</b> release your creativity</i>\n\n',
                                    parse_mode=ParseMode.HTML
                                    )

async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inputs = update.message.text.split()[1:]  # Split the message and get all inputs after the /gen command
    prompt = " ".join(inputs)
    print(prompt)

    if not inputs:
        await context.bot.send_message(
            chat_id=update.message.chat.id,
            text=f'Hello {update.message.from_user.first_name}, Please enter the inputs after the /magic command',
        )
        return

    inline_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("MGC-Realistic", callback_data={'prompt': prompt, 'model': 'realistic-vision-v13', 'username': update.message.from_user.first_name}),
                InlineKeyboardButton("MGC-Protogen", callback_data={'prompt': prompt, 'model': 'protogen-3.4', 'username': update.message.from_user.first_name})
            ],
            [
                InlineKeyboardButton("MGC-Analog Diffusion", callback_data={'prompt': prompt, 'model': 'analog-diffusion', 'username': update.message.from_user.first_name}),
                InlineKeyboardButton("MGC-AnythingV4", callback_data={'prompt': prompt, 'model': 'anything-v4', 'username': update.message.from_user.first_name}),
            ]
        ]
    )
    

    await context.bot.send_message (
        chat_id=update.message.chat.id,
        text=f'<b>{update.message.from_user.first_name},\n\nYou are generating an image...\nPlease choose a style for your image.</b>\n\n<a rel="nofollow" href="https://rb.gy/szbrol">https://magic-ai.org/</a>',
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.HTML
    )

    
async def getModel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    json_data = json.dumps(query.data)
    print(json_data)
    username = json.loads(json_data)['username']

    datadict = json.loads(json_data)
    if 'prompt' in datadict:
        prompt = json.loads(json_data)['prompt']
        model = json.loads(json_data)['model']

    if 'url' in datadict:
        print('Upscale detected')
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=f'Request of: <b>{username}</b>\n\nPlease wait while we upscale your image.',
            parse_mode=ParseMode.HTML
        )
        await upscale(query.message, datadict['url'], context, username)
        return 

    await context.bot.send_message (
        chat_id=query.message.chat.id,
        text=f'<b>{username}</b> is generating an image.\n\nYour image is being generated...',
        parse_mode=ParseMode.HTML
    )
    await requestApi(query.message, prompt, model, context, username)
    
async def upscale(update: Update, downloadUrl, context: ContextTypes.DEFAULT_TYPE, username) -> None:
    url = 'https://stablediffusionapi.com/api/v3/super_resolution'
    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        "key": "YimEHAg0HxDBkYtZp7X8ZEv7u84XWtt66TgVA78BnGWQlLHe6cdoDQREjpV5",
        "url": downloadUrl,
        "scale": 3,
        "webhook": 'null',
        "face_enhance": 'false'
    }
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                print(data)
                if resp.status == 200:
                    if data['status'] == 'success':
                        try:
                            await context.bot.send_photo(
                                chat_id=update.chat.id,
                                photo=data['output'],
                                caption=f'Request of: <b>{username}</b>\n\nHere is your upscaled image.',
                                parse_mode=ParseMode.HTML
                                
                            )
                        except Exception as e:
                            await context.bot.send_message(
                                chat_id=update.chat.id,
                                text=f'Request of: <b>{username}</b>\n\n<b>Sorry, we were unable to upscale your image.</b>\n\n Please try again.',
                                parse_mode=ParseMode.HTML
                            )
                        break
                    if data['status'] == 'processing' and data['messege'] == 'Request processing':
                        print('Requesting again')
                        await upscale(update, downloadUrl, context, username)
                    if data['status'] == 'processing' and data['messege'] == 'Try to fetch request after given estimated time':
                        if 'fetch_result' in data:
                            url = data['fetch_result']
                        if 'eta' in data:
                            eta = data['eta']
                            await processing_update(update, eta, context)
                            await asyncio.sleep(math.ceil(eta))
                        continue
                    if data['status'] == 'error':
                        await error_update(update, context, username)
                        break
                    if data['status'] == 'failed':
                        continue
                    else:
                        raise Exception(f'Request failed with status code {resp.status}')


async def requestApi(update: Update, prompt, model, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:

    print('MODEL THAT WILL BE USED: ', model)
    url = 'https://stablediffusionapi.com/api/v3/dreambooth'
    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        'key': 'YimEHAg0HxDBkYtZp7X8ZEv7u84XWtt66TgVA78BnGWQlLHe6cdoDQREjpV5',
        'model_id': model,
        'prompt': prompt,
        'negative_prompt': 'painting, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, deformed, ugly, blurry, bad anatomy, bad proportions, extra limbs, cloned face, skinny, glitchy, double torso, extra arms, extra hands, mangled fingers, missing lips, ugly face, distorted face, extra legs, anime',
        'width': '512',
        'height': '512',
        'samples': '1',
        'num_inference_steps': '30',
        'seed': None,
        'guidance_scale': 7.5,
        'webhook': None,
        'track_id': None,
        #'safety_checker': 'yes'
    }
    
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                print(data)
                if resp.status == 200:
                    if data['status'] == 'success':
                        await downloadImage(data['id'], data['output'][0], update, prompt, model, context, username)
                        return
                    if data['status'] == 'processing' and data['messege'] == 'Request processing':
                        print('Requesting again')
                        await requestApi(update, prompt, model, context, username)
                    if data['status'] == 'processing' and data['messege'] == 'Try to fetch request after given estimated time':
                        if 'fetch_result' in data:
                            url = data['fetch_result']
                        if 'eta' in data:
                            eta = data['eta']
                            await processing_update(update, eta, context)
                            await asyncio.sleep(math.ceil(eta))
                        continue
                    if data['status'] == 'error':
                        await error_update(update, context, username)
                        break
                    if data['status'] == 'failed':
                        continue
                    else:
                        raise Exception(f'Request failed with status code {resp.status}')
                    
async def downloadImage(id: int, downloadUrl: str, update: Update, prompt: str, model: str, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(downloadUrl) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f'{id}.png', mode='wb')
                    await f.write(await resp.read())
                    # call watermark function
                    if await add_watermark(f'{id}.png', 'https://t.me/aigonewild', update, context, username) == False:
                        await send_image(update, id, prompt, model, downloadUrl, context, username)
                        os.remove(f'{id}.png')
                        os.remove(f'{id}_watermarked.png')
                        await f.close()
    except Exception as e:
        print(f'An error occurred: {e}')

async def processing_update(update: Update, eta: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    eta = math.ceil(eta)


    text='Image requested by: {0}!\n\nI am still processing your image please wait...\n\n<b>ETA: {1} seconds.</b>\n'.format(update.from_user.first_name, math.ceil(eta))
 
    await context.bot.send_message(
		chat_id=update.chat.id,
        text=text,
        parse_mode=ParseMode.HTML
	)
    
async def error_update(update: Update, context: ContextTypes.DEFAULT_TYPE, username) -> None:

    text= 'Hi {update.from_user.first_name}!\n\nDue to in-demand accesses and requests your image cannot be generated.\n\nPlease try again later.\n'
    await context.bot.send_message(
            chat_id=update.chat.id,
            text = f'{text}'
        )
        
async def send_image(update: Update, file_name: str, prompt: str, model: str, download_url: str, context: ContextTypes.DEFAULT_TYPE, username) -> None:
    with open(f'{file_name}_watermarked.png', 'rb') as file:

        
        await context.bot.send_photo(
            chat_id=update.chat.id,
            caption= f'Image request of: <b>{username}\n\n</b><b>Successful creation with mgc-{model}</b>!\n\nPrompt:\n(<b>{prompt}</b>)\n\nModel: <b>mgc-{model}</b>\n\n<a target="_blank">https://magic-ai.org/</a>',
            photo=telegram.InputFile(file),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Variation", callback_data={'prompt': prompt, 'model': model, 'username': username}),
                InlineKeyboardButton("Upscale", callback_data={'url': download_url, 'username': username}),
            ]]),
        )
        
async def add_watermark(file_path: str, watermark_text: str, update: Update, context: ContextTypes.DEFAULT_TYPE, username) -> None:
    async with aiofiles.open(file_path, "rb") as file:
        img_data = await file.read()
        try:
            with io.BytesIO(img_data) as img_stream:
                img = Image.open(img_stream)
                draw = ImageDraw.Draw(img)
                font = ImageFont.truetype('FeatureMono-Bold.ttf', 24)
                
                textwidth = draw.textlength(watermark_text, font)
                textheight = font.getsize(watermark_text)[1]

                width, height = img.size
                x = width / 2 - textwidth / 2
                y = height - textheight - 300

                draw.text((x+80, y+290), watermark_text, font=font)
            
                new_file_path = file_path.split('.')[0] + '_watermarked.png'
                img.save(new_file_path)
                return False
        except OSError as e:
            await context.bot.send_message (
                chat_id=update.chat.id,
                text=f'<b>Sorry {username}, Something went wrong. You can try regenerating your image again...</b>',
                parse_mode=ParseMode.HTML
                )
            return True

                
                
                    
persistence = PicklePersistence(filepath="arbitrarycallbackdatabot")
app = ApplicationBuilder().token("6095522761:AAFRRzX456igiLCAd-2qzhnplg6WymSPiBU").persistence(persistence).arbitrary_callback_data(True).build()

app.add_handler(CommandHandler("start", hello))
app.add_handler(CommandHandler("magic", gen))
app.add_handler(CallbackQueryHandler(getModel))
app.run_polling()