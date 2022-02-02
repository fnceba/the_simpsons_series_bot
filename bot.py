from threading import Timer
import threading
import telebot
import sqlite3
import re
import datetime
import time

bot = telebot.TeleBot("")
conn = sqlite3.connect("simpsons.db", check_same_thread=False)
curs = conn.cursor()
lock = threading.Lock()
#curs.execute("CREATE TABLE IF NOT EXISTS series (ruid TEXT, engid, season INTEGER, part INTEGER, caption TEXT)")
#curs.execute("CREATE TABLE IF NOT EXISTS lang (id INTEGER, language TEXT)")
#conn.commit()
bot_logger = telebot.TeleBot('')

messages={'ru':["Привет! Чтобы продолжить, просто введи сезон и серию через пробел. Например, если тебя интересует 1 сезон и 2 серия, отправь \"1 2\". \n Чтобы поменять язык, введи команду /language", "Не нашел!", "Выбери язык:", "Готово"],
            'en':["Hello there! Just send \"1 2\" and see what you got. Be carefull to the whitespace in the middle of this string! \n Also send /language to switch it.", "Nut found!🌰", "Choose language:","Done"]}
sqnums={'enid':5,'encaption':4,'rucaption':3,'ruid':0 }
languages={'ru':'en','en':'ru'}
season = 1
'''
def log(message):
    #bot_logger.send_message(307518206,f'#Simpsons получил сообщение!\n user: @{message.from_user.username}\n name: {message.from_user.first_name} {message.from_user.last_name}\n text: {message.text} \n content_type: {message.content_type}\n id: {message.chat.id}', disable_notification=True)
def log_call(call):
    if call.message.chat.id != 307518206:
        bot_logger.send_message(307518206,f'#Simpsons получил callback!\n id: {call.message.chat.id}\n dat:{call.data}', disable_notification=True)
'''
def log(message):
    #curs.execute("CREATE TABLE IF NOT EXISTS log_messages (id INTEGER, message_id INTEGER, date TEXT, time TEXT)")
    #print('mess:',message)
    
    with lock:
        curs.execute(f"insert into log_messages VALUES({message.chat.id}, {message.message_id}, \"{str(datetime.date.today())}\", \"{str(datetime.datetime.now().time())}\")")
        conn.commit()
        
    
def log_call(call):
    #print('call:',call)
    #curs.execute("CREATE TABLE IF NOT EXISTS log_calls (id INTEGER, data TEXT, date TEXT, time TEXT)")
    
    with lock:
        curs.execute(f"insert into log_calls VALUES({call.message.chat.id}, \"{call.data}\", \"{str(datetime.date.today())}\", \"{str(datetime.datetime.now().time())})\")")
        conn.commit()
        

def get_vid(num,lang):
    curs.execute(f"SELECT * FROM series WHERE season = "+num[0]+" AND part = "+num[1])
    vid = curs.fetchone()
    #print(num, vid)
    if not vid or not vid[sqnums[f'{lang}caption']]:
        return [None]
    return [vid[sqnums[f'{lang}id']], ['S{:02d}E'.format(int(num[0])),'S{:02d}E{:02d} '.format(int(num[0]),int(num[1]))][int(lang=='en')]+vid[sqnums[f'{lang}caption']]]


def generate_message(num, lang):
    vid=get_vid(num, lang)
    #print('vid:',vid)
    if not vid[0]:
        return [[None,messages[lang][1]],None]
    next_call=[num[0],str(int(num[1])+1)]
    if not get_vid(next_call,lang)[0]:
        next_call = [str(int(num[0])+1),'1']
        if not get_vid(next_call,lang)[0]:
            next_call = None
    if num[1]=='1' and num[0]=='1':
        prev_call=None
    elif num[1]=='1':
        curs.execute('SELECT MAX(part) FROM series WHERE season = '+str(int(num[0])-1)+f' AND {lang}id IS NOT NULL')
        prev_call = [str(int(num[0])-1), str(curs.fetchone()[0])]
    else:
        prev_call=[num[0],str(int(num[1])-1)]
    if next_call:
        next_call.append(lang)
    if prev_call:
        prev_call.append(lang)
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row_width=2
    #print(num, prev_call)
    btnlist=[]
    if prev_call:
        btnlist.append(telebot.types.InlineKeyboardButton('<-',callback_data=' '.join(prev_call)))
    if next_call:
        btnlist.append(telebot.types.InlineKeyboardButton('->',callback_data=' '.join(next_call)))
    keyboard.add(*btnlist)
    keyboard.add(telebot.types.InlineKeyboardButton(lang,callback_data=' '.join([num[0],num[1],languages[lang]])))
    return [vid, keyboard]


def set_lang(id,lang):
    curs.execute(f"SELECT language FROM lang WHERE id = {id}")

    with lock:
        if curs.fetchone():
            curs.execute(f'UPDATE lang SET language="{lang}" WHERE id={id}')
        else:
            curs.execute(f'INSERT INTO lang (language,id) VALUES("{lang}",{id})')
        conn.commit()

