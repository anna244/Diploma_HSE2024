import asyncio
import io
import logging
import mimetypes
import os

import aiohttp
import magic
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (BotCommand, BufferedInputFile, CallbackQuery,
                           InlineKeyboardButton, InlineKeyboardMarkup,
                           InputMediaPhoto, KeyboardButton, Message, PhotoSize,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove)
from aiogram.utils.media_group import MediaGroupBuilder

# полученный у @BotFather
BOT_TOKEN = os.environ.get('TGBOT_API_TOKEN')
API_URL = os.environ.get('API_URL', 'http://localhost:8000')

# Инициализируем хранилище (создаем экземпляр класса MemoryStorage)
storage = MemoryStorage()

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Объект бота
bot = Bot(token=BOT_TOKEN)

# Диспетчер
dp = Dispatcher(storage=storage)

# # Создаем "базу данных" пользователей
# user_dict: dict[int, dict[str, str | int | bool]] = {}

# Пример данных в словаре
# {
#     411554990: {
#         'gender': 'women', 
#         'photo_unique_id': 'AQADTtkxGwABwDlLfQ', 
#         'photo_id': 'AgACAgIAAxkBAAPQZmcYwAEbDJ4wBE-XkXQiFikqVbEAAk7ZMRsAAcA5S5pnKfoNAAGLLwEAAwIAA3gAAzUE', 
#         'promt': 'your_promt'
#     }
# }

# Cоздаем класс, наследуемый от StatesGroup, для группы состояний нашей FSM
class FSMFillForm(StatesGroup):
    # Создаем экземпляры класса State, последовательно
    # перечисляя возможные состояния, в которых будет находиться
    # бот в разные моменты взаимодействия с пользователем
    name_of_model = State()
    files = State()        # Состояние ожидания ввода изображений
    gender = State()      # Состояние ожидания выбора пола
    promt= State()     # Состояние ожидания загрузки текста

# Функция для настройки кнопки Menu бота
async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(
            command='/start',
            description='Начать'),
    ]
    await bot.set_my_commands(main_menu_commands)


# Хэндлер на команду /start
@dp.message(CommandStart(), StateFilter(default_state))
async def cmd_start(message: types.Message):
    # Создаем объекты кнопок
    button_1 = KeyboardButton(text='ControlNet')
    button_2 = KeyboardButton(text='Lora')
    button_3 = KeyboardButton(text='Lora_inference')

    # Создаем объект клавиатуры, добавляя в него кнопки
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button_1, button_2, button_3]],
        resize_keyboard=True
    )

    await message.answer(
        text = 'Привет! Я - бот, который умеет обучать ControlNet и LoRA на твоих данных',
        reply_markup=keyboard
    )
   

# Этот хэндлер будет срабатывать на команду "/cancel" в любых состояниях,
# кроме состояния по умолчанию, и отключать машину состояний
@dp.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(
        text='Вы вышли из команды\n\n'
             'Чтобы снова перейти к заполнению данных - '
             'отправьте команду /start'
    )
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()
    

#-----------------------------------------------------------------------------------------
# Этот хэндлер будет срабатывать на ответ "ControlNet" 
# https://docs.aiogram.dev/en/latest/dispatcher/filters/magic_filters.html
@dp.message(F.text.in_({'ControlNet', 'Lora'}), StateFilter(default_state))
async def process_ControlNet_answer(message: Message, state: FSMContext):
    await state.update_data(name_of_model=message.text)

    # Создаем объекты инлайн-кнопок
    male_button = InlineKeyboardButton(
        text='women',
        callback_data='women'
    )
    female_button = InlineKeyboardButton(
        text='men',
        callback_data='men'
    )

    # Добавляем кнопки в клавиатуру (две в одном ряду )
    keyboard: list[list[InlineKeyboardButton]] = [
        [male_button, female_button]
    ]
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    # Отправляем пользователю сообщение с клавиатурой
    await message.answer(
        text='Спасибо!',
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        text='Укажите ваш пол',
        reply_markup=markup,
    )
    # Устанавливаем состояние ожидания выбора пола
    await state.set_state(FSMFillForm.gender)


# Этот хэндлер будет срабатывать на нажатие кнопки при
# выборе пола и переводить в состояние отправки фото
@dp.callback_query(StateFilter(FSMFillForm.gender),
                   F.data.in_(['women', 'men']))
async def process_gender_press(callback: CallbackQuery, state: FSMContext):
    # Cохраняем пол (callback.data нажатой кнопки) в хранилище,
    # по ключу "gender"
    await state.update_data(gender=callback.data)
    # Удаляем сообщение с кнопками, потому что следующий этап - загрузка фото
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.delete()
    await callback.message.answer(
        text='Спасибо! А теперь загрузите, пожалуйста, фото'
    )
    # Устанавливаем состояние ожидания загрузки фото
    await state.set_state(FSMFillForm.files)


