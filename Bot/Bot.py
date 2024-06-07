import telebot
from telebot import types
from threading import Thread
from secrets import secrets
from sound_request import SoundRequest
from sender_queue import SenderQueue
from sound_receiver import receive_sound
from context import Context
#import sound_user_send

token = secrets.get('BOT_API_TOKEN')
bot = telebot.TeleBot(token)

users_context = Context()

requests_queue = SenderQueue('requests_queue')
requests_queue.connect()


def check_is_generating(message):
    user_context = users_context.get_data(message.from_user.id, message.chat.id)

    if user_context != None and 'is_generating' in user_context:
        bot.send_message(message.chat.id, text='Идет процесс генерации аудиозаписи. Подождите окончания процесса.')
        return True

    return False

@bot.message_handler(commands=['help'])
def get_help(message):
    if message.text == '/help':
        bot.send_message(message.chat.id, text='Я бот, который может генерировать звуки заданной продолжительности. \n\n'+
                         'Просто опишите словами на английском языке какой звук вы бы хотели получить, например, "Birds chirping", '+
                         '(если вы используете другой язык, то не получите желаемого результата, но мы работаем над этим) '+
                         'потом я спрошу вас какой продолжительности должен быть этот звук в секундах, вам надо написать число не превышающее 300, '+
                         'например, "90". \n\nЗатем вы ждете непродолжительное время и вуаля! '+
                         'Вы можете прослушать и при необходимости скачать сгенерированную аудиозапись.')
    else:
        bot.send_message(message.chat.id, text='Что-то пошло не так. Вы не должны были здесь находиться')

@bot.message_handler(commands=['start'])
def start_message(message):

    if check_is_generating(message):
        return

    users_context.reset_data(message.from_user.id, message.chat.id)

    if message.text == '/help':
        bot.send_message(message.chat.id, text='Опишите звук на английском языке, который бы вы хотели получить.')
    else:
        bot.send_message(message.chat.id, text=f'Здравствуйте, {message.from_user.first_name}! Опишите звук на английском языке, который бы вы хотели получить.')
    
    bot.register_next_step_handler(message, get_prompt)

def get_prompt(message):
    
    if check_is_generating(message):
        return

    prompt = message.text

    if prompt.isnumeric() or prompt == '': 
        bot.send_message(message.chat.id, text='Пожалуйста, введите свой запрос в виде строки.')
        bot.register_next_step_handler(message, get_prompt)
        return
  
    if prompt == '/help':
        get_help(message)
        start_message(message)

    elif prompt == '/start':
        start_message(message)

    else:
        bot.send_message(message.chat.id, text='Ок, теперь напишите какой продолжительности звук вы бы хотели получить в секундах (не более 300 секунд).')
        bot.register_next_step_handler(message, get_duration)

        users_context.add_data(message.from_user.id, message.chat.id, prompt=prompt)


def get_duration(message):
    

    prompt = users_context.get_data(message.from_user.id, message.chat.id)['prompt']
    duration = message.text


    if duration == '/help':
        get_help(message)
        bot.send_message(message.chat.id, text='Напишите какой продолжительности звук вы бы хотели получить в секундах (не более 300 секунд).')
        bot.register_next_step_handler(message, get_duration)
        #return

    elif duration == '/start':
        start_message(message)

    elif duration.isnumeric() == False:

        bot.send_message(message.chat.id, text='Пожалуйста, введите продолжительность в виде целого числа.')
        bot.register_next_step_handler(message, get_duration)
    
    elif int(duration) > 300:

        bot.send_message(message.chat.id, text='Продолжительность не должна превышать 300 секунд (5 минут). Пожалуйста, введите число меньше.')
        bot.register_next_step_handler(message, get_duration)

    else:

        keyboard = types.InlineKeyboardMarkup()

        key_yes = types.InlineKeyboardButton(text='Да', callback_data='yes')
        key_no = types.InlineKeyboardButton(text='Нет', callback_data='no')

        keyboard.add(key_yes)
        keyboard.add(key_no)

        question = f'Вам нужен звук "{prompt}" с продолжительностью {duration} секунд?'

        bot.send_message(message.chat.id, text=question, reply_markup=keyboard)

        users_context.add_data(message.from_user.id, message.chat.id, duration=duration)


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
   
    user_context = users_context.get_data(call.from_user.id, call.message.chat.id)

    if user_context == None:
        return

    if call.data == 'yes':

        if ('prompt' in user_context) and ('duration' in user_context) and ('is_generating' not in user_context):

            bot.send_message(call.message.chat.id, text='Ок, подождите немного, аудио генерируется.', reply_markup=types.ReplyKeyboardRemove())
            users_context.add_data(call.from_user.id, call.message.chat.id, is_generating=True)
            
            json_data = SoundRequest(call.message.chat.id, call.from_user.id, int(user_context['duration']), user_context['prompt']).json_create()

            requests_queue.send_message(json_data)

            #receive_data(call.message.chat.id, call.from_user.id)

    elif call.data == 'no':
        if 'is_generating' in user_context:
            return

        users_context.reset_data(call.from_user.id, call.message.chat.id)

        bot.send_message(call.message.chat.id, text='Ок, начнем с начала. Опишите звук на английском языке, который бы вы хотели получить.', reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(call.message, get_prompt)

'''
def receive_data(chatid, userid):
    sound_data = sound_user_send.sound_receive()

    #sound_file = open(file_path, mode='rb')
    bot.send_audio(chatid, sound_data)
    #sound_file.close()
'''

def start_after_audio_sent(user_id, chat_id):
    bot.send_message(chat_id, text='Звук сгенерирован успешно.')
    bot.send_message(chat_id, text='Для генерации нового звука, введите новое описание на английском языке.')
    #bot.register_next_step_handler(message, get_prompt)
    bot.register_next_step_handler_by_chat_id(chat_id, get_prompt)


receiver_thread = Thread(target=receive_sound, args=(bot, users_context, start_after_audio_sent,)) #receive sound and send it to bot
receiver_thread.start()

bot.polling(none_stop=True, interval=0)
requests_queue.close()