def get_lang(id):
    curs.execute(f"SELECT language FROM lang WHERE id = {id}")
    lang=curs.fetchone()
    if lang:
        return lang[0]
    else:
        set_lang(id,'en')
        return 'en'

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    log_call(call)
    dat=call.data.split(' ')
    set_lang(call.message.chat.id,dat[2])
    mes=generate_message([dat[0],dat[1]],dat[2])
    #print(mes)
    if not mes[0][0]:
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(chat_id=call.message.chat.id,text=mes[0][1])
    else:
        bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.message_id, media=telebot.types.InputMediaVideo(mes[0][0]))
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=mes[0][1],reply_markup=mes[1])


@bot.message_handler(commands=['language'])
def set_lang_command(message):
    log(message)
    keyboard=telebot.types.ReplyKeyboardMarkup()
    keyboard.add(*languages.keys())
    bot.send_message(message.chat.id,messages[get_lang(message.chat.id)][2], reply_markup=keyboard)
    bot.register_next_step_handler(message,set_lang_step)

def set_lang_step(message):
    if message.text in languages.keys():
        set_lang(message.chat.id, message.text)
        bot.send_message(message.chat.id,messages[get_lang(message.chat.id)][3], reply_markup=telebot.types.ReplyKeyboardRemove())
        send_welcome(message)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    log(message)
    bot.send_message(message.chat.id,messages[get_lang(message.chat.id)][0])

'''
############################################### Методы для загрузки видео в бота

@bot.message_handler(regexp=r".. \d+ \d+")
def my_save_vid_message(message):
    if message.chat.id == 307518206:
        spl = message.text.split()
        bot.send_message(message.chat.id, "send video:")
        bot.register_next_step_handler(message, lambda m: my_handle_docs_video(m,spl[0],spl[1],spl[2]))
    else:
        log(message)

def my_handle_docs_video(message,language,season,part):
    curs.execute(f"SELECT * FROM series WHERE season={season} and part={part}")
    print(f'curs: {language} {season} {part} {message.caption}')
    if curs.fetchone():
        curs.execute(f'UPDATE series SET {language}caption="{message.caption}",{language}id="{message.video.file_id}" WHERE season={season} and part={part}')
    else:
        curs.execute(f'INSERT INTO series ({language}caption,{language}id,season,part) VALUES("{message.caption}","{message.video.file_id}",{season},{part})')
    conn.commit()
    bot.send_message(message.chat.id, "ok")
'''
@bot.message_handler(commands=['stat'])
def send_statistic(message):
    log(message)
    send_stat()
@bot.message_handler(commands=['send'])
def send_to_somebody(message):
    log(message)
    if message.chat.id == 307518206:
        msg = bot.send_message(message.chat.id,'Send id:')
        bot.register_next_step_handler(msg, id_step)

def id_step(message):
    msg = bot.send_message(message.chat.id,'Send message:')
    bot.register_next_step_handler(msg, lambda m: send_step(m, message.text))

def send_step(message,id):
    #bot.send_message(id,message.text)
    bot.copy_message(id,message.chat.id, message.message_id)

@bot.message_handler(regexp=r"(\d+).+?(\d+)")
def send_vid_message(message):
    log(message)
    l=generate_message(re.search('(\d+).+?(\d+)', message.text).groups(),get_lang(message.chat.id))
    if l[0][0]:
        bot.send_video(message.chat.id, l[0][0], caption=l[0][1], reply_markup=l[1])
    else:
        #print('no')
        bot.send_message(message.chat.id, messages[get_lang(message.chat.id)][1])

@bot.message_handler(content_types=["text","audio","document","photo","sticker","video","video_note","voice","location","contact","new_chat_members","left_chat_member","new_chat_title","new_chat_photo","delete_chat_photo","group_chat_created","supergroup_chat_created","channel_chat_created","migrate_to_chat_id","migrate_from_chat_id","pinned_message"])
def recieve_any_message(message):
    bot.forward_message(307518206,message.chat.id, message.message_id)
    log(message)

lock = threading.Lock()
def send_stat():
    try:
#       lock.acquire(True)
        message_count = curs.execute(f'SELECT COUNT(*) from log_messages where date = \"{str(datetime.date.today())}\"').fetchone()[0]
        call_count = curs.execute(f'SELECT COUNT(*) from log_calls where date = \"{str(datetime.date.today())}\"').fetchone()[0]
        bot_logger.send_message(307518206,f'{str(datetime.date.today())}\n Сегодня Гомер получил {message_count} сообщений и {call_count} callback-ов!')
    except Exception as e:
        bot_logger.send_message(307518206,"OSHIBKA:"+str(e)[:4000])
#    finally:
#        lock.release()

def repeat_send_stat():
    send_stat()
    t = Timer(3600*24, repeat_send_stat)
    t.start()
#repeat_send_stat()
#while True:
try:
    bot.polling(none_stop=True, timeout=123)
except Exception as e:
    bot_logger.send_message(307518206,"OШIBKA:"+str(e)[:4000])
#sleep(15)

'''
while True:
    try:
        bot.polling()
    except Exception as err:
        with open('output.txt', 'w') as file:  # Use file to refer to the file object
            file.write(datetime.datetime.now+" e:"+str(Exception))
'''