# Этот хэндлер будет срабатывать, если во время выбора пола
# будет введено/отправлено что-то некорректное
@dp.message(StateFilter(FSMFillForm.gender))
async def warning_not_gender(message: Message):
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками '
             'при выборе пола\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


# Этот хэндлер будет срабатывать, если отправлено фото
# и переводить в состояние ввода promt
@dp.message(StateFilter(FSMFillForm.files),
            F.photo[-1].as_('largest_photo'))
async def process_photo_sent(message: Message,
                             state: FSMContext,
                             largest_photo: PhotoSize):
    # Cохраняем данные фото (file_unique_id и file_id) в хранилище
    # по ключам "photo_unique_id" и "photo_id"
    is_empty = False
    data = await state.get_data()
    files = data.get('files')
    if not files:
        is_empty = True
        files = {}
    files[largest_photo.file_unique_id] = {
        'photo_unique_id': largest_photo.file_unique_id,
        'photo_id': largest_photo.file_id
    }
    await state.update_data(
        files=files
    )

    # Если обрабатываем первую фотографию
    if is_empty:
        await message.answer(
            text='Введите свой promt',
            reply_markup=ReplyKeyboardRemove()
        )

    # Устанавливаем состояние ожидания выбора образования
    await state.set_state(FSMFillForm.promt)


# Этот хэндлер будет срабатывать, если во время отправки фото
# будет введено/отправлено что-то некорректное
@dp.message(StateFilter(FSMFillForm.files))
async def warning_not_photo(message: Message):
    await message.answer(
        text='Пожалуйста, на этом шаге отправьте '
             'ваше фото\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


# Этот хэндлер будет срабатывать на ввод promt
# выводить из машины состояний
@dp.message(StateFilter(FSMFillForm.promt), F.text.isalpha())
async def process_promt_sent(message: Message, state: FSMContext):
    # Cохраняем имя в хранилище по ключу "promt"
    await state.update_data(promt=message.text)
    # Добавляем в "базу данных" анкету пользователя
    # по ключу id пользователя
    data = await state.get_data()
    # user_dict[message.from_user.id] = data
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await message.answer(
        text='Спасибо! Ваши данные сохранены! Пришлем результат когда все будет готово\n\n'
    )
    
    async with aiohttp.ClientSession() as session:
        request_data = aiohttp.FormData()
        request_data.add_field('fio', f'telegram_{message.from_user.id}')
        request_data.add_field('gender', data['gender'])
        request_data.add_field('name_of_model', data['name_of_model'])
        request_data.add_field('promt', data['promt'])

        for fille_data in data['files'].values():
            # https://docs.aiogram.dev/en/latest/api/download_file.html
            file = await bot.download(fille_data['photo_id'])
            file_format = magic.from_buffer(file.read(2048), True)
            file.seek(0)
            file_extension = mimetypes.guess_extension(file_format) or '.jpg'
            request_data.add_field('files', file, filename=f'{fille_data["photo_unique_id"]}{file_extension}')

        generated_image_urls = []
        request = session.post(f'{API_URL}/input_train/', data=request_data)
        async with request as resp:
            server_response = await resp.json()
            generated_image_urls = server_response['generated_images']
        
        # https://docs.aiogram.dev/en/latest/utils/media_group.html#usage
        # https://stackoverflow.com/questions/78285221/send-multiple-photos-with-text-aiogram
        media_group = MediaGroupBuilder(caption='Результат')
        for item in generated_image_urls:
            async with session.get(url=item) as response:
                response.auto_decompress = False
                buffer = io.BytesIO(await response.read())
                buffer.seek(0)
                # convert http://localhost:8000/static/telegram_411554990/tatto1.png to telegram_411554990_tatto1.png
                caption = '_'.join(item.split('/')[-2:])
                # https://docs.aiogram.dev/en/latest/api/upload_file.html#upload-from-buffer
                media = BufferedInputFile(buffer.read(), filename=caption)
                media_group.add(type='photo', media=media)

        await bot.send_media_group(chat_id=message.chat.id, media=media_group.build())
    

# Этот хэндлер будет срабатывать, если во время отправки Promt
# будет введено/отправлено что-то некорректное
@dp.message(StateFilter(FSMFillForm.promt))
async def warning_not_promt(message: Message):
    await message.answer(
        text='Пожалуйста, напишите корректный promt!\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )


#--------------------------------------------------------------------------------------------------------------    
# Этот хэндлер будет срабатывать на любые сообщения в состоянии "по умолчанию",
# кроме тех, для которых есть отдельные хэндлеры
@dp.message(StateFilter(default_state))
async def send_echo(message: Message):
    await message.reply(text='Извините, не понимаю')


# Запуск процесса поллинга новых апдейтов
async def main():
    await set_main_menu(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
